import csv
import unittest
from pathlib import Path
from normalize_exceptions import clean, normalize_terminal, normalize_timestamp


class NormalizationTests(unittest.TestCase):
    def test_terminal_alias(self):
        self.assertEqual(normalize_terminal(" T3 "), "Terminal 3")
        self.assertEqual(normalize_terminal("Terminal 3"), "Terminal 3")
        self.assertIsNone(normalize_terminal("T9"))

    def test_timestamp_timezone_not_invented(self):
        self.assertEqual(normalize_timestamp("08/14/2026 09:45"), ("2026-08-14T09:45:00", False))
        self.assertEqual(normalize_timestamp("2026-08-14T10:03:00Z"), ("2026-08-14T10:03:00Z", True))

    def test_supplied_export(self):
        with Path(__file__).with_name("exceptions.csv").open(newline="") as fh:
            records, counts, warnings = clean(csv.DictReader(fh))
        self.assertEqual(len(records), 5)
        self.assertEqual(dict(counts), {"missed_pickup": 2, "doc_mismatch": 2, "carrier_substitution": 1})
        self.assertEqual({r["terminal"] for r in records}, {"Terminal 3"})
        self.assertEqual(records[2]["carrier_code"], "SWFT")
        self.assertEqual(records[3]["carrier_code"], "")
        self.assertTrue(any(w["exception_id"] == "CPX-88216" and w["field"] == "carrier_code" for w in warnings))
        self.assertEqual(sum(w["field"] == "event_ts" for w in warnings), 4)


if __name__ == "__main__":
    unittest.main()
