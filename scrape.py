import sqlite3
import json
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

# Constants
API_BASE_URL = "https://api.henleypassportindex.com/api/v3"
DB_NAME = "data/passportindex.db"


def create_database():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Country (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS CountryRanking (
            country_code TEXT,
            year INTEGER,
            rank INTEGER,
            visa_free_count INTEGER,
            PRIMARY KEY (country_code, year),
            FOREIGN KEY (country_code) REFERENCES Country(code)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS VisaRequirement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_country TEXT,
            to_country TEXT,
            effective_date DATE NOT NULL,
            requirement_type TEXT,
            FOREIGN KEY (from_country) REFERENCES Country(code),
            FOREIGN KEY (to_country) REFERENCES Country(code)
        )
        """)

        # cursor.execute("""
        # CREATE INDEX IF NOT EXISTS idx_visa_requirement
        # ON VisaRequirement(from_country, to_country, effective_date)
        # """)


def fetch_data(url):
    try:
        with urlopen(url) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
    except URLError as e:
        print(f"URL Error: {e.reason}")
    return None


def fetch_countries():
    """
    Fetches the list of all countries from the Henley Passport Index API.

    Returns:
    list: A list of dictionaries, each containing country information.

    Example response:
    [
        {
            "code": "AF",
            "country": "Afghanistan",
            "has_data": true,
            "region": "ASIA",
            "visa_free_count": 26,
            "openness": 22.61,
            "visa_free_url": "https://cdn.henleyglobal.com/storage/app/media/HPI/AF_visa_free.pdf",
            "visa_required_url": "https://cdn.henleyglobal.com/storage/app/media/HPI/AF_visa_required.pdf",
            "visa_full_url": "https://cdn.henleyglobal.com/storage/app/media/HPI/AF_visa_full.pdf",
            "flags": {
                "is_cbi": 0,
                "is_rbi": 0
            },
            "data": {
                "2021": {"rank": 116, "visa_free_count": 26},
                "2020": {"rank": 106, "visa_free_count": 26},
                // ... more years ...
            }
        },
        // ... more countries ...
    ]
    """
    data = fetch_data(f"{API_BASE_URL}/countries")
    return data.get("countries", [])


def fetch_visa_single(country_code):
    """
    Fetches visa requirement data for a single country from the Henley Passport Index API.

    Args:
    country_code (str): The two-letter country code.

    Returns:
    dict: A dictionary containing visa requirement information for the specified country.

    Example response:
    {
        "code": "SG",
        "country": "Singapore",
        "visa_free_access": [
            {"code": "CN", "name": "China"},
            {"code": "JP", "name": "Japan"},
            // ... more countries ...
        ],
        "visa_required": [
            {"code": "AF", "name": "Afghanistan"},
            // ... more countries ...
        ],
        "electronic_travel_authorisation": [
            {"code": "AU", "name": "Australia"},
            // ... more countries ...
        ],
        "visa_on_arrival": [
            {"code": "BH", "name": "Bahrain"},
            // ... more countries ...
        ],
        "visa_online": [
            {"code": "IN", "name": "India"},
            // ... more countries ...
        ]
    }
    """
    return fetch_data(f"{API_BASE_URL}/visa-single/{country_code}")


def insert_country_data(country):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO Country (code, name, region)
            VALUES (?, ?, ?)
            """,
            (
                country["code"],
                country["country"],
                country.get("region"),
            ),
        )

        ranking_data = country.get("data")
        if isinstance(
            ranking_data, list
        ):  # NOTE: if a country does not have any ranking data, the API returns [] instead of {}
            return

        for year, data in ranking_data.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO CountryRanking (country_code, year, rank, visa_free_count)
                VALUES (?, ?, ?, ?)
                """,
                (
                    country["code"],
                    int(year),
                    data.get("rank"),
                    data.get("visa_free_count"),
                ),
            )


def insert_visa_requirements(country_code, visa_data):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        current_date = datetime.now().date().isoformat()

        for req_type, countries in visa_data.items():
            if req_type in ("code", "country"):
                continue

            for destination in countries:
                cursor.execute(
                    """
                    INSERT INTO VisaRequirement (from_country, to_country, effective_date, requirement_type)
                    VALUES (?, ?, ?, ?)
                    """,
                    (country_code, destination["code"], current_date, req_type),
                )


def main():
    create_database()
    countries = fetch_countries()

    for country in countries:
        insert_country_data(country)
        visa_data = fetch_visa_single(country["code"])
        if visa_data:
            insert_visa_requirements(country["code"], visa_data)
            print(f"Processed {country['country']}")
        else:
            print(f"Failed to fetch visa data for {country['country']}")


if __name__ == "__main__":
    main()