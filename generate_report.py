from lib import JenkinsAnalysis
from lib import ResultAnalyser
from lib import FailureAnalyser
from lib import SummaryAnalyser
from lib import ReportGeneration
from data.constants import *
import os

del os.environ["http_proxy"]
del os.environ["https_proxy"]

if __name__ == "__main__":

    print("Starting Jenkins Nightly Analysis for {}".format(NIGHTLY_PIPELINE))
    greport = JenkinsAnalysis(JENKINS_URL, USER_NAME, PASSWORD)
    rp = ResultAnalyser()
    fa = FailureAnalyser(rp, greport)
    sa = SummaryAnalyser()
    rg = ReportGeneration(REPORTS_PATH)

    if "curation" in NIGHTLY_PIPELINE:
        greport.build_details = rp.build_details = False

    report_result = greport.analyze_report(NIGHTLY_PIPELINE)
    
    print(f"Starting Downstream Analysis for {NIGHTLY_PIPELINE} nightly jobs")
    nightly_df = rp.parse_output(report_result)

    print("Starting Failure Analysis and Comparison for Downstream jobs")
    failures_df = fa.parse_output(report_result)
    summary_df = sa.parse_output(fa.summary_data)

    result = {"Nightly": nightly_df, "Failures": failures_df, "Summary": summary_df}
    rg.write_to_excel(NIGHTLY_PIPELINE, result)

    rg.copy_results()
