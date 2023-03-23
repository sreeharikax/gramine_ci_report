
class GramineNightly:
    def __init__(self, ci_obj, rp, fa, sa):
        self.ci_obj = ci_obj
        self.rp = rp
        self.fa = fa
        self.sa = sa
        self.result_file = ""

    def analyze_and_report(self, nightly_pipeline):
        self.result_file = f"{nightly_pipeline}_results"
        report_result = self.ci_obj.analyze_report(nightly_pipeline)
        # print(report_result)

        print(f"Starting Downstream Analysis for {nightly_pipeline} nightly jobs")
        nightly_df = self.rp.parse_output(report_result)
        summary_df = self.rp.parse_output(report_result, True)

        print("Starting Failure Analysis and Comparison for Downstream jobs")
        failures_df = self.fa.parse_output(report_result)

        result = {"Nightly": summary_df, "Jenkins": nightly_df, "Failures": failures_df}

        self.sa.write_to_excel(self.result_file, result)