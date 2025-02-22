### scraper.py
This module is  responsible for scraping Airbnb. It uses selenium to navigate to a list of cities, scrape the listings, and pushes raw metrics to a database to later be used in the data fusion engine.

To run it, install the python dependencies and run `python scraper.py`, by default it uses the geckodriver (Firefox), so you should see that browser open up unless you have it in headless mode (recommended for prod).
