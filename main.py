from scraper import JobScraper

js=JobScraper()

print(len(js.scrape_data(start_page=1000, end_page=1099)))