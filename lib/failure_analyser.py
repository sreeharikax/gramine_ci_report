from lib.result_analyser import ResultAnalyser
import pandas as pd
import itertools
import os


class FailureAnalyser(ResultAnalyser):
    def __init__(self, ra):
        self.rg = ra
        self.fdata = {}
        self.f_list = {}
        self.failures_list = os.path.join(os.path.dirname(__file__), "../data/failures_list.csv")

    def get_suites_list(self, test_list):
        comb_list = []
        for key, value in self.rg.rdata.items():
            # if "gsc" not in key:
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
        headers_list = [x for x in self.rg.rdata.keys()  if (self.rg.rdata[x].get("build_details", {}).get("result", "") != "SUCCESS")]
        return headers_list

    def parse_output(self, output, summary=False):
        self.rg.rdata = output
        headers = self.get_headers()
        test_suites = self.rg.get_test_suites(summary)
        test_list = test_suites.copy()
        suites_list = self.get_suites_list(test_list)
        self.fetch_known_failures()
        row_list = pd.MultiIndex.from_tuples(suites_list)
        df = pd.DataFrame('', row_list, columns=headers)
        try:
            for tc in test_list:
                for suite in headers:
                    data = self.fdata[suite]
                    res = data.get(tc, {})
                    if res != None:
                        if tc == "build_details":
                            for key in self.rg.build_keys:
                                df.loc[(tc, key), suite] = res.get(key)
                        else:
                            for index, val in enumerate(res):
                                df.loc[(tc, index), suite] = val
        except Exception as e:
            print("Exception Occured during failure analysis for suite {} and tc {} and exception is {}".format(suite, tc, e))

        f_df = df.style.apply(self.color_format)
        f_df.set_properties(**{'text-align': 'center'})
        return f_df

    def fetch_known_failures(self):
        self.f_list = pd.read_csv(self.failures_list)

    def get_node_failures(self, node, sgx_mode):
        return list(self.f_list.loc[(self.f_list['Node'] == node) & (self.f_list['SGX'] == sgx_mode)]['Test'])

    def color_format(self, f_df):
        node_name = f_df['build_details']['node']
        sgx_mode = f_df['build_details']['Mode']
        self.node_failures = self.get_node_failures(node_name, sgx_mode)
        df_1 = f_df.copy()
        for index_1, index_2 in f_df.keys():
            if index_1 == "build_details" and index_2 == "result" and df_1["build_details"]["result"] == "ABORTED":
                df_1.loc[index_1, index_2] = 'background-color: #FFC000;'
            elif (df_1.loc[index_1, index_2] in self.node_failures) or df_1.loc[index_1, index_2] == '' or index_1 == "build_details":
                df_1.loc[index_1, index_2] = '' #background-color: #FFC000;
            else:
                df_1.loc[index_1, index_2] = 'background-color: orange;'
        return df_1
