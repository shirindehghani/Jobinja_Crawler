import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller
import time
from random import randint
import warnings
import json
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from configs.headers_cookies import headers, cookies

warnings.filterwarnings("ignore")


class JobScraper:
    def __init__(self):
        self.http=None
        self.https=None
        self.port=None
        self.jobinja_base_url=None
        self.start_sleep=None
        self.end_sleep=None
        self.jobs_titles_tags=None
        self.jobs_titles_created_tags=None
        self.company_location_tags=None
        self.company_name_tags=None
        self.job_category_tags=None
        self.cooperation_type_tags=None
        self.salary_tags=None
        self.read_config(config_path="./configs/configs.json")
    
    def read_config(self, config_path):
        try:
            config_file=open(config_path,'r')
        except IOError:
            logger.error('Specify the correct config path.')
        else:
            my_config=json.load(config_file)
            config_file.close()
            self.http=my_config['http']
            self.https=my_config['https']
            self.port=my_config['port']
            self.jobinja_base_url=my_config['jobinja_base_url']
            self.start_sleep=my_config['start_sleep']
            self.end_sleep=my_config['end_sleep']
            self.jobs_titles_tags=my_config['jobs_titles_tags']
            self.jobs_titles_created_tags=my_config['jobs_titles_created_tags']
            self.company_location_tags=my_config['company_location_tags']
            self.company_name_tags=my_config['company_name_tags']
            self.job_category_tags=my_config['job_category_tags']
            self.cooperation_type_tags=my_config['cooperation_type_tags']
            self.salary_tags=my_config['salary_tags']

    def connect_tor(self):
        session = requests.session()
        session.proxies = {
            'http': self.http,
            'https': self.https
        }
 
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
            raise_on_status=False
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def change_tor_ip(self):
        with Controller.from_port(port=self.port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)

    def scrape_data(self, start_page=1, end_page=3):
        session = self.connect_tor()

        all_pages = []

        for i in range(start_page, end_page):
            base_url = str(self.jobinja_base_url)+f"jobs/latest-job-post-%D8%A7%D8%B3%D8%AA%D8%AE%D8%AF%D8%A7%D9%85%DB%8C-%D8%AC%D8%AF%DB%8C%D8%AF?&sort_by=published_at_desc&page={i}"

            try:
                res = session.get(base_url, cookies=cookies, headers=headers)
                print(f"Status Code at page {i}: " + str(res.status_code))
                time.sleep(randint(self.start_sleep, self.end_sleep))

                if res.status_code == 403:
                    print("IP blocked, changing IP...")
                    self.change_tor_ip()
                    res = session.get(base_url, cookies=cookies, headers=headers)
                    time.sleep(randint(self.start_sleep, self.end_sleep))

                soup = BeautifulSoup(res.text, 'html.parser')

                jobs = soup.select(self.jobs_titles_tags)
                date = soup.select(self.jobs_titles_created_tags)
                location = soup.select(self.company_location_tags)

                list_all = []

                for i in range(len(jobs)):
                    response = {"status_code": res.status_code,
                                "job_title": None,
                                "company_name": None,
                                "location": None,
                                "cooperation_type": None,
                                "job_category": None,
                                "salary": None,
                                "date": None,
                                "url": None}

                    response['job_title'] = jobs[i].get_text(strip=True) if jobs[i] else "Error"
                    response['url'] = jobs[i]['href']
                    response['date'] = date[i].get_text(strip=True) if date[i] else "Error"
                    response['location'] = location[i].get_text(strip=True) if location[i] else "Error"

                    res2 = session.get(response['url'], cookies=cookies, headers=headers)
                    time.sleep(randint(3, 7))

                    soup2 = BeautifulSoup(res2.text, 'html.parser')
                    response['company_name'] = soup2.select_one(self.company_name_tags).get_text(strip=True) if soup2.select_one(self.company_name_tags) else "Error"
                    response['job_category'] = soup2.select_one(self.job_category_tags).get_text(strip=True) if soup2.select_one(self.job_category_tags) else "Error"
                    response['cooperation_type'] = soup2.select_one(self.cooperation_type_tags).get_text(strip=True) if soup2.select_one(self.cooperation_type_tags) else "Error"
                    response['salary'] = soup2.select_one(self.salary_tags).get_text(strip=True) if soup2.select_one(self.salary_tags) else "Error"
                    list_all.append(response)

                all_pages.append(list_all)
                time.sleep(60)

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {i}: {e}")

        logger.info("Scraping finished!")
        return all_pages
