"""
zipcodebase_extended.py

A module for interacting with the ZipcodeBase API and its extended endpoints.

Documentation: https://app.zipcodebase.com/documentation

Endpoints covered:
- Postal code to location information (/search)
- Distance calculation between postal codes (/distance)
- Postal codes within a radius (/radius)
- Postal codes by city (/city)
- Postal codes by state (/state)
- Provinces/States of a country (/states)
"""

import requests

API_KEY = "f14c1040-f2c7-11ef-8d4e-c5d7c7671d88"
BASE_URL = "https://app.zipcodebase.com/api/v1/"

def lookup_zip_codes(codes, country="US"):
    """
    Lookup location information for a list of postal codes.
    """
    endpoint = BASE_URL + "search"
    params = {
        "apikey": API_KEY,
        "codes": ",".join(codes),
        "country": country
    }
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching zip code data: {e}")
        return None

def calculate_distance(from_zip, to_zip, country="US"):
    """
    Calculate the distance between a base postal code (from_zip) and one or more other postal codes (to_zip).
    
    Parameters:
        from_zip (str): The base postal code.
        to_zip (str or list): A single postal code or a list of postal codes to compare.
        country (str): The country code (default "US").
        
    Returns:
        dict: JSON response from the API.
    """
    endpoint = BASE_URL + "distance"
    
    # If to_zip is a list, join it into a comma-separated string
    if isinstance(to_zip, list):
        compare_value = ",".join(to_zip)
    else:
        compare_value = to_zip
    
    params = {
        "apikey": API_KEY,
        "country": country,
        "code": from_zip,
        "compare": compare_value
    }
    
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error calculating distance: {e}")
        return None


def get_postal_codes_within_radius(zip_code, radius, country="US"):
    """
    Retrieve postal codes within a specified radius from a given postal code.
    
    Parameters:
        zip_code (str): The base postal code.
        radius (int or float): The search radius (units as defined by the API, e.g. miles or km).
        country (str): Country code (default "US").
    """
    endpoint = BASE_URL + "radius"
    params = {
        "apikey": API_KEY,
        "country": country,
        "code": zip_code,
        "radius": radius
    }
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching postal codes within radius: {e}")
        return None

def get_postal_codes_by_city(city, country="US", state_name=None, limit=None):
    """
    Retrieve postal codes for a given city.

    Endpoint: GET/POST code/city

    Parameters:
        city (str): Name of the city (required).
        country (str): ISO 3166-1 alpha-2 country code (required, default "US").
        state_name (str, optional): Name of the province/state.
        limit (int, optional): Limit the number of results returned.

    Note:
        Every 10 postal codes returned are charged as 1 request.

    Returns:
        dict: JSON response from the API, or None if an error occurs.
    """
    endpoint = BASE_URL + "code/city"
    params = {
        "apikey": API_KEY,
        "city": city,
        "country": country
    }
    if state_name:
        params["state_name"] = state_name
    if limit:
        params["limit"] = limit
        
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching postal codes by city: {e}")
        return None


def get_postal_codes_by_state(state, country="US", limit=None):
    """
    Retrieve postal codes for a given state.

    Endpoint: GET/POST code/state

    Parameters:
        state (str): Two-letter state code (required).
        country (str): ISO 3166-1 alpha-2 country code (required, default "US").
        limit (int, optional): Limit the number of results returned.

    Note:
        Every 10 postal codes returned are charged as 1 request.

    Returns:
        dict: JSON response from the API, or None if an error occurs.
    """
    endpoint = BASE_URL + "code/state"
    params = {
        "apikey": API_KEY,
        "state_name": state,
        "country": country
    }
    if limit:
        params["limit"] = limit
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching postal codes by state: {e}")
        return None


def get_states(country="US"):
    """
    Retrieve a list of provinces/states for a given country.
    """
    endpoint = BASE_URL + "country/province"
    params = {
        "apikey": API_KEY,
        "country": country
    }
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching states: {e}")
        return None

if __name__ == "__main__":
    # Example usage:
    print("Lookup ZIP Codes:", lookup_zip_codes(["90210", "10001"]))
    print("Distance:", calculate_distance("90210", "10001"))
    print("Radius:", get_postal_codes_within_radius("90210", 10))
    print("By City:", get_postal_codes_by_city("Los Angeles"))
    print("By State:", get_postal_codes_by_state("California"))
    print("States:", get_states())