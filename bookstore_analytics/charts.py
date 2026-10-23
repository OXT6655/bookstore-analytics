"""Matplotlib export of daily revenue. The browser desk draws the same series."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def save_daily_revenue_chart(series: list[dict], path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(series)
    frame["day"] = pd.to_datetime(frame["date"])
    frame["dollars"] = frame["cents"] / 100
    figure, axis = plt.subplots(figsize=(11.2, 4.4), dpi=140)
    figure.patch.set_facecolor("#f7f5f0")
    axis.set_facecolor("#fffcf7")
    axis.plot(frame["day"], frame["dollars"], color="#1d4e89", linewidth=1.7)
    axis.fill_between(frame["day"], frame["dollars"], color="#1d4e89", alpha=0.12)
    axis.set_title(title, loc="left", color="#1c2430", fontsize=13, pad=12)
    axis.set_ylabel("Revenue (USD)")
    axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _pos: f"${value:,.0f}"))
    axis.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axis.grid(axis="y", color="#e3dcd0", linewidth=0.8)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(colors="#5e6a78")
    figure.autofmt_xdate(rotation=0, ha="center")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)
