#!/usr/bin/env python3
import sys
import json
import os
import re
import time
import threading
import random
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database_modules.database import insert_listing, get_db_connection
from urllib.parse import urlencode

# Configuration
CITY_ZIP_FILE = os.path.join(os.path.dirname(__file__), "cities_and_zipcodes.json")

# Supabase/PostgreSQL connection parameters (set these via your environment or update defaults)
DB_HOST = os.environ.get("SUPABASE_DB_HOST", "your-supabase-host.supabase.co")
DB_PORT = os.environ.get("SUPABASE_DB_PORT", "5432")
DB_NAME = os.environ.get("SUPABASE_DB_NAME", "postgres")
DB_USER = os.environ.get("SUPABASE_DB_USER", "your-db-user")
DB_PASSWORD = os.environ.get("SUPABASE_DB_PASSWORD", "your-db-password")

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

global paused
paused = False

def pause_resume_listener():
    global paused
    while True:
        command = input("Type 'pause' to pause, 'resume' to continue: ")
        if command.lower() == "pause":
            paused = True
            print("⏸️ Paused scraping...")
        elif command.lower() == "resume":
            paused = False
            print("▶️ Resuming scraping...")

def wait_for_resume():
    global paused
    while paused:
        time.sleep(1)

def waitForFullListingsLoad(max_wait=5):
    """Waits until there are more than 2 listings loaded, or until max_wait seconds have passed."""
    elapsed = 0
    while elapsed < max_wait:
        listing_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/rooms/')]")
        if len(listing_elements) > 2:
            break
        elapsed += 1
def get_listings_from_page():
    """Extracts unique listing URLs by removing extra query parameters."""
    listing_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/rooms/')]")
    listings = set()
    for elem in listing_elements:
        url = elem.get_attribute("href")
        if url:
            match = re.search(r"(https://www\.airbnb\.com/rooms/(\d+))", url)
            if match:
                listings.add(match.group(1))  # Return the base URL; listing ID is in group(2)
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
def randomize_sleep(base_min=1, base_max=3, extended_min=180, extended_max=300, extended_prob=0.01):
    """
    Sleep for a random duration between base_min and base_max seconds.
    Occasionally, sleep for an extended period between extended_min and extended_max seconds
    based on the probability extended_prob.
    """
    if random.random() < extended_prob:
        sleep_time = random.uniform(extended_min, extended_max)
        print(f"⏳ Taking an extended break for {sleep_time:.2f} seconds...")
    else:
        sleep_time = random.uniform(base_min, base_max)
        print(f"⏳ Sleeping for {sleep_time:.2f} seconds...")
    time.sleep(sleep_time)

# --- PARSING FUNCTIONS ---

def parse_listing_details(url):
    """
    Visits the listing page and extracts relevant data:
      - listing_id: extracted from the URL.
      - title: the listing title.
      - room_type: e.g. "Studio" if indicated.
      - bedroom_count: number of bedrooms.
      - bathroom_count: number of bathrooms.
      - price: the price per night.
      
    It parses the summary section from the <ol> element with a class containing 'lgx66tx'.
    Expected summary format example: "4 guests · 1 bedroom · 2 beds · 1.5 baths"
    """
    listing_data = {
        "listing_id": None,
        "title": None,
        "room_type": None,
        "bedroom_count": None,
        "bathroom_count": None,
        "price": None
    }
    check_in, check_out, guests, price_min, price_max = generate_random_search_params()
    query_params = {
        "check_in": check_in,
        "check_out": check_out,
        "adults": guests
    }
    url_with_params = f"{url}?{urlencode(query_params)}"

    try:
        driver.get(url_with_params)  
              
        # Extract the listing ID from the URL.
        m = re.search(r"/rooms/(\d+)", url)
        if m:
            listing_data["listing_id"] = m.group(1)
        
        # Extract summary details from the ordered list.
        try:
            summary_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//ol[contains(@class, 'lgx66tx')]"))
            )
            summary_text = summary_element.text.strip()
            parts = [part.strip() for part in summary_text.split("·")]
            # Example parts: ["4 guests", "1 bedroom", "2 beds", "1.5 baths"]
            for part in parts:
                part_lower = part.lower()
                if "studio" in part_lower:
                    listing_data["room_type"] = "Studio"
                elif "bedroom" in part_lower:
                    m_bedroom = re.search(r"(\d+)", part_lower)
                    if m_bedroom:
                        listing_data["bedroom_count"] = int(m_bedroom.group(1))
                elif "beds" in part_lower and listing_data["bedroom_count"] is None:
                    # Use "beds" as fallback if no "bedroom" info is present.
                    m_beds = re.search(r"(\d+)", part_lower)
                    if m_beds:
                        listing_data["bedroom_count"] = int(m_beds.group(1))
                elif "bath" in part_lower:
                    m_bath = re.search(r"([\d\.]+)", part_lower)
                    if m_bath:
                        listing_data["bathroom_count"] = float(m_bath.group(1))
        except Exception as e:
            print(f"Warning: Could not extract summary details from {url}: {e}")
        
        # Extract the price per night.
        try:
            # Locate the element that contains the breakdown text, e.g., "$545 x 10 nights"
            breakdown_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'nights')]"))
            )
            breakdown_text = breakdown_element.text.strip()  # Expected: "$545 x 10 nights"
            
            # Extract the nightly price directly from the breakdown text.
            nightly_price_match = re.search(r'\$(\d+(?:,\d+)*)\s*x', breakdown_text)
            if nightly_price_match:
                nightly_price = float(nightly_price_match.group(1).replace(',', ''))
                listing_data["price"] = nightly_price
            else:
                listing_data["price"] = None
        except Exception as e:
            print(f"Warning: Could not extract price from {url}: {e}")
            
    except Exception as e:
        print(f"Error parsing listing details from {url}: {e}")
    
    print(f"Extracted data for {url}: {listing_data}")
    return listing_data

