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

# Configuration variables
REGIONS = ["New+York+City--NY"]
NUM_PAGES_TO_SCRAPE = 10  # Number of pages to scrape per region
NUM_LISTINGS_PER_SAMPLE = 50  # Number of listings per sample
DELAY_BETWEEN_REQUESTS = 3  # Time to wait between pages to avoid detection

def setup_driver(headless=True):
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
        if current_count > prev_count:  # New listings appeared, continue waiting
            prev_count = current_count
            time.sleep(1)  # Short wait before checking again
        else:
            break  # No new listings appeared, proceed


def get_listings_from_page():
    time.sleep(3)
    """Extracts unique listing URLs by removing extra query parameters."""
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
    start_date = datetime.today() + timedelta(days=random.randint(5, 90))  # Wider range
    end_date = start_date + timedelta(days=random.randint(2, 10))  # More variation in stay length
    guests = random.randint(1, 6)  # Expand guest range

    price_min = random.choice([0, 50, 100, 150, 200])  # Adjust price filters
    possible_price_max = [250, 300, 400, 500, 750, 1000]  # Different max price points

    # Ensure price_max is always greater than price_min
    price_max = random.choice([p for p in possible_price_max if p > price_min])

    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), guests, price_min, price_max
def capture_sample(city, num_pages=NUM_PAGES_TO_SCRAPE):
    """Scrapes multiple pages for a given city with randomized search parameters and detects duplicates."""
    check_in, check_out, guests, price_min, price_max = generate_random_search_params()
    start_page = random.randint(2, 5)  # Start from a random page (not page 1)
    
    listings = set()
    duplicate_count = 0  # Track number of duplicates found

    for page in range(start_page, start_page + num_pages):
        search_url = (f"https://www.airbnb.com/s/{city}/homes?"
                      f"check_in={check_in}&check_out={check_out}&adults={guests}"
                      f"&price_min={price_min}&price_max={price_max}"
                      f"&room_types[]=Entire%20home%2Fapt&page={page}")  # Added "Entire home" filter
        print(f"\nScraping city: {city}, Page {page} -> {search_url}")

        driver.get(search_url)
        waitForFullListingsLoad()

        before_count = len(listings)  # Count listings before scraping this page
        new_listings = get_listings_from_page()

        # Check for duplicates before adding new listings
        duplicates = new_listings.intersection(listings)  # Find overlapping listings
        duplicate_count += len(duplicates)  # Track total duplicates found

        if duplicates:
            print(f"🚨 Found {len(duplicates)} duplicate listings on Page {page}: {duplicates}")

        listings.update(new_listings)  # Add only new listings

        after_count = len(listings)  # Count listings after updating
        new_unique = after_count - before_count  # How many new listings were actually added?

        print(f"Page {page} -> {len(new_listings)} listings found, {new_unique} new unique listings added.")
        print(f"Total collected: {after_count} (Total Duplicates Found: {duplicate_count})")

        try:
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Next']"))
            )
            current_url = driver.current_url  # Save the current URL before clicking
            next_button.click()
            time.sleep(DELAY_BETWEEN_REQUESTS)

            WebDriverWait(driver, 10).until(lambda d: d.current_url != current_url)  # Ensure page changes
            print(f"✅ Moved to next page: {driver.current_url}")

            waitForFullListingsLoad()
        except Exception:
            print(f"❌ No more pages available in {city}")
            break  # Stop if there's no next page

    print(f"\n✅ Final unique listings collected from {city}: {len(listings)}")
    print(f"🚨 Total duplicate listings detected: {duplicate_count}")
    return listings


def estimate_total_listings(city):
    """
    Uses Capture-Recapture method to estimate total number of listings in a city.
    Formula: N = (n1 * n2) / m
    Where:
    - n1 = Size of first sample
    - n2 = Size of second sample
    - m  = Overlapping listings (same ones in both samples)
    """
    print(f"Estimating total listings for {city} using Capture-Recapture...")
    
    # Capture two independent samples with different search parameters
    sample1 = capture_sample(city)
    time.sleep(random.randint(5, 10))  # Add delay between captures
    sample2 = capture_sample(city)
    
    n1, n2 = len(sample1), len(sample2)
    overlap = len(sample1.intersection(sample2))  # Find duplicates

    if overlap == 0:
        overlap = 1  # Avoid division by zero

    estimated_total = int(round((n1 * n2) / overlap))
    print(f"Estimated total listings in {city}: {int(estimated_total)}")
    return estimated_total

if __name__ == "__main__":
    total_listings = {}
    for region in REGIONS:
        total_listings[region] = estimate_total_listings(region)

    print("\nFinal Estimated Listings per City:")
    print(json.dumps(total_listings, indent=4))
    
    driver.quit()
