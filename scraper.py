import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller
import time
from random import randint
import warnings

from configs.headers_cookies import headers, cookies

warnings.filterwarnings("ignore")


def connect_tor():
    session = requests.session()
    session.proxies = {
        'http': 'socks5h://127.0.0.1:9050', 
        'https': 'socks5h://127.0.0.1:9050'
    }
    return session

def change_tor_ip():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)

session = connect_tor()

all_pages = []

for i in range(1, 10):
    base_url = f"https://jobinja.ir/jobs/latest-job-post-%D8%A7%D8%B3%D8%AA%D8%AE%D8%AF%D8%A7%D9%85%DB%8C-%D8%AC%D8%AF%DB%8C%D8%AF?&sort_by=published_at_desc&page={i}"
    
    res = session.get(base_url, cookies=cookies, headers=headers, timeout=5)
    
    print("Status Code: " + str(res.status_code))
    print(i)
    print()
    
    if res.status_code == 403:
        print("IP blocked, changing IP...")
        change_tor_ip()
        res = session.get(base_url, cookies=cookies, headers=headers)
        time.sleep(randint(3, 7))

    soup = BeautifulSoup(res.text, 'html.parser')
    
    jobs = soup.select('.c-jobListView__titleLink')
    date = soup.select('.c-jobListView__passedDays')
    location = location_span = soup.select("li.c-jobListView__metaItem i.c-icon--place + span")
    
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
        response['company_name'] = soup2.select_one('h2.c-companyHeader__name').get_text(strip=True) if soup2.select_one('h2.c-companyHeader__name') else "Error"
        response['job_category'] = soup2.select_one("li.c-infoBox__item:has(h4.c-infoBox__itemTitle:contains('دسته‌بندی شغلی')) span.black").get_text(strip=True) if soup2.select_one("li.c-infoBox__item:has(h4.c-infoBox__itemTitle:contains('دسته‌بندی شغلی')) span.black") else "Error"
        response['cooperation_type'] = soup2.select_one("li.c-infoBox__item:has(h4.c-infoBox__itemTitle:contains('نوع همکاری')) span.black").get_text(strip=True) if soup2.select_one("li.c-infoBox__item:has(h4.c-infoBox__itemTitle:contains('نوع همکاری')) span.black") else "Error"
        response['salary'] = soup2.select_one("li.c-infoBox__item:has(h4.c-infoBox__itemTitle:contains('حقوق')) span.black").get_text(strip=True) if soup2.select_one("li.c-infoBox__item:has(h4.c-infoBox__itemTitle:contains('حقوق')) span.black") else "Error"
        
        list_all.append(response)
    
    all_pages.append(list_all)
    time.sleep(60)

print(f"Total pages scraped: {len(all_pages)}")