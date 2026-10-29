from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
from pathlib import Path

import pandas as pd
import yaml

EUR_TO_USD = Decimal("1.2")
CENT = Decimal("0.01")
IDENTITY_FIELDS = ("name", "address", "phone", "email")

_EMPTY_TOKENS = {"", "nan", "none", "null", "n/a", "na", "-", "nil", "nat"}
_SPACE_RE = re.compile(r"\s+")
_CURRENCY_RE = re.compile(r"eur|usd|€|\$", re.IGNORECASE)
_EURO_RE = re.compile(r"eur|€", re.IGNORECASE)
_USD_RE = re.compile(r"usd|\$", re.IGNORECASE)

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
_TIME_RE = re.compile(
    r"(?P<h>\d{1,2}):(?P<min>\d{2})(?::(?P<sec>\d{2}))?(?:\s*(?P<ampm>AM|PM))?",
    re.IGNORECASE,
)
_ISO_RE = re.compile(r"(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})")
_DOT_RE = re.compile(r"(?P<d>\d{1,2})\.(?P<m>\d{1,2})\.(?P<y>\d{4})")
_SLASH_RE = re.compile(r"(?P<m>\d{1,2})/(?P<d>\d{1,2})/(?P<y>\d{2,4})")
_NAMED_RE = re.compile(
    rf"(?P<d>\d{{1,2}})[\s\-]+(?P<mon>{_MONTH_ALT})[\s\-]+(?P<y>\d{{4}})",
    re.IGNORECASE,
)
_CTIME_RE = re.compile(
    rf"\b(?P<mon>{_MONTH_ALT})\s+(?P<d>\d{{1,2}})\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def normalize_text(value) -> str:
    if _is_missing(value):
        return ""
    text = _SPACE_RE.sub(" ", str(value).replace("\u00a0", " ")).strip().casefold()
    if text in _EMPTY_TOKENS:
        return ""
    return text


def normalize_phone(value) -> str:
    if _is_missing(value):
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits or digits in {"0"}:
        return ""
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def display_text(value) -> str:
    if _is_missing(value):
        return ""
    text = _SPACE_RE.sub(" ", str(value).replace("\u00a0", " ")).strip()
    if text.casefold() in _EMPTY_TOKENS:
        return ""
    return text


def parse_unit_price_usd(value) -> Decimal | None:
    if _is_missing(value):
        return None
    raw = str(value).replace("\u00a0", " ").strip()
    if raw.casefold() in _EMPTY_TOKENS:
        return None
    is_eur = _EURO_RE.search(raw) is not None
    is_usd = _USD_RE.search(raw) is not None
    if is_eur == is_usd:
        return None
    cleaned = re.sub(r"eur|usd", "", raw, flags=re.IGNORECASE)
    cleaned = _SPACE_RE.sub("", cleaned)
    cleaned = re.sub(r"(?<=\d)[€$¢](?=\d)", ".", cleaned)
    cleaned = re.sub(r"[€$¢]", "", cleaned)
    cleaned = cleaned.replace(",", ".")
    if cleaned.count(".") > 1 or cleaned in {"", "."}:
        return None
    if cleaned.startswith("."):
        cleaned = "0" + cleaned
    if cleaned.endswith("."):
        cleaned = cleaned + "0"
    if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
        return None
    amount = Decimal(cleaned)
    if amount < 0:
        return None
    rate = EUR_TO_USD if is_eur else Decimal("1")
    return (amount * rate).quantize(CENT, rounding=ROUND_HALF_UP)


def _calendar_date(year: int, month: int, day: int) -> date | None:
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _normalize_timestamp_text(value) -> str:
    text = str(value).replace("\u00a0", " ").strip()
    text = re.sub(r"(?i)\b([AP])\s*\.\s*M\s*\.", r"\1M", text)
    text = re.sub(r"(?<=\d)T(?=\d)", " ", text)
    text = text.replace(",", " ").replace(";", " ")
    return _SPACE_RE.sub(" ", text).strip()


def _extract_clock(text: str) -> bool:
    match = _TIME_RE.search(text)
    if match is None:
        return False
    hour = int(match.group("h"))
    minute = int(match.group("min"))
    second = int(match.group("sec") or 0)
    ampm = match.group("ampm")
    if ampm:
        marker = ampm.upper()
        if marker == "AM":
            if hour == 12:
                hour = 0
            elif hour > 12:
                return False
        elif hour < 12:
            hour += 12
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        return False
    return True


def parse_order_date(value) -> date | None:
    if _is_missing(value):
        return None
    text = _normalize_timestamp_text(value)
    if not text or not _extract_clock(text):
        return None

    parsed: date | None = None
    iso = _ISO_RE.search(text)
    if iso:
        parsed = _calendar_date(int(iso.group("y")), int(iso.group("m")), int(iso.group("d")))
    if parsed is None:
        dotted = _DOT_RE.search(text)
        if dotted:
            parsed = _calendar_date(
                int(dotted.group("y")), int(dotted.group("m")), int(dotted.group("d"))
            )
    if parsed is None:
        slash = _SLASH_RE.search(text)
        if slash:
            parsed = _calendar_date(
                int(slash.group("y")), int(slash.group("m")), int(slash.group("d"))
            )
    if parsed is None:
        named = _NAMED_RE.search(text)
        if named:
            parsed = _calendar_date(
                int(named.group("y")),
                _MONTHS[named.group("mon").casefold()],
                int(named.group("d")),
            )
    if parsed is None:
        ctime = _CTIME_RE.search(text)
        year = _YEAR_RE.search(text)
        if ctime and year:
            parsed = _calendar_date(
                int(year.group(1)),
                _MONTHS[ctime.group("mon").casefold()],
                int(ctime.group("d")),
            )
    return parsed


def author_keys(value) -> tuple[str, ...]:
    if _is_missing(value):
        return ()
    if isinstance(value, (list, tuple)):
        raw_parts = [str(part) for part in value]
    else:
        raw_parts = str(value).split(",")
    keys: list[str] = []
    seen: set[str] = set()
    for part in raw_parts:
        key = normalize_text(part)
        if not key or key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return tuple(sorted(keys))


def _yaml_value(record: dict, name: str):
    if name in record:
        return record[name]
    if f":{name}" in record:
        return record[f":{name}"]
    return None


def _clean_year(value) -> int | None:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        year = value
    else:
        text = str(value).strip()
        if not re.fullmatch(r"\d{3,4}", text):
            return None
        year = int(text)
    if 1400 <= year <= 2030:
        return year
    return None


def load_books(path: Path) -> tuple[pd.DataFrame, dict]:
    documents = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    rows = []
    bad_year = 0
    blank_author = 0
    seen_ids: set[int] = set()
    duplicate_ids = 0
    for record in documents:
        book_id = _yaml_value(record, "id")
        try:
            book_id = int(book_id)
        except (TypeError, ValueError):
            continue
        if book_id in seen_ids:
            duplicate_ids += 1
            continue
        seen_ids.add(book_id)
        year = _clean_year(_yaml_value(record, "year"))
        if year is None:
            bad_year += 1
        keys = author_keys(_yaml_value(record, "author"))
        if not keys:
            blank_author += 1
        title = display_text(_yaml_value(record, "title")) or "(untitled)"
        rows.append(
            {
                "book_id": book_id,
                "title": title,
                "author_raw": display_text(_yaml_value(record, "author")),
                "author_keys": keys,
                "genre": display_text(_yaml_value(record, "genre")),
                "publisher": display_text(_yaml_value(record, "publisher")),
                "year": year,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(
            columns=["book_id", "title", "author_raw", "author_keys", "genre", "publisher", "year"]
        )
    frame["year"] = frame["year"].astype("Int64")
    audit = {
        "books_in": len(documents),
        "books_used": int(len(frame)),
        "duplicate_book_ids": duplicate_ids,
        "books_bad_year": bad_year,
        "books_blank_author": blank_author,
    }
    return frame, audit


def load_users(path: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(path)
    frame = pd.DataFrame(
        {
            "user_id": pd.to_numeric(raw["id"], errors="coerce"),
            "name": raw["name"].map(display_text),
            "address": raw["address"].map(display_text),
            "phone": raw["phone"].map(display_text),
            "email": raw["email"].map(display_text),
            "name_key": raw["name"].map(normalize_text),
            "address_key": raw["address"].map(normalize_text),
            "phone_key": raw["phone"].map(normalize_phone),
            "email_key": raw["email"].map(normalize_text),
        }
    )
    before = len(frame)
    frame = frame.dropna(subset=["user_id"]).copy()
    frame["user_id"] = frame["user_id"].astype(int)
    duplicate_ids = int(frame["user_id"].duplicated().sum())
    frame = frame.drop_duplicates(subset=["user_id"], keep="first")
    audit = {
        "users_in": before,
        "users_used": int(len(frame)),
        "duplicate_user_ids": duplicate_ids,
        "missing_address": int((frame["address"] == "").sum()),
        "missing_name": int((frame["name"] == "").sum()),
        "missing_phone": int((frame["phone"] == "").sum()),
        "missing_email": int((frame["email"] == "").sum()),
    }
    return frame.reset_index(drop=True), audit


def load_orders(path: Path, book_ids: set[int]) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_parquet(path)
    rows = []
    dropped_price = 0
    dropped_date = 0
    dropped_quantity = 0
    dropped_keys = 0
    eur_lines = 0
    usd_lines = 0
    unknown_book = 0
    for record in raw.itertuples(index=False):
        try:
            order_id = int(record.id)
            user_id = int(record.user_id)
            book_id = int(record.book_id)
            quantity = int(record.quantity)
        except (TypeError, ValueError):
            dropped_keys += 1
            continue
        if quantity < 1:
            dropped_quantity += 1
            continue
        unit = parse_unit_price_usd(record.unit_price)
        if unit is None:
            dropped_price += 1
            continue
        order_day = parse_order_date(record.timestamp)
        if order_day is None:
            dropped_date += 1
            continue
        raw_price = str(record.unit_price)
        if _EURO_RE.search(raw_price):
            eur_lines += 1
        else:
            usd_lines += 1
        if book_id not in book_ids:
            unknown_book += 1
        unit_cents = int(unit * 100)
        rows.append(
            {
                "order_id": order_id,
                "user_id": user_id,
                "book_id": book_id,
                "quantity": quantity,
                "unit_price_usd": float(unit),
                "paid_price": float(unit * quantity),
                "paid_cents": unit_cents * quantity,
                "timestamp": pd.Timestamp(order_day),
                "date": order_day.isoformat(),
                "year": order_day.year,
                "month": order_day.month,
                "day": order_day.day,
                "known_book": book_id in book_ids,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(
            columns=[
                "order_id",
                "user_id",
                "book_id",
                "quantity",
                "unit_price_usd",
                "paid_price",
                "paid_cents",
                "timestamp",
                "date",
                "year",
                "month",
                "day",
                "known_book",
            ]
        )
    else:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        frame["quantity"] = frame["quantity"].astype(int)
        frame["year"] = frame["year"].astype(int)
        frame["month"] = frame["month"].astype(int)
        frame["day"] = frame["day"].astype(int)
    duplicate_ids = int(frame["order_id"].duplicated().sum()) if len(frame) else 0
    frame = frame.drop_duplicates(subset=["order_id"], keep="first")
    audit = {
        "orders_in": int(len(raw)),
        "orders_used": int(len(frame)),
        "duplicate_order_ids": duplicate_ids,
        "dropped_price": dropped_price,
        "dropped_date": dropped_date,
        "dropped_quantity": dropped_quantity,
        "dropped_keys": dropped_keys,
        "eur_lines": eur_lines,
        "usd_lines": usd_lines,
        "unknown_book": unknown_book,
    }
    return frame.reset_index(drop=True), audit


class _UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        parent = self.parent
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def reconcile_users(users: pd.DataFrame) -> tuple[pd.Series, list[dict]]:
    records = [
        {
            "name": row.name_key,
            "address": row.address_key,
            "phone": row.phone_key,
            "email": row.email_key,
        }
        for row in users.itertuples(index=False)
    ]
    finder = _UnionFind(len(records))
    buckets: dict[str, dict[str, list[int]]] = {field: defaultdict(list) for field in IDENTITY_FIELDS}
    for index, record in enumerate(records):
        for field in IDENTITY_FIELDS:
            if record[field]:
                buckets[field][record[field]].append(index)

    examples: list[dict] = []
    compared: set[tuple[int, int]] = set()
    for groups in buckets.values():
        for indexes in groups.values():
            if len(indexes) < 2:
                continue
            for left, right in combinations(indexes, 2):
                pair = (left, right) if left < right else (right, left)
                if pair in compared:
                    continue
                compared.add(pair)
                changed = [
                    field for field in IDENTITY_FIELDS if records[left][field] != records[right][field]
                ]
                if len(changed) > 1:
                    continue
                finder.union(left, right)
                if len(examples) < 24 and changed:
                    field = changed[0]
                    examples.append(
                        {
                            "user_ids": [
                                int(users.at[left, "user_id"]),
                                int(users.at[right, "user_id"]),
                            ],
                            "changed": field,
                            "values": [
                                str(users.at[left, field]),
                                str(users.at[right, field]),
                            ],
                        }
                    )

    labels = pd.Series([finder.find(index) for index in range(len(records))], index=users.index)
    return labels, examples


def load_store(store_dir: Path) -> dict:
    books, book_audit = load_books(store_dir / "books.yaml")
    users, user_audit = load_users(store_dir / "users.csv")
    orders, order_audit = load_orders(store_dir / "orders.parquet", set(books["book_id"].tolist()))
    cluster_labels, link_examples = reconcile_users(users)
    users = users.copy()
    users["cluster_label"] = cluster_labels
    return {
        "books": books,
        "users": users,
        "orders": orders,
        "link_examples": link_examples,
        "audit": {**book_audit, **user_audit, **order_audit},
    }


def spelling_table(books: pd.DataFrame) -> dict[str, str]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for raw in books["author_raw"]:
        for part in str(raw).split(","):
            shown = display_text(part)
            key = normalize_text(part)
            if key:
                counts[key][shown] += 1
    chosen = {}
    for key, spellings in counts.items():
        ranking = sorted(spellings.items(), key=lambda item: (-item[1], -len(item[0]), item[0].casefold()))
        chosen[key] = ranking[0][0]
    return chosen
