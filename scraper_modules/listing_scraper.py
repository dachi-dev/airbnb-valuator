#!/usr/bin/env python3
import json
import re
import time
import random
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
NUM_PAGES_TO_SCRAPE = 15  # Number of pages per ZIP code
DELAY_BETWEEN_REQUESTS = 3  # Time delay to avoid detection
CITY_ZIP_FILE = "cities_and_zipcodes.json"  # File containing city names & ZIP codes

def setup_driver(headless=True):
    """Setup Selenium WebDriver."""
    options = Options()
    options.headless = headless
    options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:116.0) Gecko/20100101 Firefox/116.0"
    )
    return webdriver.Firefox(options=options)

driver = setup_driver(headless=False)

def waitForFullListingsLoad(max_wait=5):
    """Waits until listings stop appearing dynamically, up to max_wait seconds."""
    prev_count = 0
    for _ in range(max_wait):
        listing_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/rooms/')]")
        current_count = len(listing_elements)
        if current_count > prev_count:
            prev_count = current_count
            time.sleep(1)  
        else:
            break  

def get_listings_from_page():
    """Extracts unique listing URLs by removing extra query parameters."""
    time.sleep(3)
    listing_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/rooms/')]")
    listings = set()

    for elem in listing_elements:
        url = elem.get_attribute("href")
        if url:
            match = re.search(r"(https://www\.airbnb\.com/rooms/\d+)", url)
            if match:
                listings.add(match.group(1))  # Add only the base URL
    return listings

def generate_random_search_params():
    """Generate diverse search parameters to increase sample independence."""
    start_date = datetime.today() + timedelta(days=random.randint(5, 90))
    end_date = start_date + timedelta(days=random.randint(2, 10))
    guests = random.randint(1, 6)

    price_min = random.choice([0, 50, 100, 150, 200])  
    possible_price_max = [250, 300, 400, 500, 750, 1000]  
    price_max = random.choice([p for p in possible_price_max if p > price_min])

    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), guests, price_min, price_max

def scrape_zipcode(city, zip_code):
    """Scrapes listings for a given city and ZIP code."""
    check_in, check_out, guests, price_min, price_max = generate_random_search_params()
    start_page = random.randint(2, 5)  
    listings = set()

    for page in range(start_page, start_page + NUM_PAGES_TO_SCRAPE):
        search_url = (f"https://www.airbnb.com/s/{zip_code}/homes?"
                      f"check_in={check_in}&check_out={check_out}&adults={guests}"
                      f"&price_min={price_min}&price_max={price_max}"
                      f"&room_types[]=Entire%20home%2Fapt&page={page}")

        print(f"\n🔍 Scraping {city} (ZIP: {zip_code}), Page {page} -> {search_url}")
        driver.get(search_url)
        waitForFullListingsLoad()
        new_listings = get_listings_from_page()
        listings.update(new_listings)

        try:
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Next']"))
            )
            current_url = driver.current_url  
            next_button.click()
            time.sleep(DELAY_BETWEEN_REQUESTS)

            WebDriverWait(driver, 10).until(lambda d: d.current_url != current_url)
            print(f"✅ Moved to next page: {driver.current_url}")
            waitForFullListingsLoad()
        except:
            print(f"❌ No more pages available for {city} (ZIP {zip_code})")
            break  

    print(f"📊 Total unique listings found in {city} (ZIP {zip_code}): {len(listings)}")
    return listings

def estimate_listings_for_city(city, zip_codes):
    """Iterates through ZIP codes for a city and saves unique listings."""
    all_unique_listings = set()
    listings_by_zip = {}

    for zip_code in zip_codes:
        zip_listings = scrape_zipcode(city, zip_code)
        listings_by_zip[zip_code] = list(zip_listings)
        all_unique_listings.update(zip_listings)

    print(f"\n📊 Summary for {city}:")
    print(f"✅ Total unique listings: {len(all_unique_listings)}")

    results = {
        "city": city,
        "total_unique_listings": len(all_unique_listings),
        "listings_by_zip": listings_by_zip,
        "all_listings": list(all_unique_listings)
    }

    with open(f"{city.replace(' ', '_')}_airbnb_listings.json", "w") as f:
        json.dump(results, f, indent=4)

    print(f"\n📂 Listings saved to {city.replace(' ', '_')}_airbnb_listings.json")

def load_cities_from_file(file_path):
    """Reads city names and ZIP codes from a JSON file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found.")
        return {}

if __name__ == "__main__":
    city_data = load_cities_from_file(CITY_ZIP_FILE)

    if not city_data:
        print("❌ No cities found in the file. Exiting.")
        driver.quit()
        exit()

    for city, zip_codes in city_data.items():
        print(f"\n🚀 Starting Airbnb Scraping for {city}")
        estimate_listings_for_city(city, zip_codes)

    driver.quit()

    print("🏁 Scraping complete. All data saved to JSON files.")