# CHANGELOG — Accuracy Tracker

## v0.6.0 — 2026-04-23 — Auto-checkin loop (close the grading gap)

**Trigger:** user flagged P2 🔴 Critical — "6 predictions logged 2026-04-22, 0 checkins. Fleet logs but doesn't grade." Fund had prediction data but no systematic grading; every hit rate was manually triggered or stale.

### Shipped
- `.accuracy checkin` — idempotent auto-scorer; grades every prediction ≥24h old, skips predictions scored within the reschedule window (default 24h)
- `data/checkins.jsonl` — append-only per-checkin log; one record per (prediction_id, run_at); prediction_id = `{ticker}_{date}`
- `get_price_record()` helper — full price-desk record (carries `session_state` + `data_quality` from price-desk v0.3.0)
- Flags `--min-age=Nh` (age gate) and `--reschedule=Nh` (re-run gate) for tuning

### Verified (2026-04-23 21:38 UTC)
First run scored 7 predictions (AMD +19.70% HIT, MU +27.58% HIT, NOW +2.26% HIT, TSLA / CRM / 2× NVDA = HOLD). Fresh (<24h) prediction correctly skipped. Second run: Scored 0, Recent skipped 7 — idempotency confirmed. No duplicate records written.

### Schema
- Skill `version` 0.5.0 → 0.6.0
- New log schema `checkins.jsonl` v0.1 — records carry prediction_id, run_at, days_elapsed, score (HIT/MISS/N/A/UNSCORED), source_price_desk snapshot

### Why this ships P2 of Data-Integrity Foundation
Before this, rumble was a prediction generator with no closing loop. Now every rumble ≥24h old gets an audit-trailed score without manual effort. Compounding signal for `.accuracy legends`, `.accuracy review`, and `.accuracy cohort` — they all read the same feed now.

---

## v0.4.0 — 2026-04-20

**Weekly reflection ritual — Dalio's pain + reflection = progress, made concrete.**

- 🔬 **New command:** `.accuracy review [Nd]` — default 7d window, optional `14d` / `30d` / `90d`
- 📊 **6-section structured report:**
  1. What happened (hit/miss/hold/unscored breakdown)
  2. Your call vs Judge (hypothesis-vs-verdict divergence tracking)
  3. Legend scorecard for THIS WINDOW only (not all-time)
  4. Patterns Claude auto-surfaces (misses, divergences, over-HOLDing, unscored fetch fails, small-sample noise)
  5. Reflection prompts (user fills in — Claude does NOT fabricate your reflection)
  6. Metadata persisted to `data/reflections.jsonl` for trend tracking
- 🧬 **Divergence signal:** when you pre-registered a hypothesis and diverged from judge, it's flagged — divergence = training signal
- 📝 **User-owned reflection text:** machine tracks metadata only (hits/misses/patterns); your written reflections are YOURS — paste into notepad/journal
- 🕯️ **Ritual discipline:** closes each Sunday-morning review loop → compounds over weeks

**Why:** `.accuracy legends` (v0.3) shows WHO predicted well. `.accuracy review` closes the loop — forces you to actually LOOK at the data, ask Dalio's 5 reflection questions, and write down what you learned. Without this ritual, per-legend data is noise. With it, every week becomes a compounding calibration loop.

---

## v0.3.0 — 2026-04-20

**Per-legend hit-rate attribution.** Dalio believability-weighted decision-making, made explicit.

- 🏛️ **New command:** `.accuracy legends` — scores every voting + advisory legend's individual stance against actual forward return, aggregated across all rumbles
- 📊 **Hit / Miss / Neutral** breakdown per legend, sorted by hit rate
- 💰 **"Avg return when bullish"** column reveals which legends generate real alpha, not just directional accuracy
- 🎯 **Calibration milestones:** <10 = noise · 10-20 = trend · 20+ = attribution starts · 50 = v1.0
- 📜 **Logged to accuracy-scores.jsonl** with legend-level breakdown for trend tracking
- 🧬 Foundation for future weight-tilting: high-hit-rate legends earn more weight; low-hit-rate legends earn less (or removal)

**Why:** Previously, accuracy-tracker graded the OVERALL verdict only. Every legend was weighted equally regardless of track record. This left the single most-important Bridgewater-quality signal uncaptured: *which pillars actually predict well*? v0.3 fixes that.

---

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
