# Jobinja Job Scraper

This repository contains a Python-based web scraper designed to scrape job listings from [Jobinja](https://jobinja.ir), a Persian job board. The scraper collects job details including job title, company name, location, job category, cooperation type, salary, and posting date for each job listing.

## Features
- Scrapes the latest job posts from Jobinja.
- Collects detailed job information from each job listing page.
- Implements rate-limiting and IP rotation to prevent IP blocking using **Tor**.
- Utilizes `requests`, `BeautifulSoup`, and `stem` to handle requests and parse HTML content.

## Requirements

- **Python 3.x**
- **Libraries**:
  - `requests`
  - `BeautifulSoup4`
  - `stem` (for Tor control)
  - `time`
  - `random`
  - `warnings`

Install the required libraries by running:

```bash
pip install requests beautifulsoup4 stem



