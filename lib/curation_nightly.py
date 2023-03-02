
class CurationNightly:
    def __init__(self, ci_obj, rp, fa, sa):
        self.ci_obj = ci_obj
        self.rp = rp
        self.fa = fa
        self.sa = sa
        self.result_file = ""

    def analyze_and_report(self, nightly_pipeline):
        self.result_file = f"{nightly_pipeline}_results"
        print("Starting Curation App nightly analysis")
        report_result = self.ci_obj.analyze_report(nightly_pipeline)
        print(report_result)

        self.ci_obj.build_details = self.rp.build_details = False
        curation_result = self.ci_obj.analyze_report(nightly_pipeline)
        curation_df = self.rp.parse_output(curation_result)
        failures_df = self.fa.parse_output(curation_result)

        # Convert the dataframe to an XlsxWriter Excel object.
        result = {"Curation": curation_df, "Failures": failures_df}

        self.sa.write_to_excel(self.result_file, result)