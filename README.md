# Five-store sales desk

Cleaned sales extracts for five bookstores, with a browser desk for the figures each store is graded on.

Open `docs/index.html` after the data file has been generated. The page has a store switcher and three sections:

1. Revenue — top 5 days as `YYYY-MM-DD`, and the daily revenue chart.
2. Customers — real customer count, the best buyer as an array of user ids, and a chat for the reconciliation.
3. Authors — distinct author sets, the set that sold the most copies, and a chat for those sets.

## Reproduce

```bash
pip install -r requirements.txt
python -m bookstore_analytics
python -m unittest tests.test_cleaning
```

That rewrites `docs/data.js`, `output/summary.json`, and a matplotlib PNG per store in `output/charts/`. The page reads `docs/data.js`, so it works from disk without a server.

## Cleaning

Orders, users, and books are loaded from each `STORE*` folder (`orders.parquet`, `users.csv`, `books.yaml`).

- Timestamps use several spellings (ISO, `10-Dec-2025`, `04/29/26`, `29.07.2025`, `Fri Apr 10 …`). Slash dates are month/day because the first number never exceeds 12 and the second often does. Dot dates are day/month for the opposite reason. The chart and the top-5 list use the calendar date only.
- Money is stored in cents. `$`, `USD`, `€`, and `EUR` mark the currency. A symbol placed between the major units and the cents is the decimal point: `70€99¢` is €70.99, `$20¢25` is $20.25, `46$99¢` is $46.99. Euro amounts are multiplied by 1.20 and rounded half-up to the cent. `paid_price` is that unit price times quantity.
- Rows with a blank or impossible year stay in the catalogue; the year is left empty. No order in these extracts failed the price or date parser.
- Duplicate ids would be collapsed to the first row. These extracts have none.

## Customers

A raw `user_id` is not a person. Two rows are linked when at most one of name, address, phone, and email differs. Phones are the last 10 digits. Text is compared case-insensitively, with whitespace collapsed. A blank address does not count as the same address.

If A matches B and B matches C, all three are one person. Each step changes a single field; the two ends can differ in two fields. The best-buyer array is every `user_id` in that person's group. Matching does not over-merge: the largest group in any store is three rows.

## Authors

Names on a book are split on commas. Order and capitalisation do not create a new set, so "Paul, John" and "John, Paul" are one set, and either name alone is a different set. The set count is taken from the catalogue, including titles that never sold. Popularity is copies sold (`quantity` summed), not titles and not revenue.

## What the desk is not

The two chats answer only from the tables for the selected store. They do not call an external model. A question outside customers or author sets gets a short list of what that chat can answer.
