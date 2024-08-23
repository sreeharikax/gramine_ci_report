import os
from datetime import date
import pandas as pd
import inspect


class ReportGeneration():
    def __init__(self, dest_path):
        self.build_folder = "Gramine_Nightly_{}".format(str(date.today()))
        self.dest_path = os.path.join(dest_path, "Gramine_Report", self.build_folder)

    def copy_results(self):
        if not os.path.exists(self.dest_path): os.makedirs(self.dest_path)
        print("Copying the excel data to {}".format(self.dest_path))
        os.system("cp -f " + self.result_file + " " + self.dest_path)

    def process_result_folder(self, pipeline):
        file = inspect.stack()[2].filename
        self.result_folder = os.path.join(os.path.dirname(file), "results", self.build_folder)
        if not os.path.exists(self.result_folder): os.makedirs(self.result_folder)
        pipeline_no = os.environ.get("pipeline_no")
        self.result_file = f'{self.result_folder}/{pipeline}_{pipeline_no}.xlsx'

    @staticmethod
    def table_format(workbook, worksheet, max_row, max_col):
        border_fmt = workbook.add_format({'bottom': 1, 'top': 1, 'left': 1, 'right': 1, "align": "left"})
        worksheet.conditional_format(0, 0, max_row, max_col + 1, {'type': 'no_errors', 'format': border_fmt})

    @staticmethod
    def conditional_format(workbook, worksheet, max_row, max_col):

        # Add a format. Light red fill with dark red text.
        format3 = workbook.add_format({'bold': 1,
                                       'bg_color': '#FFC7CE',
                                       'font_color': '#9C0006'})

        # Add a format. Light green text.
        format4 = workbook.add_format({'bold': 1,
                                       'bg_color': '#76933C'})

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
                                                 'value': '"FIXED"',
                                                 'format': format4})

        worksheet.conditional_format(0, 0, max_row, max_col+1, {'type': 'cell',
                                                 'criteria': 'equal to',
                                                 'value': '"ABORTED"',
                                                 'format': format3})

        worksheet.conditional_format(0, 0, max_row, max_col + 1, {'type': 'cell',
                                                                  'criteria': 'equal to',
                                                                  'value': '"FAILURE"',
                                                                  'format': format3})

        worksheet.conditional_format(0, 0, max_row, max_col + 1, {'type': 'cell',
                                                                  'criteria': 'equal to',
                                                                  'value': '"UNKNOWN"',
                                                                  'format': format3})

        worksheet.freeze_panes(3, 2)


    def write_to_excel(self, pipeline, data_dict):
        self.process_result_folder(pipeline)
        writer = pd.ExcelWriter(self.result_file, engine='xlsxwriter')
        try:
            for name, r_df in data_dict.items():
                self.process_output(writer, r_df, name)
        finally:
            # Close the Pandas Excel writer and output the Excel file.
            # writer.save()
            writer.close()

    def process_output(self, writer, out_df, sheet_name):
        max_row, max_col = out_df.data.shape
        if "ErrType" in out_df.columns:
            col_list = out_df.columns.drop("ErrType")
            max_col -= 1
            out_df.to_excel(writer, sheet_name=sheet_name, columns=col_list)
        else:
            out_df.to_excel(writer, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        left_align = workbook.add_format({'bold': 1, 'align': 'left'})

        if sheet_name == "Summary":
            for i, idx in enumerate(out_df.index):
                worksheet.write(i + 1, 0, idx[0], left_align)
                worksheet.write(i + 1, 1, idx[1], left_align)

        self.conditional_format(workbook, worksheet, max_row, max_col)
        self.table_format(workbook, worksheet, max_row, max_col)
