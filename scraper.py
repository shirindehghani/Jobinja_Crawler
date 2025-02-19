import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller
import json
import re
from datetime import datetime, timedelta
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from configs.headers_cookies import headers, cookies

import warnings
warnings.filterwarnings("ignore")


class JobScraper:
    def __init__(self, config_path="./configs/configs.json"):
        self.session = None
        self.load_config(config_path)
        self.connect_tor()

    def load_config(self, config_path):
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as config_file:
                my_config = json.load(config_file)
        except IOError:
            logger.error("Specify the correct config path.")
            return

        self.http = my_config['http']
        self.https = my_config['https']
        self.port = my_config['port']
        self.base_url = my_config['jobinja_base_url']
        self.jobs_titles_tags = my_config['jobs_titles_tags']
        self.jobs_titles_created_tags = my_config['jobs_titles_created_tags']
        self.company_location_tags = my_config['company_location_tags']
        self.company_name_tags = my_config['company_name_tags']
        self.job_category_tags = my_config['job_category_tags']
        self.cooperation_type_tags = my_config['cooperation_type_tags']
        self.salary_tags = my_config['salary_tags']

    def connect_tor(self):
        """Create a persistent Tor session with retries."""
        self.session = requests.session()
        self.session.proxies = {'http': self.http, 'https': self.https}

        retry_strategy = Retry(
            total=5,
            backoff_factor=0.3, 
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def change_tor_ip(self):
        with Controller.from_port(port=self.port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)

    def farsi_to_english(self, num_str):
        return num_str.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    def fetch_page(self, url, retry_once=True):
        try:
            response = self.session.get(url, cookies=cookies, headers=headers)
            if response.status_code == 403 and retry_once:
                logger.warning("Blocked! Changing IP and retrying...")
                self.change_tor_ip()
                return self.fetch_page(url, retry_once=False)
            return response if response.status_code == 200 else None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def extract_job_details(self, soup):
        return {
            "companyName": soup.select_one(self.company_name_tags).get_text(strip=True) if soup.select_one(self.company_name_tags) else "N/A",
            "jobCategory": soup.select_one(self.job_category_tags).get_text(strip=True) if soup.select_one(self.job_category_tags) else "N/A",
            "cooperationType": soup.select_one(self.cooperation_type_tags).get_text(strip=True) if soup.select_one(self.cooperation_type_tags) else "N/A",
            "salary": soup.select_one(self.salary_tags).get_text(strip=True) if soup.select_one(self.salary_tags) else "N/A",
        }

    def process_job_page(self, job_url):
        res = self.fetch_page(job_url)
        return self.extract_job_details(BeautifulSoup(res.text, 'html.parser')) if res else None

    def scrape_data(self, start_page=1, end_page=3):
        all_jobs = []
        base_url_pattern = f"{self.base_url}jobs/latest-job-post-%D8%A7%D8%B3%D8%AA%D8%AE%D8%AF%D8%A7%D9%85%DB%8C-%D8%AC%D8%AF%DB%8C%D8%AF?&sort_by=published_at_desc&page="

        with ThreadPoolExecutor(max_workers=10) as executor:
            for page_num in range(end_page, start_page, -1):
                logger.info(f"We are in {page_num} page!")
                page_url = base_url_pattern + str(page_num)
                res = self.fetch_page(page_url)
                if not res:
                    continue

                soup = BeautifulSoup(res.text, 'html.parser')
                job_elements = soup.select(self.jobs_titles_tags)
                date_elements = soup.select(self.jobs_titles_created_tags)
                location_elements = soup.select(self.company_location_tags)

                job_urls = [job.get('href') for job in job_elements if job]

                future_to_url = {executor.submit(self.process_job_page, job_url): job_url for job_url in job_urls}

                for future in as_completed(future_to_url):
                    job_url = future_to_url[future]
                    try:
                        job_details = future.result()
                        if job_details:
                            job_index = job_urls.index(job_url)
                            date_text = self.farsi_to_english(date_elements[job_index].get_text(strip=True)) if date_elements[job_index] else "N/A"
                            job_date = (datetime.now().date() if "امروز" in date_text else datetime.now().date() - timedelta(days=int(re.search(r'\d+', date_text).group())) if re.search(r'\d+', date_text) else "N/A")

                            all_jobs.append({
                                "jobTitle": job_elements[job_index].get_text(strip=True) if job_elements[job_index] else "N/A",
                                "date": str(job_date),
                                "location": location_elements[job_index].get_text(strip=True) if location_elements[job_index] else "N/A",
                                "url": job_url,
                                "key": re.search(r'/jobs/([^/]+)/', job_url).group(1) if re.search(r'/jobs/([^/]+)/', job_url) else None,
                                **job_details
                            })
                    except Exception as e:
                        logger.exception(f"Error processing job {job_url}: {e}")

            logger.info(f"Processing start_page: {start_page}")
            page_url = base_url_pattern + str(start_page)
            res = self.fetch_page(page_url)
            if res:
                soup = BeautifulSoup(res.text, 'html.parser')
                job_elements = soup.select(self.jobs_titles_tags)
                date_elements = soup.select(self.jobs_titles_created_tags)
                location_elements = soup.select(self.company_location_tags)

                job_urls = [job.get('href') for job in job_elements if job]

                future_to_url = {executor.submit(self.process_job_page, job_url): job_url for job_url in job_urls}

                for future in as_completed(future_to_url):
                    job_url = future_to_url[future]
                    try:
                        job_details = future.result()
                        if job_details:
                            job_index = job_urls.index(job_url)
                            date_text = self.farsi_to_english(date_elements[job_index].get_text(strip=True)) if date_elements[job_index] else "N/A"
                            job_date = (datetime.now().date() if "امروز" in date_text else datetime.now().date() - timedelta(days=int(re.search(r'\d+', date_text).group())) if re.search(r'\d+', date_text) else "N/A")

                            all_jobs.append({
                                "jobTitle": job_elements[job_index].get_text(strip=True) if job_elements[job_index] else "N/A",
                                "date": str(job_date),
                                "location": location_elements[job_index].get_text(strip=True) if location_elements[job_index] else "N/A",
                                "url": job_url,
                                "key": re.search(r'/jobs/([^/]+)/', job_url).group(1) if re.search(r'/jobs/([^/]+)/', job_url) else None,
                                **job_details
                            })
                    except Exception as e:
                        logger.exception(f"Error processing job {job_url}: {e}")

        logger.info("Scraping completed!")
        return all_jobs
