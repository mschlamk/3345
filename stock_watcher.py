#!/usr/bin/env python3
"""Momentum and volume-based stock trend watcher.

Rules implemented from user guidance:
- STAY: strong uptrend (price > MA20, MA20 > MA50, pullback reclaim behavior)
- TRIM: warning phase (repeated closes below MA20, failed rebounds, heavy down-volume days)
- CUT: possible trend break (decisive break below MA50 + additional weakness signals)

The script prints a concise alert summary whenever it runs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class Alert:
    action: str
    score: int
    volume_note: str
    summary: str


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ma20"] = out["Close"].rolling(20).mean()
    out["ma50"] = out["Close"].rolling(50).mean()
    out["vol20"] = out["Volume"].rolling(20).mean()
    out["down_day"] = out["Close"] < out["Close"].shift(1)
    out["heavy_down_day"] = out["down_day"] & (out["Volume"] > 1.4 * out["vol20"])
    return out


def _last_n_below_ma20(df: pd.DataFrame, n: int = 7) -> int:
    recent = df.tail(n)
    return int((recent["Close"] < recent["ma20"]).sum())


def _failed_rebounds(df: pd.DataFrame, lookback: int = 15) -> int:
    """Count attempts that moved over MA20 intraperiod but closed back under it."""
    recent = df.tail(lookback)
    cond = (recent["High"] > recent["ma20"]) & (recent["Close"] < recent["ma20"])
    return int(cond.sum())


def _reclaimed_pullback(df: pd.DataFrame, lookback: int = 20) -> bool:
    recent = df.tail(lookback)
    # Pullback reclaim proxy: touched/closed below MA20 at least once, now closed above MA20.
    touched = (recent["Close"] < recent["ma20"]).any()
    now_above = recent.iloc[-1]["Close"] > recent.iloc[-1]["ma20"]
    return bool(touched and now_above)


def classify(df: pd.DataFrame, weak_sector: bool = False, weak_earnings_reaction: bool = False) -> Alert:
    if len(df) < 60:
        raise ValueError("Need at least 60 rows of OHLCV data.")

    dfi = compute_indicators(df)
    last = dfi.iloc[-1]

    below_ma20_count = _last_n_below_ma20(dfi)
    failed_rebounds = _failed_rebounds(dfi)
    heavy_down_days_10 = int(dfi.tail(10)["heavy_down_day"].sum())

    strong_uptrend = (
        (last["Close"] > last["ma20"]) and
        (last["ma20"] > last["ma50"]) and
        _reclaimed_pullback(dfi)
    )

    decisive_break_ma50 = (last["Close"] < 0.98 * last["ma50"])  # 2% under MA50

    score = 0
    notes = []

    if strong_uptrend:
        score += 2
        notes.append("trend structure intact (Close>MA20>MA50)")

    if below_ma20_count >= 4:
        score -= 2
        notes.append(f"{below_ma20_count}/7 recent closes below MA20")

    if failed_rebounds >= 2:
        score -= 1
        notes.append(f"{failed_rebounds} failed rebound attempts")

    if heavy_down_days_10 >= 2:
        score -= 2
        notes.append(f"{heavy_down_days_10} heavy-volume down days in last 10 sessions")

    if decisive_break_ma50:
        score -= 3
        notes.append("decisive break below MA50")

    if weak_earnings_reaction:
        score -= 1
        notes.append("weak earnings reaction flag")

    if weak_sector:
        score -= 1
        notes.append("sector weakness flag")

    if score <= -4:
        action = "CUT"
    elif score <= -1:
        action = "TRIM"
    else:
        action = "STAY"

    vol = dfi.tail(10)
    down_vol = vol[vol["down_day"]]["Volume"].mean()
    up_vol = vol[~vol["down_day"]]["Volume"].mean()

    if pd.notna(down_vol) and pd.notna(up_vol):
        if down_vol > 1.15 * up_vol:
            volume_note = "Distribution risk: down-day volume is heavier than up-day volume."
        elif up_vol > 1.1 * down_vol:
            volume_note = "Constructive: rallies are occurring on stronger volume than dips."
        else:
            volume_note = "Neutral volume balance between up and down days."
    else:
        volume_note = "Insufficient mixed up/down sessions to compare volume profile."

    summary = "; ".join(notes) if notes else "no major warning signals"
    return Alert(action=action, score=score, volume_note=volume_note, summary=summary)


def load_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is required for live data. Install with: pip install yfinance") from exc

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No data returned for symbol: {symbol}")
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Stock momentum watcher with MA/volume alerts")
    parser.add_argument("symbol", help="Ticker symbol, e.g. NVDA")
    parser.add_argument("--period", default="1y", help="History period (default: 1y)")
    parser.add_argument("--weak-sector", action="store_true", help="Flag simultaneous sector weakness")
    parser.add_argument("--weak-earnings-reaction", action="store_true", help="Flag weak post-earnings behavior")

    args = parser.parse_args(argv)

    df = load_data(args.symbol, period=args.period)
    alert = classify(df, weak_sector=args.weak_sector, weak_earnings_reaction=args.weak_earnings_reaction)

    print(f"[{args.symbol}] ACTION: {alert.action} (score={alert.score})")
    print(f"Reason: {alert.summary}")
    print(f"Volume: {alert.volume_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
