from scraper import JobScraper

js=JobScraper()

print(js.scrape_data(start_page=1, end_page=3))