# Stock Momentum Watcher

Simple CLI app that rates a stock as **STAY / TRIM / CUT** using moving averages and volume behavior.

## What it checks

- **Strong uptrend (STAY bias):**
  - Price above 20-day moving average (MA20)
  - MA20 above MA50
  - Pullback reclaim behavior
- **Warning phase (TRIM bias):**
  - Repeated closes below MA20
  - Failed rebounds near MA20
  - Heavy-volume down days
- **Possible trend break (CUT bias):**
  - Decisive break below MA50
  - Optional weak earnings reaction flag
  - Optional sector weakness flag

It also prints a **volume condition note** (constructive / neutral / distribution risk).

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python stock_watcher.py NVDA
python stock_watcher.py AMD --weak-sector
python stock_watcher.py SMCI --weak-earnings-reaction --weak-sector
```

## Automation ideas

- Run every close with cron/GitHub Actions.
- Pipe output to Slack/Discord/email.
- Track score history in CSV and alert only on state changes.
