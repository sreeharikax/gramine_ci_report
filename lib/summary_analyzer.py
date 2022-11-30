import os
from datetime import date
import inspect


class SummaryAnalyser():
    def __init__(self):
        self.build_folder = "Gramine_Nightly_{}".format(str(date.today()))
        jk_workspace = "\\\\inecsamba.iind.intel.com\\nfs\\iind\\proj\\ssg\\ubt12_disk001"
        self.dest_path = os.path.join(jk_workspace, "Gramine_Report", self.build_folder)
        self.process_result_folder()

    def copy_results(self):
        if not os.path.exists(self.dest_path): os.makedirs(self.dest_path)
        print("Copying the excel data to {}".format(self.dest_path))
        os.system("robocopy /R:5 /MIR /COPY:DT /DCOPY:T " + self.result_folder + " " + self.dest_path)

    def process_result_folder(self):
        file = inspect.stack()[2].filename
        self.result_folder = os.path.join(os.path.dirname(file), "results", self.build_folder)
        if not os.path.exists(self.result_folder): os.makedirs(self.result_folder)
        self.result_file = '{}/nightly_results.xlsx'.format(self.result_folder)

    @staticmethod
    def table_format(workbook, worksheet, max_row, max_col):
        border_fmt = workbook.add_format({'bottom': 1, 'top': 1, 'left': 1, 'right': 1})
        worksheet.conditional_format(0, 0, max_row, max_col + 1, {'type': 'no_errors', 'format': border_fmt})

    @staticmethod
    def conditional_format(workbook, worksheet, max_row, max_col):

        # Add a format. Light red fill with dark red text.
        format3 = workbook.add_format({'bold': 1,
                                       'bg_color': '#FFC7CE',
                                       'font_color': '#9C0006'})

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

    def process_output(self, writer, out_df, sheet_name):
        out_df.to_excel(writer, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        max_row, max_col = out_df.data.shape

        self.conditional_format(workbook, worksheet, max_row, max_col)
        self.table_format(workbook, worksheet, max_row, max_col)
