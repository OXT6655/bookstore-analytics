from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def save_daily_revenue_chart(series: list[dict], path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(series)
    frame["day"] = pd.to_datetime(frame["date"])
    frame["dollars"] = frame["cents"] / 100
    plt.figure(figsize=(10, 4))
    plt.plot(frame["day"], frame["dollars"])
    plt.title(title)
    plt.xlabel("date")
    plt.ylabel("revenue, USD")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
