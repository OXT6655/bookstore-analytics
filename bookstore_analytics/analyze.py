from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

import pandas as pd

from bookstore_analytics.cleaning import spelling_table


def _money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(int(cents))
    return f"{sign}{cents // 100:,}.{cents % 100:02d}"


def _unique_keeping_order(values) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def analyze_store(name: str, loaded: dict) -> dict:
    users: pd.DataFrame = loaded["users"]
    orders: pd.DataFrame = loaded["orders"]
    books: pd.DataFrame = loaded["books"]
    audit = dict(loaded["audit"])

    labels = users["cluster_label"]
    cluster_of_label: dict[int, list[int]] = defaultdict(list)
    for index, label in labels.items():
        cluster_of_label[int(label)].append(int(index))

    user_cluster = dict(zip(users["user_id"].astype(int), labels.astype(int)))
    spend = defaultdict(int)
    copies_by_user = defaultdict(int)
    for row in orders.itertuples(index=False):
        label = user_cluster.get(int(row.user_id))
        if label is None:
            continue
        spend[label] += int(row.paid_cents)
        copies_by_user[label] += int(row.quantity)

    clusters = []
    for label, indexes in cluster_of_label.items():
        group = users.loc[indexes]
        changed = []
        for field in ("name", "address", "phone", "email"):
            if group[field].nunique(dropna=False) > 1:
                changed.append(field)
        ids = sorted(int(item) for item in group["user_id"])
        clusters.append(
            {
                "ids": ids,
                "names": _unique_keeping_order(group["name"]),
                "addresses": _unique_keeping_order(group["address"]),
                "phones": _unique_keeping_order(group["phone"]),
                "emails": _unique_keeping_order(group["email"]),
                "changed": changed,
                "spend_cents": int(spend.get(label, 0)),
                "copies": int(copies_by_user.get(label, 0)),
            }
        )
    clusters.sort(key=lambda item: (-item["spend_cents"], item["ids"]))

    size_counts = Counter(len(item["ids"]) for item in clusters)
    best = clusters[0] if clusters else None
    best_spend = best["spend_cents"] if best else 0
    best_ties = [item for item in clusters if item["spend_cents"] == best_spend and best_spend > 0]

    daily = (
        orders.groupby("date", as_index=False)["paid_cents"].sum().sort_values("date")
        if len(orders)
        else pd.DataFrame(columns=["date", "paid_cents"])
    )
    series = []
    if len(daily):
        start = date.fromisoformat(daily["date"].iloc[0])
        end = date.fromisoformat(daily["date"].iloc[-1])
        amounts = dict(zip(daily["date"], daily["paid_cents"].astype(int)))
        cursor = start
        while cursor <= end:
            key = cursor.isoformat()
            series.append({"date": key, "cents": int(amounts.get(key, 0))})
            cursor += timedelta(days=1)

    ranked_days = sorted(series, key=lambda item: (-item["cents"], item["date"]))
    positive_days = [item for item in ranked_days if item["cents"] > 0]
    top5 = positive_days[:5]
    cutoff = top5[-1]["cents"] if top5 else 0
    top_dates = {item["date"] for item in top5}
    tied_at_cutoff = [
        item["date"]
        for item in positive_days
        if item["cents"] == cutoff and item["date"] not in top_dates
    ]

    spellings = spelling_table(books)
    titles_by_set: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for row in books.itertuples(index=False):
        keys = tuple(row.author_keys)
        if not keys:
            continue
        titles_by_set[keys].append(row.title)

    book_set = {int(row.book_id): tuple(row.author_keys) for row in books.itertuples(index=False)}
    copies_by_set: dict[tuple[str, ...], int] = defaultdict(int)
    for row in orders.itertuples(index=False):
        keys = book_set.get(int(row.book_id))
        if not keys:
            continue
        copies_by_set[keys] += int(row.quantity)

    author_sets = []
    for keys, titles in titles_by_set.items():
        names = [spellings.get(key, key) for key in keys]
        author_sets.append(
            {
                "authors": names,
                "copies": int(copies_by_set.get(keys, 0)),
                "titles": titles,
            }
        )
    author_sets.sort(key=lambda item: (-item["copies"], ", ".join(item["authors"]).casefold()))
    top_copies = author_sets[0]["copies"] if author_sets else 0
    most_popular = [item for item in author_sets if item["copies"] == top_copies and top_copies > 0]

    solo = sum(1 for item in author_sets if len(item["authors"]) == 1)
    total_cents = int(orders["paid_cents"].sum()) if len(orders) else 0
    audit.update(
        {
            "real_users": len(clusters),
            "multi_record_people": sum(1 for item in clusters if len(item["ids"]) > 1),
            "records_in_merged_people": sum(len(item["ids"]) for item in clusters if len(item["ids"]) > 1),
            "component_sizes": {str(size): count for size, count in sorted(size_counts.items())},
            "orphan_orders": int((~orders["user_id"].isin(set(user_cluster))).sum()) if len(orders) else 0,
            "author_sets": len(author_sets),
            "solo_author_sets": solo,
            "collaborative_author_sets": len(author_sets) - solo,
            "total_cents": total_cents,
            "orders_with_known_book": int(orders["known_book"].sum()) if len(orders) else 0,
        }
    )

    return {
        "store": name,
        "audit": audit,
        "total_cents": total_cents,
        "order_count": int(len(orders)),
        "top5_days": [{"date": item["date"], "cents": item["cents"]} for item in top5],
        "top5_tie_dates": tied_at_cutoff,
        "daily_revenue": series,
        "unique_users": len(clusters),
        "best_buyers": [
            {
                "ids": item["ids"],
                "names": item["names"],
                "addresses": item["addresses"],
                "phones": item["phones"],
                "emails": item["emails"],
                "changed": item["changed"],
                "spend_cents": item["spend_cents"],
                "copies": item["copies"],
            }
            for item in best_ties
        ],
        "unique_author_sets": len(author_sets),
        "most_popular": [
            {
                "authors": item["authors"],
                "copies": item["copies"],
                "titles": item["titles"][:12],
                "title_count": len(item["titles"]),
            }
            for item in most_popular
        ],
        "author_sets": [
            {
                "authors": item["authors"],
                "copies": item["copies"],
                "titles": item["titles"],
            }
            for item in author_sets
        ],
        "clusters": clusters,
        "link_examples": loaded["link_examples"],
        "money_preview": {
            "total": _money(total_cents),
            "top_day": _money(top5[0]["cents"]) if top5 else "0.00",
        },
    }
