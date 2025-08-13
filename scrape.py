import json
import sqlite3
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

API_BASE_URL = "https://api.henleypassportindex.com/api/v3"
DB_NAME = "data/passportindex.db"


def setup_database() -> None:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout = 5000;")

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
            from_country TEXT,
            to_country TEXT,
            effective_date DATE NOT NULL,
            requirement_type TEXT,
            PRIMARY KEY (from_country, to_country, effective_date),
            FOREIGN KEY (from_country) REFERENCES Country(code),
            FOREIGN KEY (to_country) REFERENCES Country(code)
        )
        """)


def fetch_data(url: str) -> Any:
    try:
        with urlopen(url) as response:
            data = response.read().decode()
            return json.loads(data)
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        raise
    except URLError as e:
        print(f"URL Error: {e.reason}")
        raise


def fetch_countries() -> list[dict[str, Any]]:
    """
    Fetches the list of all countries from the Henley Passport Index API.

    Example:
    https://api.henleypassportindex.com/api/v3/countries

    Returns:
    list: A list of dictionaries, each containing country information.

    Example:
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
    response = fetch_data(f"{API_BASE_URL}/countries")
    data = response.get("countries", {})
    print(f"Fetched {len(data)} countries")
    return data


def fetch_visa_single(country_code: str) -> dict[str, Any]:
    """
    Fetches visa requirement data for a single country from the Henley Passport Index API.

    Example:
    https://api.henleypassportindex.com/api/v3/visa-single/SG

    Args:
    country_code (str): The two-letter country code.

    Returns:
    dict: A dictionary containing visa requirement information for the specified country.

    Example:
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
    response = fetch_data(f"{API_BASE_URL}/visa-single/{country_code}")
    print(f"Fetched visa data for {country_code}")
    return response


def insert_country_data(country: dict[str, Any]) -> int:
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

        insert_count = 0
        ranking_data = country.get("data")

        # NOTE: if a country does not have any ranking data, the API returns [] instead of {}
        if not ranking_data:
            return 0

        for year, data in ranking_data.items():
            # Check if the record already exists
            cursor.execute(
                "SELECT 1 FROM CountryRanking WHERE country_code = ? AND year = ?",
                (country["code"], int(year)),
            )
            record_exists = cursor.fetchone() is not None
            if not record_exists:
                cursor.execute(
                    """
                    INSERT INTO CountryRanking (country_code, year, rank, visa_free_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        country["code"],
                        int(year),
                        data.get("rank"),
                        data.get("visa_free_count"),
                    ),
                )

                insert_count += 1
                print(f"Inserted new ranking: {country['code']} ({year})")

        return insert_count


def insert_visa_requirements(from_country_code, visa_data) -> int:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        current_date = datetime.now().date().isoformat()
        insert_count = 0

        for req_type, countries in visa_data.items():
            if req_type in ("code", "country"):
                continue

            for to_country in countries:
                cursor.execute(
                    """
                    SELECT requirement_type
                    FROM VisaRequirement
                    WHERE from_country = ? AND to_country = ?
                    ORDER BY effective_date DESC
                    LIMIT 1
                    """,
                    (from_country_code, to_country["code"]),
                )

                result = cursor.fetchone()

                if result is None or result[0] != req_type:
                    # NOTE: insert only if there's no previous record or the requirement type has changed
                    cursor.execute(
                        """
                        INSERT INTO VisaRequirement (from_country, to_country, effective_date, requirement_type)
                        VALUES (?, ?, ?, ?)
                        """,
                        (from_country_code, to_country["code"], current_date, req_type),
                    )

                    insert_count += 1
                    print(
                        f"Inserted new requirement: {from_country_code} to {to_country['code']} ({req_type})"
                    )

        return insert_count


def main() -> None:
    setup_database()
    countries: list[dict[str, Any]] = fetch_countries()

    new_country_ranking_count = 0
    new_visa_requirement_count = 0

    for country in countries:
        rankings: int = insert_country_data(country)
        new_country_ranking_count += rankings

        visa_data: dict[str, Any] = fetch_visa_single(country["code"])
        if visa_data:
            new_visa_requirement_count += insert_visa_requirements(
                country["code"], visa_data
            )
        else:
            print(f"Failed to fetch visa data for {country['country']}")

    print("\nSummary:")
    print(f"New country rankings inserted: {new_country_ranking_count}")
    print(f"New visa requirements inserted: {new_visa_requirement_count}")


if __name__ == "__main__":
    main()
