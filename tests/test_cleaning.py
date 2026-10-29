import unittest
from datetime import date

import pandas as pd

from bookstore_analytics.cleaning import (
    author_keys,
    parse_order_date,
    parse_unit_price_usd,
    reconcile_users,
)
from decimal import Decimal


class PriceTests(unittest.TestCase):
    def test_dollar_spellings(self):
        self.assertEqual(parse_unit_price_usd("$ 35"), Decimal("35.00"))
        self.assertEqual(parse_unit_price_usd("30.0USD"), Decimal("30.00"))
        self.assertEqual(parse_unit_price_usd("USD25.25"), Decimal("25.25"))
        self.assertEqual(parse_unit_price_usd("29.0$"), Decimal("29.00"))
        self.assertEqual(parse_unit_price_usd("36. $"), Decimal("36.00"))
        self.assertEqual(parse_unit_price_usd("41.$"), Decimal("41.00"))
        self.assertEqual(parse_unit_price_usd("$42\u00a225"), Decimal("42.25"))
        self.assertEqual(parse_unit_price_usd("46$99\u00a2"), Decimal("46.99"))

    def test_euro_conversion(self):
        self.assertEqual(parse_unit_price_usd("EUR37.50"), Decimal("45.00"))
        self.assertEqual(parse_unit_price_usd("\u20ac22\u00a225"), Decimal("26.70"))
        self.assertEqual(parse_unit_price_usd("20.50\u20ac"), Decimal("24.60"))
        self.assertEqual(parse_unit_price_usd("70\u20ac99\u00a2"), Decimal("85.19"))
        self.assertEqual(parse_unit_price_usd("29\u20ac50\u00a2"), Decimal("35.40"))

    def test_rejects_ambiguous_or_empty(self):
        self.assertIsNone(parse_unit_price_usd("19.00"))
        self.assertIsNone(parse_unit_price_usd("EUR $10"))
        self.assertIsNone(parse_unit_price_usd("NULL"))


class DateTests(unittest.TestCase):
    def test_shapes_seen_in_the_extracts(self):
        cases = {
            "09:28,10-Dec-2025": date(2025, 12, 10),
            "2025-06-25;05:00:01 A.M.": date(2025, 6, 25),
            "10:31:43 P.M. 2026-01-14": date(2026, 1, 14),
            "03:02:34;17-JUL-2026": date(2026, 7, 17),
            "Fri Apr 10 15:32:26 2026": date(2026, 4, 10),
            "15-September-2025,16:55": date(2025, 9, 15),
            "04/29/26,13:42": date(2026, 4, 29),
            "29.07.2025 20:59:59": date(2025, 7, 29),
            "2025-10-29T14:28:22": date(2025, 10, 29),
            "2025-08-26T20:57:40.674": date(2025, 8, 26),
            " 2-AUG-2025,03:07": date(2025, 8, 2),
            "12:02:54 P.M. 12/17/25": date(2025, 12, 17),
            "03/31/26 04:38:16 P.M.": date(2026, 3, 31),
        }
        for raw, expected in cases.items():
            self.assertEqual(parse_order_date(raw), expected, raw)


class AuthorTests(unittest.TestCase):
    def test_same_names_are_one_set(self):
        together = author_keys("Paul, John")
        flipped = author_keys("John, Paul")
        solo = author_keys("John")
        self.assertEqual(together, flipped)
        self.assertNotEqual(together, solo)
        self.assertEqual(len({together, flipped, solo, author_keys("Paul")}), 3)


class ReconcileTests(unittest.TestCase):
    def test_one_field_links_and_chains_stay_one_person(self):
        users = pd.DataFrame(
            [
                {
                    "user_id": 1,
                    "name": "John",
                    "address": "1 Main",
                    "phone": "111",
                    "email": "a@b.test",
                    "name_key": "john",
                    "address_key": "1 main",
                    "phone_key": "111",
                    "email_key": "a@b.test",
                },
                {
                    "user_id": 2,
                    "name": "Johnny",
                    "address": "1 Main",
                    "phone": "111",
                    "email": "a@b.test",
                    "name_key": "johnny",
                    "address_key": "1 main",
                    "phone_key": "111",
                    "email_key": "a@b.test",
                },
                {
                    "user_id": 3,
                    "name": "Johnny",
                    "address": "2 Main",
                    "phone": "111",
                    "email": "a@b.test",
                    "name_key": "johnny",
                    "address_key": "2 main",
                    "phone_key": "111",
                    "email_key": "a@b.test",
                },
                {
                    "user_id": 4,
                    "name": "Other",
                    "address": "9 Side",
                    "phone": "999",
                    "email": "z@b.test",
                    "name_key": "other",
                    "address_key": "9 side",
                    "phone_key": "999",
                    "email_key": "z@b.test",
                },
            ]
        )
        labels, _examples = reconcile_users(users)
        self.assertEqual(labels.nunique(), 2)
        self.assertEqual(labels.iloc[0], labels.iloc[1])
        self.assertEqual(labels.iloc[1], labels.iloc[2])
        self.assertNotEqual(labels.iloc[0], labels.iloc[3])


if __name__ == "__main__":
    unittest.main()
