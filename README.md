# Passport DB

Tracking historical changes in passport rankings and visa requirements.

## How This Works

```mermaid
graph TB
	subgraph Vercel
        deployment[Datasette]
        class deployment vercel;
    end

    subgraph GitHub
        subgraph Actions
            scraper[scrape.py]
        end
        subgraph Artifacts
            db[(passportindex.db)]
            class db artifacts;
        end
    end

    subgraph Henley Passport Index
        api[API]
    end

    db --> |1: Download| scraper
    api --> |2: Fetch Data| scraper
    scraper --> |3: Upload| db
    scraper --> |4: Publish| deployment
    deployment --> |5: View/Access Data| client[User]
```

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
