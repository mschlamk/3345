#!/usr/bin/env python3
"""Momentum and volume-based stock trend watcher."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional

import pandas as pd

MAX_SYMBOLS = 20


@dataclass
class Alert:
    action: str
    score: int
    volume_note: str
    summary: str


def score_key() -> str:
    return "CUT <= -4, TRIM = -3..-1, STAY >= 0"


def parse_symbols(symbols_input: str) -> list[str]:
    symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    unique_symbols = list(dict.fromkeys(symbols))
    if not unique_symbols:
        raise ValueError("Provide at least one symbol.")
    if len(unique_symbols) > MAX_SYMBOLS:
        raise ValueError(f"You can monitor at most {MAX_SYMBOLS} symbols per run.")
    return unique_symbols


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ma20"] = out["Close"].rolling(20).mean()
    out["ma50"] = out["Close"].rolling(50).mean()
    out["vol20"] = out["Volume"].rolling(20).mean()
    out["down_day"] = out["Close"] < out["Close"].shift(1)
    out["heavy_down_day"] = out["down_day"] & (out["Volume"] > 1.4 * out["vol20"])
    return out


def _last_n_below_ma20(df: pd.DataFrame, n: int = 7) -> int:
    return int((df.tail(n)["Close"] < df.tail(n)["ma20"]).sum())


def _failed_rebounds(df: pd.DataFrame, lookback: int = 15) -> int:
    recent = df.tail(lookback)
    return int(((recent["High"] > recent["ma20"]) & (recent["Close"] < recent["ma20"])).sum())


def _reclaimed_pullback(df: pd.DataFrame, lookback: int = 20) -> bool:
    recent = df.tail(lookback)
    return bool((recent["Close"] < recent["ma20"]).any() and (recent.iloc[-1]["Close"] > recent.iloc[-1]["ma20"]))


def classify(df: pd.DataFrame, weak_sector: bool = False, weak_earnings_reaction: bool = False) -> Alert:
    if len(df) < 60:
        raise ValueError("Need at least 60 rows of OHLCV data.")

    dfi = compute_indicators(df)
    last = dfi.iloc[-1]

    score = 0
    notes: list[str] = []

    if (last["Close"] > last["ma20"]) and (last["ma20"] > last["ma50"]) and _reclaimed_pullback(dfi):
        score += 2
        notes.append("trend structure intact (Close>MA20>MA50)")
    below_ma20_count = _last_n_below_ma20(dfi)
    if below_ma20_count >= 4:
        score -= 2
        notes.append(f"{below_ma20_count}/7 recent closes below MA20")
    failed_rebounds = _failed_rebounds(dfi)
    if failed_rebounds >= 2:
        score -= 1
        notes.append(f"{failed_rebounds} failed rebound attempts")
    heavy_down_days_10 = int(dfi.tail(10)["heavy_down_day"].sum())
    if heavy_down_days_10 >= 2:
        score -= 2
        notes.append(f"{heavy_down_days_10} heavy-volume down days in last 10 sessions")
    if last["Close"] < 0.98 * last["ma50"]:
        score -= 3
        notes.append("decisive break below MA50")
    if weak_earnings_reaction:
        score -= 1
        notes.append("weak earnings reaction flag")
    if weak_sector:
        score -= 1
        notes.append("sector weakness flag")

    action = "CUT" if score <= -4 else "TRIM" if score <= -1 else "STAY"

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

    return Alert(action=action, score=score, volume_note=volume_note, summary="; ".join(notes) if notes else "no major warning signals")


def load_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker(symbol).history(period=period, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No data returned for symbol: {symbol}")
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def analyze_symbols(symbols: list[str], period: str, weak_sector: bool, weak_earnings_reaction: bool) -> pd.DataFrame:
    rows = []
    for symbol in symbols:
        try:
            alert = classify(load_data(symbol, period=period), weak_sector=weak_sector, weak_earnings_reaction=weak_earnings_reaction)
            rows.append({"Symbol": symbol, "Action": alert.action, "Score": alert.score, "Reason": alert.summary, "Volume": alert.volume_note})
        except Exception as exc:
            rows.append({"Symbol": symbol, "Action": "ERROR", "Score": -999, "Reason": str(exc), "Volume": "n/a"})
    return pd.DataFrame(rows)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Stock momentum watcher with MA/volume alerts")
    parser.add_argument("symbols", help="Comma-separated symbols (max 20), e.g. NVDA,AMD,SMCI")
    parser.add_argument("--period", default="1y")
    parser.add_argument("--weak-sector", action="store_true")
    parser.add_argument("--weak-earnings-reaction", action="store_true")
    args = parser.parse_args(argv)

    symbols = parse_symbols(args.symbols)
    table = analyze_symbols(symbols, args.period, args.weak_sector, args.weak_earnings_reaction)
    print(table.to_string(index=False))
    print(f"\nScore key: {score_key()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
