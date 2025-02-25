from scraper import JobScraper

js=JobScraper()

print(len(js.scrape_data(start_page=1, end_page=100)))