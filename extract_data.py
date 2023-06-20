import time
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import selenium.webdriver.remote.remote_connection as remote_connection
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import pandas as pd
import logging

logging.basicConfig(level=logging.DEBUG)
remote_connection.LOGGER.setLevel(logging.DEBUG)
def print(*messages):
    logging.info(' '.join(map(str, messages)))

load_dotenv()

current_directory = os.getcwd()
outputs_directory = f'{current_directory}/outputs/'

# Check if directory exist
if not os.path.exists(outputs_directory):
    os.makedirs(outputs_directory)

class VeoliaClient:
    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2866.71 Safari/537.36')
        self.chrome_options.add_argument("--disable-infobars")
        self.chrome_options.add_argument("--disable-notifications")
        self.chrome_options.add_argument("--disable-infobars")
        self.chrome_options.add_argument("--start-maximized")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--verbose")
        self.chrome_options.add_argument("--whitelisted-ips=''")
        self.chrome_options.add_experimental_option("prefs", { \
            "profile.default_content_setting_values.media_stream_mic": 1, 
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.geolocation": 1, 
            "profile.default_content_setting_values.notifications": 1 
        })
        self.chrome_options.add_experimental_option("prefs", {
            "download.default_directory": outputs_directory,
            "download.prompt_for_download": False,
        })
        self.chrome_options.add_argument('--headless')
        self.webdriver_service = ChromeDriverManager().install()
        self.driver = webdriver.Chrome(executable_path=self.webdriver_service, options=self.chrome_options)
        self.url = 'https://clients.recyclage.veolia.fr/'
        self.email = os.getenv('VEOLIA_EMAIL')
        self.password = os.getenv('VEOLIA_PASSWORD')
        print("init")
    
    def login(self):
        self.driver.get(self.url)
        email_input = self.driver.find_element(By.XPATH, '//input[@name="email"]')
        password_input = self.driver.find_element(By.XPATH, '//input[@name="password"]')
        email_input.send_keys(self.email)
        time.sleep(1)
        password_input.send_keys(self.password)
        time.sleep(1)
        login_button = self.driver.find_element(By.XPATH, '//button[.//div[text()=" Se connecter "]]')
        login_button.click()
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, '//span[contains(text(), "Modules")]')))
        print("Logged successfully !")
    
    def download_prestation_excel(self):
        self.driver.get(f"{self.url}suivre-mes-prestations/evacuation-de-dechets/realisees")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//a[contains(., "Export Excel")]')))
        export_excel_link = self.driver.find_element(By.XPATH, '//a[contains(., "Export Excel")]')
        link_url = export_excel_link.get_attribute('href')
        while "api" not in link_url:
            print(f"Trying to get good download link")
            export_excel_link = self.driver.find_element(By.XPATH, '//a[contains(., "Export Excel")]')
            link_url = export_excel_link.get_attribute('href')
        export_excel_link.click()
        print(f"Final download link : {link_url}")
        time.sleep(1)
        # Wait for the download to complete
        while not os.path.exists(f'{outputs_directory}veolia_prestation.xlsx'):
            print("Download in progress...")
            time.sleep(1)
        print("Download Complete !")
        os.rename(f'{outputs_directory}veolia_prestation.xlsx', f'{outputs_directory}new.xlsx')
        print("new.xlsx created !")
        
    
    def compare_and_update_prestations(self):
        new_file_path = f'{outputs_directory}new.xlsx'
        old_file_path = f'{outputs_directory}old.xlsx'
        
        if not os.path.exists(old_file_path):
            pd.read_excel(new_file_path).to_excel(old_file_path, index=False)
            print("old.xlsx created !")

        old_df = pd.read_excel(old_file_path)
        new_df = pd.read_excel(new_file_path)
        
        if old_df.equals(new_df):
            print("Identical file detected with previous version, no change needed !")
        else:
            print("Different file detected, update of old.xlsx !")
            new_df.to_excel(old_file_path, index=False)
            print("old.xlsx updated !")    

    
    def close(self):
        self.driver.quit()

def main():
    veolia_client = VeoliaClient()
    veolia_client.login()
    veolia_client.download_prestation_excel()
    veolia_client.close()
    veolia_client.compare_and_update_prestations()
    
if __name__ == "__main__":
    main()