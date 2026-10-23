"""Print the desk figures. Used while checking the cleaners."""

from pathlib import Path

import pandas as pd

from bookstore_analytics.analyze import analyze_store
from bookstore_analytics.cleaning import load_store, parse_unit_price_usd

raw = pd.read_parquet(Path("data/STORE1/orders.parquet"))
usd = raw.unit_price.map(lambda value: float(parse_unit_price_usd(value) or -1))
print(
    "STORE1 max",
    round(usd.max(), 2),
    "over 500",
    int((usd > 500).sum()),
    "unparsed",
    int((usd < 0).sum()),
)

for store in sorted(path for path in Path("data").iterdir() if path.is_dir()):
    result = analyze_store(store.name, load_store(store))
    audit = result["audit"]
    print("==", store.name)
    print(
        "dropped",
        audit["dropped_price"],
        audit["dropped_date"],
        "total",
        result["money_preview"]["total"],
        "users",
        result["unique_users"],
        "sets",
        result["unique_author_sets"],
    )
    print(
        "top5",
        [(item["date"], f"{item['cents'] / 100:,.2f}") for item in result["top5_days"]],
    )
    print(
        "popular",
        [(", ".join(item["authors"]), item["copies"]) for item in result["most_popular"]],
    )
    buyer = result["best_buyers"][0]
    print(
        "best",
        buyer["ids"],
        f"{buyer['spend_cents'] / 100:,.2f}",
        buyer["names"],
        buyer["changed"],
    )
