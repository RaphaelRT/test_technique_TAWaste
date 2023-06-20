import pandas as pd
from datetime import datetime
import numpy as np
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import logging
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.DEBUG)
def print(*messages):
    logging.info(' '.join(map(str, messages)))

class ProcessData:
    def __init__(self):
        self.current_directory = os.getcwd()
        self.outputs_directory = f'{self.current_directory}/outputs/'
        self.df = pd.read_excel(f"{self.outputs_directory}new.xlsx")
    
    def filter_by_current_year(self):
        #'YYYY-MM-DD'
        self.df['Date de réalisation'] = pd.to_datetime(self.df['Date de réalisation'])
        current_year = pd.Timestamp.now().year
        #Begin January 1st
        start_date = pd.Timestamp(year=current_year, month=1, day=1)
        self.filtered_df = self.df[self.df['Date de réalisation'] >= start_date]
        min_date = self.filtered_df['Date de réalisation'].min()
        max_date = self.filtered_df['Date de réalisation'].max()

        print("Minimal date :", min_date)
        print("Maximal date :", max_date)
    
    def replace_str_in_df(self, col_name, str_to_replace, replacement):
        matching_rows = self.filtered_df[col_name].str.contains(str_to_replace, case=False, regex=False)
        self.filtered_df.loc[matching_rows, col_name] = replacement

    def create_coords_col(self):
        with open('coords.json') as f:
            coord_data = json.load(f)
            self.filtered_df['Coordonnées'] = self.filtered_df['Lieu de collecte'] + ', ' + self.filtered_df['Rue du lieu de collecte'] + ', ' + self.filtered_df['Code postal du lieu de collecte'].astype(str) + ' ' + self.filtered_df['Ville du lieu de collecte']
            self.filtered_df['Coordonnées'] = self.filtered_df['Coordonnées'].map(coord_data)

    def export(self):
        self.filtered_df.to_excel(f'{self.outputs_directory}data_filtered.xlsx', index=False)
    
    def convert_df_for_gsheets(self, df):
        # Copy the DataFrame to avoid changing the original data
        df = df.copy()

        # Convert Timestamps to strings
        for col in df.select_dtypes(include=[np.datetime64, pd.Timestamp]).columns:
            df[col] = df[col].astype(str)

        # Convert numpy numbers to Python standard types
        for col in df.select_dtypes(include=[np.number]).columns:
            df[col] = df[col].apply(lambda x: int(x) if x == x else "")

        # Convert numpy booleans to Python standard types
        for col in df.select_dtypes(include=[np.bool_]).columns:
            df[col] = df[col].astype(bool)

        # Convert columns containing lists or dictionaries to strings
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                df[col] = df[col].astype(str)

        return df
    
    def export_to_gsheet(self):
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(f'{self.current_directory}/veoliatest-390210-ed110a3b2ee1.json', scope)
        client = gspread.authorize(creds)

        # Check if there is already a spreadsheet with the same name and delete it
        spreadsheets = client.list_spreadsheet_files()
        for spreadsheet in spreadsheets:
            if spreadsheet['name'] == 'veolia_export':
                client.del_spreadsheet(spreadsheet['id'])

        # Create and share a new spreadsheet
        sheet = client.create('veolia_export')
        sheet.share(os.getenv('MAIL_GOOGLE'), perm_type='user', role='writer')
        
        sheet = client.open('veolia_export')
        worksheet = sheet.sheet1
        
        df = self.convert_df_for_gsheets(self.filtered_df)        
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        
        print("Successfully exported to google sheet !")
        
        with open('last_update.txt', 'w') as f:
            f.write(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
        
def main():
    def wait_for_file(filepath, timeout=500):
        """
        Wait for a file to appear at the given filepath. 
        If the file does not appear within the timeout period, raise an exception.
        """
        start_time = time.time()
        while not os.path.exists(filepath):
            time.sleep(1)
            if time.time() - start_time > timeout:
                raise FileNotFoundError(f"{filepath} not found after {timeout} seconds")
        print(f"{filepath} found!")
        # Continue with the rest of your code

    # usage
    wait_for_file(f'{os.getcwd()}/outputs/new.xlsx')

    process_data = ProcessData()
    process_data.filter_by_current_year()
    process_data.replace_str_in_df("Lieu de collecte", "Clinique Belledonne", "ELSAN – CLINIQUE BELLEDONNE")
    process_data.replace_str_in_df("Rue du lieu de collecte", "83 av Gabriel Peri", "83 avenue Gabriel Peri")
    process_data.replace_str_in_df("Lieu de collecte", "TAKE A WASTE/KFC AUBAGNE*", "TAKE A WASTE/KFC AUBAGNE")
    process_data.replace_str_in_df("Rue du lieu de collecte", "*77 RUE DU DOCTEUR ESCAT*", "77 RUE DU DOCTEUR ESCAT")
    process_data.export_to_gsheet()
    process_data.create_coords_col()
    process_data.export()
    
if __name__ == "__main__":
    main()

