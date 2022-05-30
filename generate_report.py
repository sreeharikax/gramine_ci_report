from lib import GrapheneCIAnalysis
from lib import ResultAnalyser
from lib import FailureAnalyser
from datetime import date
import pandas as pd
import os

JENKINS_URL = os.environ.get('jenkins_url')
NIGHTLY_JOB = os.environ.get('nightly_pipeline')

USER_NAME = os.environ.get('username')
PASSWORD = os.environ.get('password')


def copy_results(result_folder, build_folder):
    jk_workspace = os.environ.get('dest_path')
    jk_workspace_path = os.path.join(jk_workspace, "Gramine_Report", build_folder)
    if not os.path.exists(result_folder): os.makedirs(jk_workspace_path)
    print("Copying the excel data to {}".format(jk_workspace_path))
    os.system("robocopy /MIR /COPY:DT /DCOPY:T " + result_folder + " " + jk_workspace_path)

if __name__ == "__main__":

    print("Starting Jenkins Nightly Analysis for {}".format(NIGHTLY_JOB))
    greport = GrapheneCIAnalysis(JENKINS_URL, USER_NAME, PASSWORD)
    report_result = greport.analyze_report(NIGHTLY_JOB)
    print(report_result)

    print("Starting Downstream Analysis for {}".format(NIGHTLY_JOB))
    rp = ResultAnalyser(report_result)
    nightly_df = rp.parse_output()

    print("Starting Failure Analysis and Comparison for Downstream jobs")
    fa = FailureAnalyser(report_result)
    failures_df = fa.parse_output()

    try:
        build_folder = "Gramine_Nightly_{}".format(str(date.today()))
        result_folder = os.path.join(os.path.dirname(__file__), "results", build_folder)
        if not os.path.exists(result_folder): os.makedirs(result_folder)
        writer = pd.ExcelWriter('{}/nightly_results.xlsx'.format(result_folder), engine='xlsxwriter')

        # Convert the dataframe to an XlsxWriter Excel object.
        nightly_df.to_excel(writer, sheet_name='Nightly')

        # Convert the dataframe to an XlsxWriter Excel object.
        failures_df.to_excel(writer, sheet_name='Failures')

        # Get the xlsxwriter workbook and worksheet objects.
        workbook = writer.book
        worksheet = writer.sheets['Nightly']
        worksheet2 = writer.sheets['Failures']

        max_row, max_col = nightly_df.data.shape

        # Add a format. Light red fill with dark red text.
        format3 = workbook.add_format({'bold': 1,
                                       'bg_color': '#FFC7CE',
                                       'font_color': '#9C0006'})

        border_fmt = workbook.add_format({'bottom': 1, 'top': 1, 'left': 1, 'right': 1})
        worksheet.conditional_format(0, 0, max_row, max_col+1, {'type': 'no_errors', 'format': border_fmt})

        # Apply a conditional format to the cell range.
        worksheet.conditional_format(0, 0, max_row, max_col+1, {'type': 'cell',
                                                 'criteria': 'equal to',
                                                 'value': '"Failed"',
                                                 'format': format3})

        worksheet.conditional_format(0, 0, max_row, max_col+1, {'type': 'cell',
                                                 'criteria': 'equal to',
                                                 'value': '"Regression"',
                                                 'format': format3})

        worksheet.conditional_format(0, 0, max_row, max_col+1, {'type': 'cell',
                                                 'criteria': 'equal to',
                                                 'value': '"ABORTED"',
                                                 'format': format3})
        worksheet.freeze_panes(3, 2)
        worksheet2.freeze_panes(2, 2)
    finally:
        # Close the Pandas Excel writer and output the Excel file.
        writer.save()

    copy_results(result_folder, build_folder)
