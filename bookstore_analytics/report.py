"""Write the dashboard data, the headline summary, and the matplotlib charts."""

from __future__ import annotations

import json
from pathlib import Path

from bookstore_analytics.analyze import analyze_store
from bookstore_analytics.charts import save_daily_revenue_chart
from bookstore_analytics.cleaning import load_store

ROOT = Path(__file__).resolve().parents[1]


def _headline(result: dict) -> dict:
    popular = [
        {"authors": item["authors"], "copies": item["copies"]} for item in result["most_popular"]
    ]
    buyers = [
        {"ids": item["ids"], "spend_cents": item["spend_cents"], "names": item["names"]}
        for item in result["best_buyers"]
    ]
    return {
        "top5_days": [item["date"] for item in result["top5_days"]],
        "top5_revenue_cents": [item["cents"] for item in result["top5_days"]],
        "unique_users": result["unique_users"],
        "unique_author_sets": result["unique_author_sets"],
        "most_popular": popular,
        "best_buyers": buyers,
        "total_cents": result["total_cents"],
        "extra_top5_tie_dates": result["top5_tie_dates"],
    }


def build(root: Path = ROOT) -> dict:
    data_dir = root / "data"
    stores = []
    headlines = {}
    chart_dir = root / "output" / "charts"
    for store_dir in sorted(path for path in data_dir.iterdir() if path.is_dir()):
        loaded = load_store(store_dir)
        result = analyze_store(store_dir.name, loaded)
        audit = result["audit"]
        if audit["dropped_price"] or audit["dropped_date"] or audit["dropped_keys"]:
            raise SystemExit(f"{store_dir.name} still has rows the cleaner could not read: {audit}")
        save_daily_revenue_chart(
            result["daily_revenue"],
            chart_dir / f"{store_dir.name.lower()}_daily_revenue.png",
            f"{store_dir.name} daily revenue",
        )
        result.pop("money_preview", None)
        stores.append(result)
        headlines[store_dir.name] = _headline(result)

    payload = {"stores": stores}
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    data_js = docs / "data.js"
    data_js.write_text(
        "window.DESK = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    summary_path = root / "output" / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(headlines, indent=2), encoding="utf-8")
    print(f"wrote {data_js} ({data_js.stat().st_size / 1_048_576:.1f} MB)")
    print(f"wrote {summary_path}")
    for name, headline in headlines.items():
        popular = headline["most_popular"][0]
        buyer = headline["best_buyers"][0]
        print(
            f"{name}: users={headline['unique_users']} "
            f"sets={headline['unique_author_sets']} "
            f"top day={headline['top5_days'][0]} "
            f"popular={', '.join(popular['authors'])} ({popular['copies']}) "
            f"buyer={buyer['ids']}"
        )
    return headlines
