#!/usr/bin/env python3
import json
import os
import re
import time
import random
import psycopg2
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

# Supabase/PostgreSQL connection parameters
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

# --- DATABASE FUNCTIONS ---

def get_db_connection():
    """Establish a connection to the Supabase PostgreSQL database."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

def create_table(conn):
    """Create the listings table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                listing_id TEXT PRIMARY KEY,
                city TEXT NOT NULL,
                zipcode TEXT NOT NULL,
                listing_url TEXT NOT NULL,
                room_type TEXT,
                bedroom_count INTEGER,
                bathroom_count INTEGER
            );
        """)
        conn.commit()

def insert_listing(conn, listing_data):
    """
    Insert a listing into the database.
    listing_data should be a dictionary containing:
    - listing_id, city, zipcode, listing_url, room_type, bedroom_count, bathroom_count
    """
    with conn.cursor() as cur:
        try:
            cur.execute("""
                INSERT INTO listings (listing_id, city, zipcode, listing_url, room_type, bedroom_count, bathroom_count)
                VALUES (%(listing_id)s, %(city)s, %(zipcode)s, %(listing_url)s, %(room_type)s, %(bedroom_count)s, %(bathroom_count)s)
                ON CONFLICT (listing_id) DO NOTHING;
            """, listing_data)
            conn.commit()
        except Exception as e:
            print(f"Error inserting {listing_data.get('listing_url')}: {e}")
            conn.rollback()


# --- PARSING FUNCTIONS ---

def parse_listing_details(url):
    """
    Visits the listing page and extracts relevant data:
    - listing_id: Extracted from the URL.
    - title: The listing title.
    - summary: A breakdown of key details (e.g. guests, room type, bed, bath).
    - price: Price per night.
    
    Specifically, it extracts the room type (e.g. "Studio"), number of beds, and number of baths
    from the summary information.
    """
    listing_data = {
        "listing_id": None,
        "title": None,
        "room_type": None,
        "bed": None,
        "bath": None,
    }
    
    try:
        driver.get(url)
        time.sleep(5)  # Wait for the page to load completely
        
        # Extract the listing ID from the URL
        match = re.search(r"/rooms/(\d+)", url)
        if match:
            listing_data["listing_id"] = match.group(1)

    
        # Extract the summary details (e.g., "3 guests · Studio · 1 bed · 1 bath")
        try:
            summary_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//ol[contains(@class, 'lgx66tx')]"))
            )
            summary_text = summary_element.text.strip()
            # Split the summary text by the dot separator
            parts = [part.strip() for part in summary_text.split("·")]
            # Assign details based on position (adjust if Airbnb's layout changes)
            # Expected order: guests, room type, bed info, bath info
            if len(parts) >= 4:
                # We focus on room type, bed and bath; guests can be extracted as needed.
                listing_data["room_type"] = parts[1]  # e.g., "Studio"
                listing_data["bed"] = parts[2]        # e.g., "1 bed"
                listing_data["bath"] = parts[3]       # e.g., "1 bath"
            else:
                print(f"Warning: Unexpected summary format in {url}: {summary_text}")
        except Exception as e:
            print(f"Warning: Could not extract summary details from {url}: {e}")
        
    except Exception as e:
        print(f"Error parsing listing details from {url}: {e}")
    
    return listing_data

# --- SCRAPING FUNCTIONS ---

def scrape_zipcode(city, zip_code, conn):
    """Scrapes listings for a given city and ZIP code, parses details, and inserts them into the database."""
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
        # For each new listing, visit the page to parse details and then insert into the database.
        for listing_url in new_listings:
            details = parse_listing_details(listing_url)
            if details["listing_id"]:
                listing_record = {
                    "listing_id": details["listing_id"],
                    "city": city,
                    "zipcode": zip_code,
                    "listing_url": listing_url,
                    "title": details.get("title"),
                    "price": details.get("price")
                }
                insert_listing(conn, listing_record)
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
        except Exception as e:
            print(f"❌ No more pages available for {city} (ZIP {zip_code}): {e}")
            break

    print(f"📊 Total unique listings found in {city} (ZIP {zip_code}): {len(listings)}")
    return listings

def process_city(city, zip_codes, conn):
    """Iterates through ZIP codes for a city and processes each listing."""
    for zip_code in zip_codes:
        print(f"\n🚀 Starting scrape for {city} (ZIP: {zip_code})")
        scrape_zipcode(city, zip_code, conn)

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
    print(parse_listing_details("https://www.airbnb.com/rooms/46637903?category_tag=Tag%3A5348&search_mode=flex_destinations_search&adults=1&check_in=2025-03-02&check_out=2025-03-07&children=0&infants=0&pets=0&photo_id=1123459137&source_impression_id=p3_1740089697_P3gFytq2tnFY8AiK&previous_page_section_name=1000&federated_search_id=98e024a7-0dad-48a6-b8b2-b9ee733272cc"))
    # Connect to the database and create the table if needed.
    # conn = get_db_connection()
    # create_table(conn)

    # Load cities and ZIP codes from file.
    # city_data = load_data_from_file(CITY_ZIP_FILE)
    # if not city_data:
    #     print("❌ No cities found in the file. Exiting.")
    #     driver.quit()
    #     conn.close()
    #     exit()

    # Process each city.
    # for city, zip_codes in city_data.items():
    #     print(f"\n🚀 Starting Airbnb Scraping for {city}")
    #     process_city(city, zip_codes, conn)

    # driver.quit()
    # conn.close()
    # print("🏁 Scraping complete. All data pushed to the database.")