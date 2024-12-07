# Passport DB

Tracking historical changes in passport rankings and visa requirements.

## Database Schema

```mermaid
erDiagram
    Country {
        TEXT code PK
        TEXT name
        TEXT region
    }
    CountryRanking {
        TEXT country_code FK
        INTEGER year
        INTEGER rank
        INTEGER visa_free_count
    }
    VisaRequirement {
        INTEGER id PK
        TEXT from_country FK
        TEXT to_country FK
        DATE effective_date
        TEXT requirement_type
    }

    Country ||--o{ CountryRanking : has
    Country ||--o{ VisaRequirement : requires
    Country ||--o{ VisaRequirement : allows
```

## Usage

### Running the Script

To run the script locally and update the database:

```bash
python3 scrape.py
```

## License

This project is licensed under the [MIT License](./LICENSE).

## Disclaimer

This software is only used for research purposes, users must abide by the relevant laws and regulations of their location, please do not use it for illegal purposes. The user shall bear all the consequences caused by illegal use.
