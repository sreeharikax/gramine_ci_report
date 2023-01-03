import os
import pandas as pd
import itertools
import copy

class ResultAnalyser:
    def __init__(self):
        self.build_details = True
        self.build_keys = []

    def get_suites_list(self, test_list):
        comb_list = []
        test_reskeys = ["Total", "Pass", "Fail", "Skip"]
        if self.build_details:
            self.build_keys = ['node', 'result', 'Mode', "OS", "Kernel Version", "IP", "build_no"]
        else:
            self.build_keys = ['result', "build_no"]
        for test in test_list:
            if test == "build_details":
                comb_list.extend(list(itertools.product([test], self.build_keys)))
            elif test not in ["test_workloads", "gsc"]:
                comb_list.extend(itertools.product([test], test_reskeys))
        return comb_list

    def get_headers_by_node(self, summary):
        headers_list = []
        data_copy = copy.deepcopy(self.rdata)
        gsc_jobs = [x for x in data_copy if "local_ci_graphene_gsc" in x]
        [data_copy.pop(job) for job in gsc_jobs]
        node_list = list(set([data_copy[x].get('build_details',{}).get('node') for x in data_copy]))
        for node in node_list:
            com_jobs = [x for x in data_copy if data_copy[x].get('build_details', {}).get('node') == node]
            headers_list.extend(com_jobs)
        if not summary: headers_list.extend(gsc_jobs)

        return headers_list

    def update_gsc_results(self):
        data_copy = copy.deepcopy(self.rdata)
        gsc_jobs = [x for x in data_copy if "local_ci_graphene_gsc" in x]
        [data_copy.pop(job) for job in gsc_jobs]
        comb = {}
        for gsc_job in gsc_jobs:
            for job, res in data_copy.items():
                if (res['build_details'].get('node') == self.rdata[gsc_job]['build_details'].get('node') and
                        res['build_details'].get('Mode') == "Gramine SGX"):
                    comb[job] = gsc_job
        for d_job, g_job in comb.items():
            data_copy[d_job]['gsc'] = self.rdata[g_job].get('test_workloads', {})
        return data_copy

    def parse_output(self, output, summary=False):
        self.rdata = copy.deepcopy(output)
        headers = self.get_headers_by_node(summary)
        test_suites = self.get_test_suites(summary)
        suites_list = self.get_suites_list(test_suites)

        if summary:
            result_summary = copy.deepcopy(self.update_gsc_results())
        else:
            result_summary = copy.deepcopy(self.rdata)

        row_list = pd.MultiIndex.from_tuples(suites_list)
        df = pd.DataFrame('', row_list, columns=headers)
        for tc in test_suites:
            for suite, data in result_summary.items():
                try:
                    res = data.get(tc, {})
                    for x, y in res.items():
                        if type(y) == int:
                            df.loc[(tc, x), suite] = int(y)
                        else:
                            df.loc[(tc, x), suite] = y
                except Exception as e:
                    print("Exception Occured during result analysis for pipeline {}:".format(suite), str(e))

        df_1 = df.style.apply(self.highlight_cells, axis=None)
        df_1.set_properties(**{'text-align': 'center'})
        return df_1

    def highlight_cells(self, x):
        df_1 = copy.deepcopy(x)
        for index in range(len(x)):
            if index %2 == 0:
                df_1.iloc[index] = 'background-color: #B4C6E7'
            else:
                df_1.iloc[index] = 'background-color: #E7E6E6'

        return df_1

    def get_test_suites(self, summary):
        cases_list = []
        for rkey, rval in self.rdata.items():
            cases_list.extend(list(rval.keys()))
        cases_list = list(set(cases_list))
        cases_list.sort()
        if summary: cases_list.append('gsc')
        cases_list.remove('failures')
        return cases_list

