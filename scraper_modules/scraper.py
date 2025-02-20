#!/usr/bin/env python3
import json
import re
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Configuration variables
REGIONS = [
    "New+York--NY",
    "Los+Angeles--CA",
    "Chicago--IL",
]
NUM_LISTINGS_PER_REGION = 10  # Desired number of listings per region

def setup_driver(headless=False):
    options = Options()
    options.headless = headless
    # Optionally override the user-agent (here using a typical Firefox user-agent on macOS)
    options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:116.0) Gecko/20100101 Firefox/116.0"
    )
    return webdriver.Firefox(options=options)

driver = setup_driver(headless=False)

def waitForListingElement(timeout=10):
    # Wait until at least one listing element is present on the new page
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/rooms/')]"))
    )

def goToNextPage():
    current_url = driver.current_url
    # Wait for the "Next" button to be clickable and click it
    next_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Next']"))
    )
    next_button.click()
    current_page += 1
    # Wait until the URL changes (i.e. the page navigates)
    WebDriverWait(driver, 10).until(lambda d: d.current_url != current_url)
    # Wait until at least one listing element is present on the new page
    waitForListingElement()
def __apply_whole_house_filter():
    # Click on the Filters button
    filter_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='Filters']"))
    )
    filter_button.click()

    # Wait for the "Entire home" option to be clickable and click it.
    entire_home_option = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Entire home')]"))
    )
    entire_home_option.click()

    # Wait for the Apply filter button (with text like "Show 1,000+ places") to be clickable, then click it.
    apply_filter_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//a[contains(text(), 'Show') and contains(@href, 'refinement_paths')]"
        ))
    )
    apply_filter_button.click()
    waitForListingElement()
    # added this dummy sleep because sometime only 1 listing loads even though there are more resulting in only one listing link being scraped; we can be smarter.
    time.sleep(3)
def scrapeForListingsInCity(city, max_retries=3):
    import re, time
    # Validate that the city parameter is in the format "City+Name--ST"
    pattern = r"^[A-Za-z+]+--[A-Za-z]{2}$"
    if not re.match(pattern, city):
        raise ValueError("City parameter must be in the format 'City+Name--StateCode', e.g., 'New+York--NY'")
    search_url = f"https://www.airbnb.com/s/{city}/homes"
    print(f"Scraping region: {city} -> {search_url}")
    
    # Try to load the page and wait for listings with retries
    for attempt in range(max_retries):
        try:
            
            driver.get(search_url)
            # Wait until at least one listing element is present, with a timeout of 10 seconds
            waitForListingElement()
            break  # Successfully loaded and found listings; exit the retry loop.
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)  # Wait a bit before retrying.
    __apply_whole_house_filter()

    # Find listing links by locating elements with href containing "/rooms/"
    listing_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/rooms/')]")
    listing_links = []
    for elem in listing_elements:
        url = elem.get_attribute("href")
        if url and url not in listing_links:
            listing_links.append(url)
        if len(listing_links) >= NUM_LISTINGS_PER_REGION:
            break

    print(f"Found {len(listing_links)} listings in region {city}")
    return listing_links

if __name__ == "__main__":
    print(scrapeForListingsInCity("New+York--NY"))