import os
import pandas as pd
import itertools

class ResultAnalyser:
    def __init__(self, output, output_fname="test"):
        self.logs_dir = "report"
        self.rdata = output
        self.fname = output_fname

    def setup(self):
        if not os.path.isdir(self.logs_dir):
            os.mkdir(self.logs_dir)

    def get_suites_list(self, test_list):
        comb_list = []
        test_reskeys = ["Total", "Pass", "Fail", "Skip"]
        build_keys = ['node', 'build_no', 'result', 'sgx']
        for test in test_list:
            if test == "build_details":
                comb_list.extend(list(itertools.product([test], build_keys)))
            elif test != "test_workloads":
                comb_list.extend(itertools.product([test], test_reskeys))
        return comb_list

    def get_headers_by_node(self):
        headers_list = []
        data_copy = self.rdata.copy()
        gsc_jobs = [x for x in data_copy if "local_ci_graphene_gsc" in x]
        [data_copy.pop(job) for job in gsc_jobs]
        node_list = list(set([data_copy[x]['build_details']['node'] for x in data_copy]))
        for node in node_list:
            com_jobs = [x for x in data_copy if data_copy[x]['build_details']['node'] == node]
            headers_list.extend(com_jobs)
        headers_list.extend(gsc_jobs)

        return headers_list

    def parse_output(self):
        headers = self.get_headers_by_node()
        test_suites = self.get_test_suites()
        suites_list = self.get_suites_list(test_suites)

        row_list = pd.MultiIndex.from_tuples(suites_list)
        df = pd.DataFrame('', row_list, columns=headers)
        for tc in test_suites:
            for suite, data in self.rdata.items():
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
        return df_1

    def highlight_cells(self, x):
        df_1 = x.copy()
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
        cases_list.remove('failures')
        return cases_list

