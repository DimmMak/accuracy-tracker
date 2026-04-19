# CHANGELOG — Accuracy Tracker

## v0.2.0 — 2026-04-18

**World-Class Overhaul shipped.** Part of the fleet-wide upgrade to tree+plugin+unix architecture.

- 🌳 **Tree:** `domain:` field added to frontmatter (fund)
- 🎮 **Plugin:** `capabilities:` block declares reads / writes / calls / cannot
- 🐧 **Unix:** `unix_contract:` block declares data_format / schema_version / stdin_support / stdout_format / composable_with
- 🛡️ Schema v0.3 validation required at install (via `future-proof/scripts/validate-skill.py`)
- 🔗 Install converted to symlink pattern (kills drift between Desktop source and live install)
- 🏷️ Tagged at `v-2026-04-18-world-class` for rollback

See `memory/project_world_class_architecture.md` for the full model.

---


## [2026-04-18] — v0.1.0 — Initial ship

**Trigger:** User noticed "hypotheses are being stored but nothing's scoring them yet — that's the T1 gap." Shipped.

### Shipped
- `scripts/accuracy.py` — reads predictions.json + comparisons.json, calls price-desk for live prices, computes hit rates
- 6 commands: menu, summary, rumbles, pairs, ticker-history, log
- Every scoring run logs to `data/accuracy-scores.jsonl`

### First-run validation (2026-04-18)
```
Rumbles logged:     5 (TSLA/AMD/MU/CRM/NOW on 2026-04-17)
Scorable (non-HOLD): 3 (AMD +9.1%, MU +20.5%, NOW +16.6%)
Hits:                3/3 → 100% hit rate
  (but 1-day sample — statistical noise, need 20+ for signal)
```

### Pair-relative scoring (cleanest signal)
Pair-relative spreads control for market beta. STRONG BUY on a name that goes up 10% in a 9% market = only +1% alpha. But "A beats B by 8%" when B went up 2% = +8% pure alpha. Real hedge funds use this metric to grade analysts.

### Milestones ahead
- 10 rumbles → first real trend
- 20 rumbles → legend attribution works
- 50 rumbles → v1.0 calibration threshold
