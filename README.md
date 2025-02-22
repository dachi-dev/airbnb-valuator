### listing scraper
This module is  responsible for scraping Airbnb. It uses selenium to navigate to a list of cities, scrape the listings, and pushes raw metrics to a supabase postgresql database.
To run it, install the python dependencies and run `python scraper_modules/listing_scraper.py`, by default it uses the geckodriver (Firefox), so you should see that browser open up unless you have it in headless mode (recommended for prod).

### database
This module is responsible for the postgresql database on supabase. Requires a .env with

SUPABASE_DB_HOST=

SUPABASE_DB_PORT=

SUPABASE_DB_NAME=

SUPABASE_DB_USER=

SUPABASE_DB_PASSWORD=

