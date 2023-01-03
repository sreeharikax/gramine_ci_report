from lib import GrapheneCIAnalysis
from lib import ResultAnalyser
from lib import FailureAnalyser
from lib import SummaryAnalyser
import pandas as pd


JENKINS_URL = os.environ.get('jenkins_url')
GRAPHENE_NIGHTLY = os.environ.get('nightly_pipeline')
CURATION_NIGHTLY = os.environ.get('curation_nightly')

USER_NAME = os.environ.get('username')
PASSWORD = os.environ.get('password')


if __name__ == "__main__":

    print("Starting Jenkins Nightly Analysis for {}".format(GRAPHENE_NIGHTLY))
    greport = GrapheneCIAnalysis(JENKINS_URL, USER_NAME, PASSWORD)
    report_result = greport.analyze_report(GRAPHENE_NIGHTLY)
    print(report_result)

    print(f"Starting Downstream Analysis for {GRAPHENE_NIGHTLY} nightly jobs")
    rp = ResultAnalyser()
    nightly_df = rp.parse_output(report_result)
    summary_df = rp.parse_output(report_result, True)

    print("Starting Failure Analysis and Comparison for Downstream jobs")
    fa = FailureAnalyser(rp)
    failures_df = fa.parse_output(report_result)

    print("Starting Curation App nightly analysis")
    greport.build_details = rp.build_details = False
    curation_result = greport.analyze_report(CURATION_NIGHTLY)
    curation_df = rp.parse_output(curation_result)

    # Convert the dataframe to an XlsxWriter Excel object.
    sa = SummaryAnalyser()
    try:
        writer = pd.ExcelWriter(sa.result_file, engine='xlsxwriter')
        sa.process_output(writer, summary_df, 'Nightly')
        sa.process_output(writer, nightly_df, 'Jenkins')
        sa.process_output(writer, failures_df, 'Failures')
        sa.process_output(writer, curation_df, 'Curation')
    finally:
        # Close the Pandas Excel writer and output the Excel file.
        writer.save()
    sa.copy_results()

