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
            self.build_keys = ['result', "build_no", "Mode"]
        for test in test_list:
            if test == "build_details":
                comb_list.extend(list(itertools.product([test], self.build_keys)))
            elif test not in ["test_workloads"]:
                comb_list.extend(itertools.product([test], test_reskeys))
        return comb_list

    def get_headers_by_baseos(self):
        headers_list = []
        data_copy = copy.deepcopy(self.rdata)
        baseos_list = list(set([data_copy[x].get('build_details',{}).get('OS') for x in data_copy]))
        for os in baseos_list:
            com_jobs = [x for x in data_copy if data_copy[x].get('build_details', {}).get('OS') == os]
            headers_list.extend(com_jobs)

        return headers_list

    def parse_output(self, output):
        self.rdata = copy.deepcopy(output)
        headers = self.get_headers_by_baseos()
        test_suites = self.get_test_suites()
        suites_list = self.get_suites_list(test_suites)

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

    def get_test_suites(self):
        cases_list = []
        for rkey, rval in self.rdata.items():
            cases_list.extend(list(rval.keys()))
        cases_list = list(set(cases_list))
        cases_list.sort()
        if "failures" in cases_list:
            cases_list.remove('failures')
        return cases_list

