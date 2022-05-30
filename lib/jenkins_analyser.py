import jenkins
import os
import json

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
        match_out = output.split("Starting building: ")
        for match in match_out:
            details = ("").join(match.split("\r\n")[0]).split(" #")
            if len(details) > 1:
                build_name = details[0].strip()
                job_details[build_name] = job_details.get(build_name, [])
                dbuild_no = details[1].strip()
                if (build_name in updated_builds.keys()) and (updated_builds.get(build_name, {}).get(dbuild_no, None) != None):
                    job_details[build_name].append(updated_builds[build_name][dbuild_no].strip())
                else:
                    job_details[build_name].append(dbuild_no)
        return job_details

    def get_build_env_details(self, pipeline, build_no):
        env_details = {}
        node_name = ''
        try:
            console_out = self.jenkins_server.get_build_info(pipeline, build_no, depth=1)
            sgx_mode = 1 if "sgx" in pipeline else 0
            for c1 in console_out['actions']:
                if "parameters" in c1.keys():
                    node_name = [param['value'] for param in c1["parameters"] if param["name"] == "node_label"][0]
            env_details["node"] = node_name
            env_details["build_no"] = build_no
            env_details["result"] = console_out["result"]
            env_details['sgx'] = sgx_mode
        except Exception as e:
            print("Unable to get build environment details for {}:{}".format(pipeline, build_no))
        return env_details

    def get_build_summary(self, pipeline_jobs):
        consolidate_data = {}
        for pipeline, build_no in pipeline_jobs.items():
            for num in build_no:
                try:
                    res = {}
                    build_info = {}
                    build_info = self.get_build_env_details(pipeline, int(num))
                    if "gsc" in pipeline:
                        pass
                    else:
                        job_report = self.jenkins_server.get_build_test_report(pipeline, int(num))
                        res = self.get_job_summary(job_report['suites'])
                        fail_summary = self.get_test_failure_data(job_report['suites'])
                        res.update({"failures": fail_summary})
                except:
                    print("Failed to analyze pipeline {}, {}".format(pipeline, num))
                finally:
                    res.update({"build_details": build_info})
                    job_name = "{}_{}".format(pipeline, num)
                    consolidate_data[job_name] = res
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
            res[suite['name'].split("_")[1]] = suite['status']
        return res

    def analyze_report(self, job_name):
        build_no = self.jenkins_server.get_job_info(job_name)["builds"][0]["number"]
        console_output = self.jenkins_server.get_build_console_output(job_name, build_no)
        downstream_jobs = self.get_jenkins_job_details(console_output)
        output = self.get_build_summary(downstream_jobs)
        return output

    def get_failed_test(self, test_data):
        failed_tests = [tc['name'] for tc in test_data if tc['status'] == "FAILED"]
        return failed_tests

