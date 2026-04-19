---
name: accuracy-tracker
domain: fund
version: 0.1.0
role: Performance Attribution Analyst
description: >
  Scores royal-rumble predictions against reality. Reads predictions.json
  (single-ticker rumbles), comparisons.json (pair verdicts), pulls live
  prices via price-desk, computes hit rates. Pair-relative scoring is
  cleaner signal than absolute (controls for market beta).
  Commands: .accuracy | .accuracy summary | .accuracy rumbles | .accuracy pairs | .accuracy TICKER | .accuracy log
  NOT for: making new predictions (use .rumble).
  NOT for: pulling live market data (use price-desk/fundamentals-desk/technicals-desk).
  NOT for: Howard Marks-style memo writeups (use .journalist).
capabilities:
  reads:
    - "royal-rumble/data/predictions.json"
    - "royal-rumble/data/comparisons.json"
    - "price-desk output"
  writes:
    - "accuracy-tracker/data/*.jsonl"
  calls:
    - "price-desk (via .price)"
  cannot:
    - "modify other skills' data"
    - "create new predictions"
    - "write outside own data folder"
unix_contract:
  data_format: "jsonl"
  schema_version: "0.1.0"
  stdin_support: false
  stdout_format: "json"
  composable_with:
    - "price-desk"
    - "royal-rumble"
---

# Accuracy Tracker — Performance Attribution Analyst

Converts stored hypotheses into measurable track record. Without this skill, every rumble is just an opinion. With this skill, every rumble is a data point.

## 🎯 COMMANDS

- `.accuracy` — menu
- `.accuracy summary` — cross-all dashboard
- `.accuracy rumbles` — score every single-ticker rumble (hit rate)
- `.accuracy pairs` — score every .compare verdict (pair-relative, cleanest signal)
- `.accuracy TICKER` — score one ticker's rumble history
- `.accuracy log [N]` — recent scoring runs

## 🔬 SCORING LOGIC

**Single-ticker:**
- STRONG BUY / BUY → expected direction: up → HIT if actual return > 0
- STRONG SELL / SELL → expected direction: down → HIT if actual return < 0
- HOLD → excluded from hit/miss count (no directional prediction)

**Pair-relative (cleaner):**
- Winner = A → HIT if A outperformed B (spread > 0)
- Winner = B → HIT if B outperformed A (spread < 0)
- Controls for market beta; measures actual stock-picking skill

## 📊 WHY PAIR-RELATIVE MATTERS

```
Single-ticker: "NVDA is a BUY" → NVDA +10% while market +8% = +2% alpha
Pair-relative: "NVDA beats AMD" → NVDA +13% / AMD +5% → +8% spread

Same system, 4x cleaner signal. This is how real funds grade analysts.
```

## 🏛️ DATA SOURCES

```
Reads:
  royal-rumble/data/predictions.json        → rumble history
  royal-rumble/data/comparisons.json        → pair history
Pulls live:
  price-desk                                → current prices
Writes:
  accuracy-tracker/data/accuracy-scores.jsonl → score trend log
```

## 🎭 CALIBRATION MILESTONES

```
5 rumbles:   too early — statistical noise
10 rumbles:  first trend visible
20 rumbles:  legend-level attribution starts working
50 rumbles:  v1.0 calibration threshold
100 rumbles: edge provable or disprovable
```
