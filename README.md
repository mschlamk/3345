# Stock Momentum Watcher

## Features
- Monitors up to **20 stocks** per run.
- Uses MA/volume rules to classify each stock as **STAY / TRIM / CUT**.
- Provides a **table output** in CLI and in a simple web UI.
- Includes a **score key** so each numeric score has an action meaning.

## Install
```bash
pip install -r requirements.txt
```

## CLI Usage
```bash
python stock_watcher.py NVDA,AMD,SMCI
python stock_watcher.py NVDA,AMD --weak-sector
python stock_watcher.py NVDA,AMD --weak-earnings-reaction --period 6mo
```

The run prints a table with Symbol, Action, Score, Reason, and Volume note.

Score key used by the app:
- `CUT <= -4`
- `TRIM = -3..-1`
- `STAY >= 0`

## UI Usage (table view)
```bash
streamlit run ui.py
```
Then open the local URL shown by Streamlit.
