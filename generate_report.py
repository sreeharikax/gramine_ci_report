from lib import GrapheneCIAnalysis
from lib import ResultAnalyser
from lib import FailureAnalyser
from lib import SummaryAnalyser
import pandas as pd


JENKINS_URL = os.environ.get('jenkins_url')
NIGHTLY_JOB = os.environ.get('nightly_pipeline')

USER_NAME = os.environ.get('username')
PASSWORD = os.environ.get('password')


if __name__ == "__main__":

    print("Starting Jenkins Nightly Analysis for {}".format(NIGHTLY_JOB))
    greport = GrapheneCIAnalysis(JENKINS_URL, USER_NAME, PASSWORD)
    report_result = greport.analyze_report(NIGHTLY_JOB)
    print(report_result)

    print("Starting Downstream Analysis for {}".format(NIGHTLY_JOB))
    rp = ResultAnalyser(report_result)
    nightly_df = rp.parse_output()
    summary_df = rp.parse_output(True)

    print("Starting Failure Analysis and Comparison for Downstream jobs")
    fa = FailureAnalyser(report_result)
    failures_df = fa.parse_output()

    # Convert the dataframe to an XlsxWriter Excel object.
    sa = SummaryAnalyser()
    try:
        writer = pd.ExcelWriter(sa.result_file, engine='xlsxwriter')
        sa.process_output(writer, summary_df, 'Nightly')
        sa.process_output(writer, nightly_df, 'Jenkins')
        sa.process_output(writer, failures_df, 'Failures')
    finally:
        # Close the Pandas Excel writer and output the Excel file.
        writer.save()
    sa.copy_results()

