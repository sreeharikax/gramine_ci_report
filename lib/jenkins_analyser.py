import jenkins
import os
import json
import re
import xml.etree.ElementTree as ET

summary = {
    "Pass": 0,
    "Fail": 0,
    "Skip": 0,
    "Total": 0
}


class GrapheneCIAnalysis:
    def __init__(self, url, u_name, u_pwd):
        self.url = url
        self.user = u_name
        self.pwd = u_pwd
        self.jenkins_server = self.create_server()

    def create_server(self):
        return jenkins.Jenkins(self.url, self.user, self.pwd)

    def get_jenkins_job_details(self, output):
        job_details = {}
        rerun_builds = os.environ.get('rerun_details', '{}')
        updated_builds = json.loads(rerun_builds)
        match_out = output.split("Scheduling project: ")
        for match in match_out[1::]:
            build_name = match.split("\r\n")[0].strip()
            job_regex = re.search("Starting building: {} .\d+".format(build_name), output)
            if job_regex:
                dbuild_no = job_regex.group().split("#")[1]
            else:
                dbuild_no = ""
            if (build_name in updated_builds.keys()):
                job_details[build_name] = updated_builds[build_name]
            else:
                job_details[build_name] = dbuild_no
        return job_details

    def get_node_details(self, pipeline, build_no, console_out):
        node_details = {}
        try:
            node_info = re.search("Running on (.*) in (.*){}".format(pipeline), console_out)
            if node_info:
                node_details["node"] = node_info.groups()[0].strip()
            else:
                node_details["node"] = re.search("Waiting for next available executor on (.)(.*)(.)\\r\\n", console_out).groups()[1].strip()
            node_data = self.jenkins_server.get_node_config(node_details['node'])
            node_details["IP"] = ET.fromstring(node_data).find('launcher').find('host').text
            node_details["Kernel Version"] = self.jenkins_server.run_script('println "uname -r".execute().text',
                                                                           node_details['node']).strip()
        except Exception as e:
            print("Unable to get node details for {}:{} {}".format(pipeline, build_no, e))
        return node_details

    def get_build_env_details(self, pipeline, build_no, console_out):
        env_details = {}
        try:
            build_out = self.jenkins_server.get_build_info(pipeline, build_no, depth=1)
            node_info = self.get_node_details(pipeline, build_no, console_out)
            if node_info: env_details.update(node_info)
            for c1 in build_out['actions']:
                if "parameters" in c1.keys() and "gsc" in pipeline:
                    distro_version = [param['value'].replace(":", " ") for param in c1['parameters'] if param['name'] == "distro_ver"][0]
                    env_details['Mode'] = "Gramine SGX"
                    env_details['OS'] = distro_version.capitalize()
                elif "environment" in c1.keys() and "gsc" not in pipeline:
                    env_details['Mode'] = "Gramine SGX" if c1["environment"].get('SGX') == "1" else "Gramine Native"
                    env_details['OS'] = c1['environment'].get('os_release_id').capitalize() + " " + c1['environment'].get('os_version')
            env_details["result"] = build_out["result"]
            env_details["build_no"] = build_no
            env_details["Kernel Version"] = self.jenkins_server.run_script('println "uname -r".execute().text', env_details['node']).strip()
        except Exception as e:
            print("Unable to get build environment details for {}:{} {}".format(pipeline, build_no, e))
        return env_details

    def verify_gsc_workloads(self, gsc_console):
        gsc_result = {'test_workloads': {'python': "FAILED", 'bash': 'FAILED'}, 'failures' :{'test_workloads':{}}}
        bash_out = re.search('docker run --device=(.*) gsc-(.*)bash -c free(.*)Mem:(.*)Swap:', gsc_console, re.DOTALL)
        python_out = re.search('docker run --device=(.*) gsc-python -c (.*)print(.*)HelloWorld!(.*)HelloWorld!', gsc_console, re.DOTALL)
        if bash_out:
            gsc_result['test_workloads']['bash'] = "PASSED"
        else:
            gsc_result['failures']['test_workloads']['bash'] = "FAILED"
        if python_out:
            gsc_result['test_workloads']['python'] = "PASSED"
        else:
            gsc_result['failures']['test_workloads']['python'] = "FAILED"

        return gsc_result

    def get_build_summary(self, pipeline_jobs):
        consolidate_data = {}
        for pipeline, build_no in pipeline_jobs.items():
            try:
                res = {}
                build_info = {"result": "FAILURE"}
                console_out = self.jenkins_server.get_build_console_output(pipeline, int(build_no))
                build_info = self.get_build_env_details(pipeline, int(build_no), console_out)
                if "gsc" in pipeline:
                    res = self.verify_gsc_workloads(console_out)
                else:
                    job_report = self.jenkins_server.get_build_test_report(pipeline, int(build_no))
                    res = self.get_job_summary(job_report['suites'])
                    fail_summary = self.get_test_failure_data(job_report['suites'])
                    res.update({"failures": fail_summary})
            except:
                print("Failed to analyze pipeline {}, {}".format(pipeline, build_no))
            finally:
                res.update({"build_details": build_info})
                # job_name = "{}_{}".format(pipeline, num)
                consolidate_data[pipeline] = res
        return consolidate_data

    def result_update(self, res, orig_data):
        updated_data = {}
        for k, v in res.items():
            updated_data[k] = res[k] + orig_data[k]
        return updated_data

    def get_job_summary(self, suites_data):
        build_report = {}
        for suite in suites_data:
            suites_list = self.get_test_suite_name(suite['cases'])
            for elem in suites_list:
                build_report[elem] = build_report.get(elem, {})
                if elem == "test_workloads":
                    build_report[elem].update(self.get_workload_result(suite['cases']))
                else:
                    summary_data = self.get_suite_summary(suite['cases'], elem)
                    if build_report[elem] == {}:
                        build_report[elem] = summary_data
                    else:
                        build_report[elem] = self.result_update(summary_data, build_report[elem])
        return build_report

    def get_test_failure_data(self, suites_data):
        fail_report = {}
        for suite in suites_data:
            suite_list = self.get_test_suite_name(suite['cases'])
            for elem in suite_list:
                failed_tests = self.get_failed_test(suite['cases'])
                old_data = fail_report.get(elem, [])
                fail_report[elem] = old_data + failed_tests
        return fail_report

    def get_test_suite_name(self, data):
        workload_list = list(set([d['className'].split(".")[-2] for d in data]))
        return workload_list

    def get_suite_summary(self, suite_data, workload):
        result = summary.copy()

        result["Pass"] = sum((tc['status'] == "PASSED") for tc in suite_data if workload in tc['className'])
        result["Fail"] = sum((tc['status'] == "FAILED") for tc in suite_data if workload in tc['className'])
        result["Skip"] = sum((tc['status'] == "SKIPPED") for tc in suite_data if workload in tc['className'])
        result["Total"] = result["Pass"] + result["Fail"] + result["Skip"]
        return result

    def get_workload_result(self, suite_data):
        res = {}
        for suite in suite_data:
            res[suite['name'].replace("test_", "").replace("_workload", "")] = suite['status']
        return res

    def analyze_report(self, job_name):
        build_no = self.jenkins_server.get_job_info(job_name)["builds"][0]["number"]
        console_output = self.jenkins_server.get_build_console_output(job_name, build_no)
        downstream_jobs = self.get_jenkins_job_details(console_output)
        output = self.get_build_summary(downstream_jobs)
        return output

    def get_failed_test(self, test_data):
        failed_tests = [tc['name'] for tc in test_data if tc['status'] in ["FAILED", "REGRESSION"]]
        return failed_tests

