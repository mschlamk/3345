import pandas as pd

from stock_watcher import classify, parse_symbols


def _build_df(close, volume):
    idx = pd.date_range("2025-01-01", periods=len(close), freq="B")
    return pd.DataFrame({"Open": close, "High": [c * 1.01 for c in close], "Low": [c * 0.99 for c in close], "Close": close, "Volume": volume}, index=idx)


def test_stay_signal_on_constructive_trend():
    df = _build_df(list(range(100, 170)), [1_000_000] * 70)
    assert classify(df).action == "STAY"


def test_cut_signal_on_break_and_distribution():
    close = list(range(100, 150)) + [148, 146, 144, 142, 140, 137, 134, 130, 126, 120]
    volume = [1_000_000] * 50 + [2_500_000, 2_400_000, 2_200_000, 2_100_000, 2_300_000, 2_700_000, 2_800_000, 2_600_000, 2_900_000, 3_100_000]
    assert classify(_build_df(close, volume), weak_sector=True).action == "CUT"


def test_parse_symbols_limit_and_cleanup():
    assert parse_symbols(" nvda, AMD, nvda ") == ["NVDA", "AMD"]
