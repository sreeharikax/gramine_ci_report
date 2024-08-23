import pandas as pd

class SummaryAnalyser:
    def __init__(self):
        pass

    def parse_output(self, result_data):
        tuple_list = []
        results = []
        err_type = []

        for config, tests in result_data.items():
            for test, out in tests.items():
                if (test != "build_details")  or (test == "build_details" and "err" in out.keys()):
                    tuple_list.append((config, test))
                    results.append(out["err"])
                    err_type.append(out["err_type"])
        index = pd.MultiIndex.from_tuples(tuple_list, names=["Job", "Workload"])
        df = pd.DataFrame('', index=index, columns=["Result", "ErrType"])
        df["Result"] = results
        df["ErrType"] = err_type

        f_df = df.style.apply(self.color_format, axis=None)
        f_df.set_properties(**{'text-align': 'left'})
        return f_df

    def color_format(self, data):
        def apply_style(row):
            if row['ErrType'] == 'ci':
                color = '#FFEB9C'
            elif row["ErrType"] == "other":
                color = 'orange'
            else:
                color = 'white'
            return ['background-color: {}'.format(color) if col == 'Result' else '' for col in data.columns]

        return pd.DataFrame(data.apply(apply_style, axis=1).tolist(), index=data.index, columns=data.columns)

