# Passport DB

Tracking historical changes in passport rankings and visa requirements.

## Database Schema

```mermaid
erDiagram
    Country ||--o{ CountryRanking : has
    Country ||--o{ VisaRequirement : "issues/receives"

    Country {
        text code PK
        text name
        text region
    }

    CountryRanking {
        text country_code PK, FK
        int year PK
        int rank
        int visa_free_count
    }

    VisaRequirement {
        text from_country PK, FK
        text to_country PK, FK
        date effective_date PK
        text requirement_type
    }
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
