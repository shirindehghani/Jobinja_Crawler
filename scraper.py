import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller
import json
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

from configs.headers_cookies import headers, cookies


class JobScraper:
    def __init__(self, config_path="./configs/configs.json"):
        self.session = None
        self.load_config(config_path)

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
        self.jobinja_base_url = my_config['jobinja_base_url']
        self.start_sleep = my_config['start_sleep']
        self.end_sleep = my_config['end_sleep']
        self.jobs_titles_tags = my_config['jobs_titles_tags']
        self.jobs_titles_created_tags = my_config['jobs_titles_created_tags']
        self.company_location_tags = my_config['company_location_tags']
        self.company_name_tags = my_config['company_name_tags']
        self.job_category_tags = my_config['job_category_tags']
        self.cooperation_type_tags = my_config['cooperation_type_tags']
        self.salary_tags = my_config['salary_tags']

    def connect_tor(self):
        """Create a session using Tor proxy with retry strategy."""
        self.session = requests.session()
        self.session.proxies = {'http': self.http, 'https': self.https}

        retry_strategy = Retry(
            total=5,
            backoff_factor=0.5,  # Reduce sleep time
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
            raise_on_status=False
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def change_tor_ip(self):
        """Change Tor IP when blocked."""
        with Controller.from_port(port=self.port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)

    def fetch_page(self, url):
        """Fetch a webpage with retry and error handling."""
        try:
            response = self.session.get(url, cookies=cookies, headers=headers)
            if response.status_code == 403:
                logger.warning("IP blocked, changing IP...")
                self.change_tor_ip()
                response = self.session.get(url, cookies=cookies, headers=headers)
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def process_job_page(self, job_url):
        """Fetch and extract job details concurrently."""
        res2 = self.fetch_page(job_url)
        if not res2 or res2.status_code != 200:
            return None

        soup2 = BeautifulSoup(res2.text, 'html.parser')
        return {
            "company_name": soup2.select_one(self.company_name_tags).get_text(strip=True) if soup2.select_one(self.company_name_tags) else "Error",
            "job_category": soup2.select_one(self.job_category_tags).get_text(strip=True) if soup2.select_one(self.job_category_tags) else "Error",
            "cooperation_type": soup2.select_one(self.cooperation_type_tags).get_text(strip=True) if soup2.select_one(self.cooperation_type_tags) else "Error",
            "salary": soup2.select_one(self.salary_tags).get_text(strip=True) if soup2.select_one(self.salary_tags) else "Error",
        }

    def scrape_data(self, start_page=1, end_page=3):
        """Main function to scrape job listings with concurrent fetching."""
        if not self.session:
            self.connect_tor()

        all_pages = []
        base_url_pattern = f"{self.jobinja_base_url}jobs/latest-job-post-%D8%A7%D8%B3%D8%AA%D8%AE%D8%AF%D8%A7%D9%85%DB%8C-%D8%AC%D8%AF%DB%8C%D8%AF?&sort_by=published_at_desc&page="

        for i in range(start_page, end_page):
            url = base_url_pattern + str(i)
            res = self.fetch_page(url)

            if not res or res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, 'html.parser')
            jobs = soup.select(self.jobs_titles_tags)
            dates = soup.select(self.jobs_titles_created_tags)
            locations = soup.select(self.company_location_tags)

            job_list = []
            job_urls = [job['href'] for job in jobs if job]

            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_job = {executor.submit(self.process_job_page, job_url): job_url for job_url in job_urls}

                for future in as_completed(future_to_job):
                    job_url = future_to_job[future]
                    try:
                        job_details = future.result()
                        if job_details:
                            job_index = job_urls.index(job_url)
                            job_list.append({
                                "status_code": res.status_code,
                                "job_title": jobs[job_index].get_text(strip=True) if jobs[job_index] else "Error",
                                "date": dates[job_index].get_text(strip=True) if dates[job_index] else "Error",
                                "location": locations[job_index].get_text(strip=True) if locations[job_index] else "Error",
                                "url": job_url,
                                **job_details
                            })
                    except Exception as e:
                        logger.error(f"Error processing job {job_url}: {e}")

            all_pages.append(job_list)

        logger.info("Scraping finished!")
        return all_pages
