import contextlib
import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError, URLError

import scrape


def make_datetime_mock(date_str: str):
    m = Mock()
    d = Mock()
    dd = Mock()
    dd.isoformat.return_value = date_str
    d.date.return_value = dd
    m.now.return_value = d
    return m


class ScrapeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.db")
        scrape.DB_NAME = self.db_path

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        scrape.setup_database()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_fetch_data_success(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"hello": "world"}'
        mock_resp.__enter__.return_value = mock_resp

        with patch("scrape.urlopen", return_value=mock_resp):
            result = scrape.fetch_data("http://example.com")
            self.assertEqual(result, {"hello": "world"})

    def test_fetch_data_raises_http_and_url_error(self):

        with patch(
            "scrape.urlopen", side_effect=HTTPError("url", 404, "Not Found", None, None)
        ):
            with self.assertRaises(HTTPError):
                scrape.fetch_data("http://example.com")

        with patch("scrape.urlopen", side_effect=URLError("no host")):
            with self.assertRaises(URLError):
                scrape.fetch_data("http://example.com")

    def test_insert_country_data_inserts_rankings(self):
        country_data = {
            "code": "XX",
            "country": "Xland",
            "region": "ASIA",
            "data": {
                "2020": {"rank": 10, "visa_free_count": 20},
                "2021": {"rank": 9, "visa_free_count": 21},
            },
        }

        inserted = scrape.insert_country_data(country_data)
        self.assertEqual(inserted, 2)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM CountryRanking WHERE country_code = ?", ("XX",)
        )
        (count,) = cur.fetchone()
        conn.close()
        self.assertEqual(count, 2)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT name, region FROM Country WHERE code = ?", ("XX",))
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "Xland")

    def test_insert_country_data_empty_ranking_returns_zero(self):
        country_data = {"code": "YY", "country": "Yland", "region": None, "data": []}
        inserted = scrape.insert_country_data(country_data)
        self.assertEqual(inserted, 0)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM Country WHERE code = ?", ("YY",))
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_insert_visa_requirements_inserts_and_updates(self):
        from_country = "SG"
        visa_data_1 = {
            "version": scrape.API_VERSION,
            "visa_free_access": [{"code": "CN", "name": "China"}],
        }

        visa_data_2 = {
            "version": scrape.API_VERSION,
            "visa_required": [{"code": "CN", "name": "China"}],
        }

        with patch.object(scrape, "datetime", new=make_datetime_mock("2020-01-01")):
            inserted1 = scrape.insert_visa_requirements(from_country, visa_data_1)
            self.assertEqual(inserted1, 1)

        with patch.object(scrape, "datetime", new=make_datetime_mock("2021-01-01")):
            inserted2 = scrape.insert_visa_requirements(from_country, visa_data_2)
            self.assertEqual(inserted2, 1)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM VisaRequirement WHERE from_country = ? AND to_country = ?",
            (from_country, "CN"),
        )
        (count,) = cur.fetchone()
        self.assertEqual(count, 2)

        cur.execute(
            "SELECT requirement_type FROM VisaRequirement WHERE from_country = ? AND to_country = ? ORDER BY effective_date DESC LIMIT 1",
            (from_country, "CN"),
        )
        (latest_type,) = cur.fetchone()
        conn.close()
        self.assertEqual(latest_type, "visa_required")

    def test_main_end_to_end_small(self):
        countries = [
            {
                "code": "AA",
                "country": "Aland",
                "data": {"2022": {"rank": 1, "visa_free_count": 5}},
            }
        ]

        visa_single = {
            "version": scrape.API_VERSION,
            "visa_free_access": [{"code": "BB", "name": "Bland"}],
        }

        scrape.DB_NAME = self.db_path

        with (
            patch("scrape.fetch_countries", return_value=countries),
            patch("scrape.fetch_visa_single", return_value=visa_single),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                scrape.main()
            output = buf.getvalue()
            self.assertIn("New country rankings inserted: 1", output)
            self.assertIn("New visa requirements inserted: 1", output)

    def test_fetch_visa_single_missing_triggers_failure_message(self):
        countries = [
            {
                "code": "CC",
                "country": "Cland",
                "data": {"2022": {"rank": 1, "visa_free_count": 1}},
            }
        ]

        with (
            patch("scrape.fetch_countries", return_value=countries),
            patch("scrape.fetch_visa_single", return_value={}),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                scrape.main()
            output = buf.getvalue()
            self.assertIn("Failed to fetch visa data for Cland", output)

    def test_api_version_change_logs(self):
        visa_data = {
            "version": scrape.API_VERSION + 1,
            "visa_free_access": [{"code": "DD", "name": "Dland"}],
        }

        with patch.object(scrape, "datetime", new=make_datetime_mock("2022-01-01")):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                inserted = scrape.insert_visa_requirements("SG", visa_data)
            output = buf.getvalue()
            self.assertIn(
                f"API version changed from {scrape.API_VERSION} to {visa_data['version']}",
                output,
            )
            self.assertEqual(inserted, 1)


if __name__ == "__main__":
    unittest.main()