def get_current_page():
    """Extracts the current page number from the pagination elements on the Airbnb search page."""
    try:
        current_page_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//button[@aria-current='page']"))
        )
        return int(current_page_element.text.strip())
    except Exception as e:
        print(f"⚠️ Could not determine the current page: {e}")
        return 1
    
# --- SCRAPING FUNCTIONS ---

def scrape_zipcode(city, zip_code):
    """Scrapes listing URLs for a given city and ZIP code and returns a set of unique listing URLs."""
    check_in, check_out, guests, price_min, price_max = generate_random_search_params()
    listings = set()
    page = 1
    search_url = (f"https://www.airbnb.com/s/{zip_code}/homes?"
                f"check_in={check_in}&check_out={check_out}&adults={guests}"
                f"&price_min={price_min}&price_max={price_max}"
                f"&room_types[]=Entire%20home%2Fapt&page={page}")
    driver.get(search_url)
    waitForFullListingsLoad()

    while page <= 1:
        wait_for_resume()
        print(f"\n🔍 Scraping {city} (ZIP: {zip_code}), Page {page}")
        new_listings = get_listings_from_page()
        listings.update(new_listings)
        try:
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Next']"))
            )
            next_button.click()
            randomize_sleep()
            waitForFullListingsLoad()
            page = get_current_page()
        except Exception as e:
            print(f"❌ No more pages available for {city} (ZIP {zip_code}): {e}")
            break

    print(f"📊 Total unique listings found in {city} (ZIP {zip_code}): {len(listings)}")
    print(f"Scraped for {zip_code} complete. Listings are \n{listings}")
    return listings

def process_listings_for_zipcode(city, zip_code, listings, conn):
    """Iterates through collected listing URLs to parse details and insert them into the database.
       The zipcode is saved as part of each record."""
    for listing_url in listings:
        wait_for_resume()
        randomize_sleep()
        details = parse_listing_details(listing_url)
        if details["listing_id"]:
            listing_record = {
                "listing_id": details["listing_id"],
                "city": city,
                "zipcode": zip_code, 
                "listing_url": listing_url,
                "room_type": details.get("room_type"),
                "bedroom_count": details.get("bedroom_count"), 
                "bathroom_count": details.get("bathroom_count"),
                "price": details.get("price")
            }
            print(f"Inserting listing record: {listing_record}")
            insert_listing(conn, listing_record)


def process_city(city, zip_codes, conn):
    """Iterates through ZIP codes for a city and processes each listing."""
    for zip_code in zip_codes:
        print(f"\n🚀 Starting scrape for {city} (ZIP: {zip_code})")
        listings = scrape_zipcode(city, zip_code)
        process_listings_for_zipcode(city, zip_code, listings, conn)

def load_data_from_file(file_path):
    """Reads city names and ZIP codes from a JSON file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found.")
        return {}

# --- MAIN EXECUTION ---

if __name__ == "__main__":

    # Start the pause/resume listener in a separate thread
    listener_thread = threading.Thread(target=pause_resume_listener, daemon=True)
    listener_thread.start()

    # Establish a PostgreSQL connection for Supabase
    conn = get_db_connection()
    #create_table(conn)

    # Load cities and ZIP codes from file.
    city_data = load_data_from_file(CITY_ZIP_FILE)
    if not city_data:
        print("❌ No cities found in the file. Exiting.")
        driver.quit()
        conn.close()
        exit()

    for city, zip_codes in city_data.items():
        print(f"\n🚀 Starting Airbnb Scraping for {city}")
        for zip_code in zip_codes:
            print(f"\n🚀 Processing {city} (ZIP: {zip_code})")
            listings = scrape_zipcode(city, zip_code)
            process_listings_for_zipcode(city, zip_code, listings, conn)

    driver.quit()
    conn.close()
    print("🏁 Scraping complete. All data pushed to the database.")
