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


class JenkinsAnalysis:
    def __init__(self, url, u_name, u_pwd):
        self.url = url
        self.user = u_name
        self.pwd = u_pwd
        self.jenkins_server = self.create_server()
        self.build_details = True

    def create_server(self):
        return jenkins.Jenkins(self.url, self.user, self.pwd)

    def get_pipeline_details(self, build_name, job_regex):
        builds_list = []
        rerun_builds = os.environ.get('rerun_details', '{}')
        updated_builds = json.loads(rerun_builds)
        if job_regex:
            for jjob in job_regex:
                dbuild_no = jjob.split("#")[1]
                if dbuild_no not in builds_list:
                    builds_list.append(dbuild_no)
        else:
            builds_list.append("")
        if (build_name in updated_builds.keys()):
            if type(updated_builds[build_name]) == dict:
                 self.update_build_no(builds_list, updated_builds[build_name])
            elif type(updated_builds[build_name]) == list:
                for build_item in updated_builds[build_name]:
                    self.update_build_no(builds_list, build_item)
        return builds_list

    def update_build_no(self, builds_list, build_val):
        for jkey, jvalue in build_val.items():
            if (jkey in builds_list) or (jkey == "add"):
                if jkey == "add":
                    builds_list.remove('')
                else:
                    builds_list.remove(jkey)
                builds_list.append(jvalue)

    def build_dict_count(self, match_out):
        build_count  = {}
        for s_b in set(match_out):
            build_count[s_b] = match_out.count(s_b)
        return build_count

    def get_jenkins_job_details(self, output):
        job_details = {}
        match_out = re.findall("Scheduling project: (.*)", output)
        s_jobs = self.build_dict_count(match_out)
        for match, count in s_jobs.items():
            build_name = match.strip()
            job_regex = re.findall("Starting building: {} .\d+".format(build_name), output)
            dbuild_no = self.get_pipeline_details(build_name, job_regex)
            if len(dbuild_no) != count:
                [dbuild_no.append("") for b_diff in range(count-len(dbuild_no))]
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
        edmm = None
        env_details = {}
        try:
            build_out = self.jenkins_server.get_build_info(pipeline, build_no, depth=1)
            env_details["result"] = build_out["result"]
            env_details["build_no"] = build_no
            if self.build_details:
                node_info = self.get_node_details(pipeline, build_no, console_out)
                if node_info: env_details.update(node_info)
                for c1 in build_out['actions']:
                    if "parameters" in c1.keys():
                        details = [param['value'] for param in c1['parameters'] if param['name'] == "EDMM"] or ["0"]
                        if details == ["1"]: edmm = True
                    elif "environment" in c1.keys():
                        if edmm:
                            env_details['Mode'] = "Gramine EDMM"
                        elif c1["environment"].get('SGX') != "1":
                            env_details['Mode'] = "Gramine Native"
                        else:
                            env_details['Mode'] = "Gramine SGX"
                        env_details['OS'] = c1.get('environment', {}).get('os_release_id',
                            '').capitalize() + " " + c1.get('environment', {}).get('os_version', '')
                        break
                env_details["Kernel Version"] = self.jenkins_server.run_script('println "uname -r".execute().text',
                                                                               env_details['node']).strip()
            if "_gsc" in pipeline:
                env_details["Mode"] = "Gramine GSC"
            elif "_curation_app" in pipeline:
                env_details["Mode"] = "Gramine Curation"
        except Exception as e:
            print("Unable to get build environment details for {}:{} {}".format(pipeline, build_no, e))
        return env_details

    def get_build_summary(self, pipeline, build_no):
        try:
            sbuild = {}
            build_info = {"result": "FAILURE"}
            console_out = self.jenkins_server.get_build_console_output(pipeline, int(build_no))
            build_info = self.get_build_env_details(pipeline, int(build_no), console_out)
            if pipeline != "local_ci_graphene_sgx_kvm":
                job_report = self.jenkins_server.get_build_test_report(pipeline, int(build_no))
                sbuild = self.get_job_summary(job_report['suites'])
                fail_summary = self.get_test_failure_data(job_report['suites'])
                sbuild.update({"failures": fail_summary})
        except:
            print("Failed to analyze pipeline {}, {}".format(pipeline, build_no))
        finally:
            sbuild.update({"build_details": build_info})
        return sbuild

    def get_pipeline_summary(self, pipeline_jobs):
        consolidate_data = {}
        for pipeline, build_list in pipeline_jobs.items():
            for build_no in build_list:
                res = self.get_build_summary(pipeline, build_no)
                if len(build_list) > 1:
                    pipeline_name = pipeline + "_" + str(build_no)
                else:
                    pipeline_name = pipeline
                consolidate_data[pipeline_name] = res
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
                failed_tests = self.get_failed_test(suite['cases'], elem)
                old_data = fail_report.get(elem, [])
                fail_report[elem] = old_data + failed_tests
        return fail_report

    def get_test_suite_name(self, data):
        workload_list = list(set([d['className'].split(".")[-2] for d in data]))
        return workload_list

    def get_suite_summary(self, suite_data, workload):
        result = summary.copy()

        result["Pass"] = sum((tc['status'] in ["PASSED", "FIXED"]) for tc in suite_data if workload in tc['className'])
        result["Fail"] = sum((tc['status'] in ["FAILED", "REGRESSION"]) for tc in suite_data if workload in tc['className'])
        result["Skip"] = sum((tc['status'] == "SKIPPED") for tc in suite_data if workload in tc['className'])
        result["Total"] = result["Pass"] + result["Fail"] + result["Skip"]
        return result

    def get_workload_result(self, suite_data):
        res = {}
        for suite in suite_data:
            res[suite['name'].replace("test_", "").replace("_workload", "")] = suite['status']
        return res

    def analyze_report(self, job_name):
        pipeline_no = os.environ.get('pipeline_no', '')
        if pipeline_no :
            pipeline_no = int(pipeline_no)
        else:
            pipeline_no = self.jenkins_server.get_job_info(job_name)["builds"][0]["number"]
        os.environ["pipeline_no"] = str(pipeline_no)
        console_output = self.jenkins_server.get_build_console_output(job_name, pipeline_no)
        downstream_jobs = self.get_jenkins_job_details(console_output)
        output = self.get_pipeline_summary(downstream_jobs)
        return output

    def get_failed_test(self, test_data, test_suite):
        failed_tests = [tc['name'] for tc in test_data if tc['status'] in ["FAILED", "REGRESSION"] and test_suite in tc['className']]
        return failed_tests

