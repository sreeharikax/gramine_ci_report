import pandas as pd
import itertools
import os
import re
from data.constants import *
import requests
import traceback

class FailureAnalyser():
    def __init__(self, ra, ci_obj):
        self.rg = ra
        self.ci_obj = ci_obj
        self.fdata = {}
        self.f_list = {}

        self.f_list = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data",
                                               "Gramine_Failures.csv"))
        self.error_df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data",
                                                 "CI_Failures.csv"))

    def get_suites_list(self, test_list):
        comb_list = []
        for key, value in self.rg.rdata.items():
            self.fdata[key] = value.get('failures', {})
            self.fdata[key]["build_details"] = value.get('build_details')

        for test in test_list:
            if test == "build_details":
                comb_list.extend(list(itertools.product([test], self.rg.build_keys)))
            else:
                max_value = max([len(fvalue.get(test, [])) for fkey, fvalue in self.fdata.items()])
                max_value = max_value+1 if (max_value == 0) else max_value
                comb_list.extend(list(itertools.product([test], list(range(max_value)))))

        return comb_list

    def get_headers(self):
        headers_list = []
        for key, val in self.rg.rdata.items():
            if key == "local_ci_graphene_sgx_kvm" and val["build_details"]["result"] == "SUCCESS":
                continue
            if [True for f_key in val.get("failures", {}).keys() if val.get("failures", {}).get(f_key, None) not in [[], {}]] or \
                    (val.get("failures", {}) == {}):
                headers_list.append(key)
        return headers_list

    def parse_output(self, output):
        self.summary_data = None
        self.rg.rdata = output
        self.fail_jobs = self.get_headers()
        test_suites = self.rg.get_test_suites()
        test_list = test_suites.copy()
        suites_list = self.get_suites_list(test_list)
        row_list = pd.MultiIndex.from_tuples(suites_list)
        df = pd.DataFrame('', row_list, columns=self.fail_jobs)
        try:
            for tc in test_list:
                for suite in self.fail_jobs:
                    data = self.fdata[suite]
                    res = data.get(tc, {})
                    if res != None:
                        if tc == "build_details":
                            for key in self.rg.build_keys:
                                df.loc[(tc, key), suite] = res.get(key)
                        else:
                            for index, val in enumerate(res):
                                df.loc[(tc, index), suite] = val
            self.summary_data = self.get_summary_data()
        except Exception as e:
            print("Exception Occured during failure analysis for suite {} and tc {} and exception is {}".format(suite, tc, e))

        f_df = df.style.apply(self.color_format)
        f_df.set_properties(**{'text-align': 'center'})
        return f_df

    def get_baseos_failures(self, exec_mode, base_os=None):
        fail_data = list(self.f_list.loc[(self.f_list['Mode'] == exec_mode) & (self.f_list['BaseOS'].isna())]['Test'])
        if base_os:
            return list(self.f_list.loc[(self.f_list['BaseOS'] == base_os) & (self.f_list['Mode'] == exec_mode)]['Test']) + fail_data
        return fail_data

    def get_failures(self, f_df):
        exec_mode = f_df['build_details'].get('Mode') or "Gramine SGX"
        base_os = None
        if f_df['build_details'].get('OS'):
            base_os = f_df['build_details']['OS']
        baseos_failures = self.get_baseos_failures(exec_mode=exec_mode, base_os=base_os)
        return baseos_failures

    def build_err_parsing(self, out):
        err_list = [desc[1]["Category"] for desc in self.error_df.iterrows() if re.search(desc[1]["Error Message"], out)]
        err_list = ", ".join(list(set(err_list)))
        return err_list

    def get_console_output(self, n_job, n_build):
        if n_job.endswith(f"_{n_build}"):
            n_job = n_job.split(f"_{n_build}")[0]
        return self.ci_obj.jenkins_server.get_build_console_output(n_job, n_build)

    def curation_workload_parsing(self, workload):
        try:
            binfo = self.ci_obj.jenkins_server.get_build_info(self.job_name, self.build_no)
            console_data = self.console_out.split("::TestClass::")
            result = [out for out in console_data if out.startswith(f"{workload} ")][0]
            if binfo and "artifacts" in binfo.keys():
                artifacts = [artifacts["fileName"] for artifacts in binfo["artifacts"] \
                             if re.search(workload+"(_verifier.log|.txt)", artifacts["fileName"])]
                for file_name in artifacts:
                    response = requests.get(f"{JENKINS_URL}/job/{self.job_name}/{self.build_no}/artifact/{file_name}")
                    if response.status_code == 200:
                        result += "\n" + response.text
            if len(result.split("\n")) < 3:
                tc_data = [tc for suite in self.test_report["suites"] for tc in suite["cases"] if
                           (tc["name"] == workload and tc["status"] != "PASSED")][0]
                if "errorStackTrace" in tc_data.keys(): result += tc_data["errorStackTrace"]
            err_data = self.build_err_parsing(result)
        except Exception:
            err_data = ""
            print(f"Exception occured during curation_workload_parsing {workload} {traceback.print_exc()}")
        return err_data

    def test_err_parsing(self, failure):
        try:
            tc_data = [tc for suite in self.test_report["suites"] for tc in suite["cases"] if (tc["name"] == failure and tc["status"] != "PASSED")][0]
            err_data = self.build_err_parsing(tc_data["stdout"] + tc_data["stderr"])
        except Exception:
            err_data = ""
            print(f"Exception occured during test_err_parsing {failure} {traceback.print_exc()}")
        return err_data

    def workload_err_parsing(self, failure):
        try:
            if failure.startswith("test_gsc_"):
                workload = re.match("test_gsc_(.*)_workload", failure).groups()[0]
                out_data = [out for out in self.console_out.split("[Pipeline] sh") if f'gsc-{workload.replace("_", "-")}' in out]
                result = ["\n".join(out_data)]
            elif failure.startswith("test_stress_ng"):
                workload = re.match("test_stress_ng_(.*)", failure).groups()[0]
                result = [out for out in self.console_out.split("[Pipeline] sh") if re.search(
                                             f"stress-ng --job {workload}(|.centos).job", out)]
            else:
                workload = re.match("test_(.*)", failure).groups()[0].replace(
                                             "_workload", "").replace("_", "-")
                result = [out for out in self.console_out.split("[Pipeline] sh\r\n") if f"cd CI-Examples/{workload}\n" in out]
            err_data = self.build_err_parsing(result[0])
        except Exception as e:
            err_data = ""
            print(f"Exception occured during workload_err_parsing {self.job_name} {failure} ", traceback.print_exc())
        return err_data

    def sdtest_error_parsing(self):
        try:
            err_data = self.build_err_parsing(self.console_out)
        except Exception as e:
            err_data = ""
            print(f"Exception occured during sdtest_error_parsing {self.job_name}", traceback.print_exc())
        return err_data


    def error_parsing(self, workload, suite):
        if  "curation" in self.job_name:
            err_out = self.curation_workload_parsing(workload)
        elif "sdtest" in workload:
            err_out = self.sdtest_error_parsing()
        elif suite in ["test_workloads", "tests_stressng"]:
            err_out = self.workload_err_parsing(workload)
        else:
            err_out = self.test_err_parsing(workload)
        return err_out

    def get_build_data(self, job_data, job_name):
        self.job_name = job_name
        self.build_no = job_data["build_details"].get("build_no")
        if self.build_no:
            self.test_report = self.ci_obj.jenkins_server.get_build_test_report(self.job_name, int(self.build_no))
            self.console_out = self.get_console_output(self.job_name, self.build_no)
        else:
            self.console_out == "Build Number not specified"
            self.test_report = {}

    def suites_failure_parsing(self, val_data, suites_list):
        try:
            wkd_data = {}
            baseos_failures = self.get_failures(val_data)
            for suite in suites_list:
                for failure in val_data[suite]:
                    if failure in baseos_failures:
                        desc = self.f_list[self.f_list["Test"] == failure].get("Description")
                        err_str = "Known Failure, No Description provided" if desc is None else desc.unique()[0]
                        err_type = "baseos"
                    else:
                        err_str = self.error_parsing(failure, suite)
                        err_type = "ci"
                        if not err_str:
                            err_str = "Unknown Failure"
                            err_type = "other"
                    wkd_data[failure] = {"err": err_str, "err_type": err_type}
        except Exception as e:
            print(f"Failed to parse suite data for n_job: {self.job_name}, {traceback.print_exc()}")
        return wkd_data

    def get_summary_data(self):
        summary_data = {}
        try:
            for n_job in self.fail_jobs:
                val = self.fdata[n_job]
                self.get_build_data(val, n_job)
                suites_list = [key for key in val.keys() if val[key] != []]
                suites_list.remove("build_details")
                summary_data[n_job] = {"build_details": val["build_details"]}
                if (val["build_details"]["result"] in ["FAILURE",  None]) and (suites_list == []):
                    if self.console_out == "Build Number not specified":
                        err_list = "Build Not Triggered Yet"
                    else:
                        err_list = self.build_err_parsing(self.console_out)
                    summary_data[n_job]["build_details"].update({"err": err_list if err_list else "Unknown Failure",
                                                                 "err_type": "ci"  if err_list else "other"})
                elif suites_list != []:
                    summary_data[n_job].update(self.suites_failure_parsing(val, suites_list))

        except Exception as e:
            print(traceback.print_exc())
        return summary_data

    def color_format(self, f_df):
        df_1 = f_df.copy()
        for col1, col2 in f_df.keys():
            out = self.summary_data[f_df.name]
            workload = df_1.loc[col1, col2]
            if col1 == "build_details" and col2 == "result" and out[col1]["result"] == "ABORTED":
                df_1.loc[col1, col2] = 'background-color: #FFC000;'
            elif workload == '' or col1 == "build_details":
                df_1.loc[col1, col2] = ''  # background-color: #FFC000;
            else:
                if out[workload]["err_type"] == "baseos":
                    df_1.loc[col1, col2] = ''
                elif out[workload]["err_type"] == "other":
                    df_1.loc[col1, col2] = 'background-color: orange;'
                else:
                    df_1.loc[col1, col2] = 'background-color: #FFEB9C;'
        return df_1


