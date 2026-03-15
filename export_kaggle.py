"""
Export CSVs for Kaggle dataset publication.

Exports:
- countries.csv          — Full country reference table
- passport_rankings.csv  — Latest year passport rankings only
- visa_requirements.csv  — Current visa requirement snapshot (latest per pair)

Usage:
    python export_kaggle.py
"""

import csv
import os
import sqlite3

DB_PATH = "data/passportindex.db"
OUTPUT_DIR = "data"


def export_countries(cursor: sqlite3.Cursor) -> int:
    cursor.execute("""
        SELECT code, name, region
        FROM Country
        ORDER BY name
    """)
    rows = cursor.fetchall()

    path = os.path.join(OUTPUT_DIR, "countries.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["country_code", "country_name", "region"])
        writer.writerows(rows)

    print(f"Exported {len(rows)} countries → {path}")
    return len(rows)


def export_latest_rankings(cursor: sqlite3.Cursor) -> int:
    cursor.execute("""
        SELECT c.code, c.name, c.region, cr.year, cr.rank, cr.visa_free_count
        FROM Country c
        JOIN CountryRanking cr ON c.code = cr.country_code
        WHERE cr.year = (SELECT MAX(year) FROM CountryRanking)
        ORDER BY cr.rank ASC, c.name ASC
    """)
    rows = cursor.fetchall()

    path = os.path.join(OUTPUT_DIR, "passport_rankings.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "country_code",
                "country_name",
                "region",
                "year",
                "rank",
                "visa_free_count",
            ]
        )
        writer.writerows(rows)

    year = rows[0][3] if rows else "N/A"
    print(f"Exported {len(rows)} rankings (year={year}) → {path}")
    return len(rows)


def export_current_visa_requirements(cursor: sqlite3.Cursor) -> int:
    cursor.execute("""
        SELECT
            vr.from_country,
            c1.name AS from_country_name,
            vr.to_country,
            c2.name AS to_country_name,
            vr.requirement_type
        FROM VisaRequirement vr
        JOIN Country c1 ON vr.from_country = c1.code
        JOIN Country c2 ON vr.to_country = c2.code
        WHERE vr.effective_date = (
            SELECT MAX(effective_date)
            FROM VisaRequirement
            WHERE from_country = vr.from_country AND to_country = vr.to_country
        )
        ORDER BY c1.name, c2.name
    """)
    rows = cursor.fetchall()

    path = os.path.join(OUTPUT_DIR, "visa_requirements.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "from_country_code",
                "from_country_name",
                "to_country_code",
                "to_country_name",
                "requirement_type",
            ]
        )
        writer.writerows(rows)

    print(f"Exported {len(rows)} current visa requirements → {path}")
    return len(rows)


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        print("=== Kaggle Export ===\n")
        export_countries(cursor)
        export_latest_rankings(cursor)
        export_current_visa_requirements(cursor)
        print(f"\nDone. Files are in the '{OUTPUT_DIR}' directory.")


if __name__ == "__main__":
    main()
