#!/usr/bin/env python3
"""
accuracy-tracker — scores royal-rumble predictions against reality.

Reads:
  royal-rumble/data/predictions.json    → single-ticker rumbles
  royal-rumble/data/comparisons.json    → pair verdicts (.compare output)
  royal-rumble/data/strategy-meetings.json → thematic plans

Pulls current prices via price-desk.
Computes hit rates, pair-relative spreads, time-weighted accuracy.
Logs scores to data/accuracy-scores.jsonl for trend tracking.

Usage:
  python3 accuracy.py                  → menu
  python3 accuracy.py summary          → high-level dashboard
  python3 accuracy.py rumbles          → score every single-ticker rumble
  python3 accuracy.py pairs            → score every .compare verdict
  python3 accuracy.py legends          → per-legend hit-rate attribution (v0.3+)
  python3 accuracy.py review [Nd]      → Dalio weekly reflection ritual (v0.4+)
  python3 accuracy.py TICKER           → score one ticker's rumble history
  python3 accuracy.py log [N]          → score log
"""
import sys
import json
import subprocess
from datetime import datetime, timezone, date
from pathlib import Path

HOME = Path.home()
PREDICTIONS = HOME / "Desktop/CLAUDE CODE/royal-rumble/data/predictions.json"
COMPARISONS = HOME / "Desktop/CLAUDE CODE/royal-rumble/data/comparisons.json"
PRICE_SCRIPT = HOME / ".claude/skills/price-desk/scripts/price.py"
SCORE_LOG = Path(__file__).parent.parent / "data" / "accuracy-scores.jsonl"
SCORE_LOG.parent.mkdir(parents=True, exist_ok=True)

D = "$"

MENU = """
📊 ACCURACY TRACKER — Performance Attribution Analyst
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What do you want to score?

1. 📈 Summary dashboard
     .accuracy summary            (cross-all aggregate)

2. 🎯 Score every single-ticker rumble
     .accuracy rumbles            (predictions.json)

3. ⚔️  Score every compare verdict
     .accuracy pairs              (comparisons.json — pair-relative)

4. 🏛️ Per-legend hit-rate attribution  ✨ v0.3+
     .accuracy legends            (which pillars actually predict well)

5. 🔬 Weekly reflection ritual (Dalio pain+reflection)  ✨ v0.4+
     .accuracy review             (last 7d, structured pain-pass-progress)
     .accuracy review 14d         (last 14d / 30d / 90d)

6. 🔍 Score one ticker's history
     .accuracy TICKER             (all rumbles on that ticker)

7. 📜 Show score log
     .accuracy log [N]            (last N scoring runs)

8. ❓ This menu
     .accuracy                    (no args = this)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pulls live prices via price-desk. Compares to predicted verdicts.
Reports hit rate, relative spreads, legend attribution.
"""


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def get_live_price(ticker):
    """Call price-desk; return current price float or None."""
    try:
        result = subprocess.run(
            ["python3", str(PRICE_SCRIPT), ticker],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(result.stdout)
        if isinstance(data, list) and data and data[0].get("status") == "OK":
            return data[0].get("price")
    except Exception:
        pass
    return None


def days_between(iso_date_str):
    """Days from iso_date_str to today."""
    try:
        d = datetime.fromisoformat(iso_date_str.replace("Z", "+00:00")).date()
    except Exception:
        try:
            d = date.fromisoformat(iso_date_str[:10])
        except Exception:
            return None
    today = date.today()
    return (today - d).days


def verdict_to_expected_direction(verdict):
    """Convert verdict to expected direction."""
    v = verdict.upper()
    if "STRONG BUY" in v:
        return 1.0
    if "BUY" in v:
        return 0.5
    if "HOLD" in v:
        return 0.0
    if "STRONG SELL" in v:
        return -1.0
    if "SELL" in v:
        return -0.5
    return 0.0


def score_rumbles():
    """Score every single-ticker rumble."""
    data = load_json(PREDICTIONS, {"rumbles": []})
    rumbles = data.get("rumbles", [])

    if not rumbles:
        print("❌ No rumbles logged yet in predictions.json")
        return

    print(f"\n🎯 SCORING {len(rumbles)} SINGLE-TICKER RUMBLES\n")
    print(f'{"TICKER":<6} {"Date":>10} {"Days":>5} {"Entry":>8} {"Live":>8} {"Return%":>8} {"Verdict":>12} {"Expected":>9} {"Score":>8}')
    print("=" * 90)

    hits = 0
    total_scored = 0
    for r in rumbles:
        ticker = r.get("ticker", "?")
        entry_price = r.get("price")
        entry_date = r.get("date", "")
        verdict = r.get("verdict", "?")
        expected = verdict_to_expected_direction(verdict)

        live_price = get_live_price(ticker)
        days = days_between(entry_date)

        if live_price is None or entry_price is None or entry_price == 0:
            print(f'{ticker:<6} {entry_date:>10} {str(days) if days is not None else "?":>5}  (could not fetch live price)')
            continue

        actual_return_pct = (live_price - entry_price) / entry_price * 100
        total_scored += 1

        # Score: did direction align with verdict?
        if expected > 0 and actual_return_pct > 0:
            score = "HIT"
            hits += 1
        elif expected < 0 and actual_return_pct < 0:
            score = "HIT"
            hits += 1
        elif expected == 0:
            score = "N/A"
            total_scored -= 1  # HOLD is neither hit nor miss
        else:
            score = "MISS"

        print(f'{ticker:<6} {entry_date:>10} {str(days):>5} {D}{entry_price:>7.2f} {D}{live_price:>7.2f} {actual_return_pct:>+7.2f}% {verdict:>12} {expected:>+9.1f} {score:>8}')

    if total_scored > 0:
        hit_rate = hits / total_scored * 100
        print("=" * 90)
        print(f'\n📊 HIT RATE: {hits}/{total_scored} = {hit_rate:.1f}%')
        print(f'   (HOLD verdicts excluded from hit/miss count)')
    else:
        print("\n⚠️  No scorable rumbles (all were HOLD or too early)")

    # Log summary
    log_score({
        "type": "rumbles",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total": len(rumbles),
        "scored": total_scored,
        "hits": hits,
        "hit_rate_pct": round(hits / total_scored * 100, 2) if total_scored else None,
    })


def score_pairs():
    """Score every .compare verdict as pair-relative."""
    data = load_json(COMPARISONS, {"comparisons": []})
    comps = data.get("comparisons", [])

    if not comps:
        print("❌ No comparisons logged yet in comparisons.json")
        return

    print(f"\n⚔️  SCORING {len(comps)} PAIR-RELATIVE VERDICTS\n")
    print(f'{"Date":>10} {"Pair":>16} {"Winner":>8} {"A return":>10} {"B return":>10} {"Spread":>10} {"Score":>8}')
    print("=" * 80)

    hits = 0
    total = 0
    for c in comps:
        ticker_a = c.get("ticker_a", "?")
        ticker_b = c.get("ticker_b", "?")
        pair_date = c.get("date", "")
        winner = c.get("winner", "?")

        live_a = get_live_price(ticker_a)
        live_b = get_live_price(ticker_b)

        # Original prices at compare time — pull from predictions.json if available
        all_rumbles = load_json(PREDICTIONS, {"rumbles": []}).get("rumbles", [])
        rumble_a = next((r for r in all_rumbles if r.get("ticker") == ticker_a and r.get("date") == pair_date), None)
        rumble_b = next((r for r in all_rumbles if r.get("ticker") == ticker_b and r.get("date") == pair_date), None)
        entry_a = rumble_a.get("price") if rumble_a else None
        entry_b = rumble_b.get("price") if rumble_b else None

        if not all([live_a, live_b, entry_a, entry_b]):
            print(f'{pair_date:>10} {ticker_a + " vs " + ticker_b:>16}  (missing price data)')
            continue

        return_a = (live_a - entry_a) / entry_a * 100
        return_b = (live_b - entry_b) / entry_b * 100
        spread = return_a - return_b  # positive = A outperformed B

        # Scoring:
        if winner == ticker_a and spread > 0:
            score = "HIT"
            hits += 1
        elif winner == ticker_b and spread < 0:
            score = "HIT"
            hits += 1
        else:
            score = "MISS"
        total += 1

        pair = f"{ticker_a} vs {ticker_b}"
        print(f'{pair_date:>10} {pair:>16} {winner:>8} {return_a:>+8.2f}% {return_b:>+8.2f}% {spread:>+8.2f}% {score:>8}')

    if total > 0:
        hit_rate = hits / total * 100
        print("=" * 80)
        print(f'\n📊 PAIR HIT RATE: {hits}/{total} = {hit_rate:.1f}%')
        print(f'   (Pair-relative accuracy — cleaner signal than absolute)')
    else:
        print("\n⚠️  No scorable pairs")

    log_score({
        "type": "pairs",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total": len(comps),
        "scored": total,
        "hits": hits,
        "hit_rate_pct": round(hits / total * 100, 2) if total else None,
    })


def score_ticker(ticker):
    """Score all rumbles for a specific ticker."""
    data = load_json(PREDICTIONS, {"rumbles": []})
    rumbles = [r for r in data.get("rumbles", []) if r.get("ticker") == ticker.upper()]

    if not rumbles:
        print(f"❌ No rumbles on {ticker} in predictions.json")
        return

    print(f"\n🔍 {ticker.upper()} — {len(rumbles)} rumble(s) on record\n")
    print(f'{"Date":>10} {"Days":>5} {"Entry":>8} {"Live":>8} {"Return%":>8} {"Verdict":>12} {"Score":>8}')
    print("=" * 70)

    live_price = get_live_price(ticker)
    if live_price is None:
        print("❌ Could not fetch live price")
        return

    for r in rumbles:
        entry_price = r.get("price")
        entry_date = r.get("date", "")
        verdict = r.get("verdict", "?")
        days = days_between(entry_date)

        if not entry_price:
            continue
        return_pct = (live_price - entry_price) / entry_price * 100
        expected = verdict_to_expected_direction(verdict)

        if expected == 0:
            score = "N/A"
        elif (expected > 0 and return_pct > 0) or (expected < 0 and return_pct < 0):
            score = "HIT"
        else:
            score = "MISS"

        print(f'{entry_date:>10} {str(days):>5} {D}{entry_price:>7.2f} {D}{live_price:>7.2f} {return_pct:>+7.2f}% {verdict:>12} {score:>8}')


def score_legends():
    """Per-legend hit-rate attribution (v0.3+).

    For each rumble in predictions.json, extract each voting legend's stance
    value and score it against actual forward return. Aggregate per legend
    to reveal which pillars actually predict well — the Dalio "believability-
    weighted" foundation. Advisory legends included separately (stance string
    only — no numeric value — so hit/miss derived from BULL/BEAR/NEUTRAL text).

    A stance is a HIT if its directional sign matches the actual return sign.
    HOLD/NEUTRAL stances excluded from hit/miss (no directional call).
    """
    data = load_json(PREDICTIONS, {"rumbles": []})
    rumbles = data.get("rumbles", [])

    if not rumbles:
        print("❌ No rumbles logged yet in predictions.json")
        return

    print(f"\n🏛️  PER-LEGEND ATTRIBUTION — {len(rumbles)} rumble(s) on record\n")

    # Aggregate: {legend: {"hits": N, "total": N, "total_return_pct": float}}
    voting_stats = {}
    advisory_stats = {}

    scored_rumbles = 0
    for r in rumbles:
        ticker = r.get("ticker", "?")
        entry_price = r.get("price")
        entry_date = r.get("date", "")

        if not entry_price or entry_price == 0:
            continue

        live_price = get_live_price(ticker)
        if live_price is None:
            continue

        actual_return_pct = (live_price - entry_price) / entry_price * 100
        actual_direction = 1 if actual_return_pct > 0 else (-1 if actual_return_pct < 0 else 0)
        scored_rumbles += 1

        # Score each voting legend
        for legend, info in r.get("voting_stances", {}).items():
            value = info.get("value", 0)
            if legend not in voting_stats:
                voting_stats[legend] = {"hits": 0, "misses": 0, "neutrals": 0, "total_return_when_bullish": 0.0, "bullish_count": 0}
            stats = voting_stats[legend]
            stance_direction = 1 if value > 0 else (-1 if value < 0 else 0)
            if stance_direction == 0:
                stats["neutrals"] += 1
            elif stance_direction == actual_direction:
                stats["hits"] += 1
            else:
                stats["misses"] += 1
            # Track: when this legend was bullish, what was avg return?
            if stance_direction > 0:
                stats["total_return_when_bullish"] += actual_return_pct
                stats["bullish_count"] += 1

        # Score each advisory legend (stance string only)
        for legend, info in r.get("advisory_stances", {}).items():
            stance = info.get("stance", "").upper()
            if legend not in advisory_stats:
                advisory_stats[legend] = {"hits": 0, "misses": 0, "neutrals": 0}
            stats = advisory_stats[legend]
            # Parse stance string to direction
            if "BULL" in stance or "BUY" in stance or "LONG" in stance:
                stance_direction = 1
            elif "BEAR" in stance or "SELL" in stance or "SHORT" in stance:
                stance_direction = -1
            else:
                stance_direction = 0
            if stance_direction == 0:
                stats["neutrals"] += 1
            elif stance_direction == actual_direction:
                stats["hits"] += 1
            else:
                stats["misses"] += 1

    if scored_rumbles == 0:
        print("⚠️  No scorable rumbles (could not fetch live prices)")
        return

    # Render voting legends table
    print(f"Scored against live prices for {scored_rumbles} rumble(s)")
    print()
    print("🗳️  VOTING LEGENDS (weighted in championship score)")
    print("=" * 82)
    print(f'{"Legend":<18} {"Hits":>5} {"Misses":>7} {"Neutral":>8} {"Scored":>7} {"Hit Rate":>10} {"Avg Ret Bull":>13}')
    print("-" * 82)

    # Sort by hit rate descending
    def rate(s):
        scored = s["hits"] + s["misses"]
        return (s["hits"] / scored) if scored else -1

    for legend in sorted(voting_stats.keys(), key=lambda k: rate(voting_stats[k]), reverse=True):
        s = voting_stats[legend]
        scored = s["hits"] + s["misses"]
        hit_rate = f"{s['hits']/scored*100:.1f}%" if scored else "—"
        avg_bull = f"{s['total_return_when_bullish']/s['bullish_count']:+.2f}%" if s["bullish_count"] else "—"
        print(f'{legend:<18} {s["hits"]:>5} {s["misses"]:>7} {s["neutrals"]:>8} {scored:>7} {hit_rate:>10} {avg_bull:>13}')

    # Render advisory legends table
    if advisory_stats:
        print()
        print("📚 ADVISORY LEGENDS (no voting weight yet — accuracy-validated)")
        print("=" * 60)
        print(f'{"Legend":<18} {"Hits":>5} {"Misses":>7} {"Neutral":>8} {"Hit Rate":>10}')
        print("-" * 60)
        for legend in sorted(advisory_stats.keys(), key=lambda k: rate(advisory_stats[k]), reverse=True):
            s = advisory_stats[legend]
            scored = s["hits"] + s["misses"]
            hit_rate = f"{s['hits']/scored*100:.1f}%" if scored else "—"
            print(f'{legend:<18} {s["hits"]:>5} {s["misses"]:>7} {s["neutrals"]:>8} {hit_rate:>10}')

    # Calibration note
    print()
    if scored_rumbles < 10:
        print(f"⚠️  Calibration: {scored_rumbles} rumbles scored — too few for reliable per-legend signal")
        print("   Reliable trend starts at 10 · legend-level attribution at 20 · v1.0 at 50")
    elif scored_rumbles < 20:
        print(f"📈 Calibration: {scored_rumbles} rumbles scored — first trend visible, noise still high")
    else:
        print(f"🎯 Calibration: {scored_rumbles} rumbles scored — legend attribution starting to mean something")

    print()
    print("💡 Use: legends with consistently high hit rates earn larger weight;")
    print("   legends with consistently low hit rates earn smaller weight (or removal).")
    print("   This is Dalio's 'believability-weighted decision making' — made explicit.")

    # Log to score trend
    log_score({
        "type": "legends",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "scored_rumbles": scored_rumbles,
        "voting": {k: {"hits": v["hits"], "misses": v["misses"], "neutrals": v["neutrals"]} for k, v in voting_stats.items()},
        "advisory": {k: {"hits": v["hits"], "misses": v["misses"], "neutrals": v["neutrals"]} for k, v in advisory_stats.items()},
    })


def score_review(window_days=7):
    """Dalio weekly reflection ritual (v0.4+).

    Generates a structured reflection report for rumbles in the last N days:
    - Hit/miss breakdown
    - Hypothesis-vs-judge divergence (self-scorekeeping)
    - Per-legend scorecard THIS WINDOW ONLY (not all-time)
    - Pattern observations auto-surfaced
    - Reflection prompt template for user to fill in
    - Persists to data/reflections.jsonl for compounding

    'Pain + reflection = progress' — Dalio.
    """
    data = load_json(PREDICTIONS, {"rumbles": []})
    rumbles = data.get("rumbles", [])

    if not rumbles:
        print("❌ No rumbles logged yet. Run .rumble TICKER first.")
        return

    # Filter by window
    window_rumbles = []
    for r in rumbles:
        d = days_between(r.get("date", ""))
        if d is not None and 0 <= d <= window_days:
            window_rumbles.append(r)

    now = datetime.now(timezone.utc)
    window_label = f"{window_days}d"
    print()
    print(f"🔬 REFLECTION RITUAL — {now.strftime('%Y-%m-%d')} (last {window_label})")
    print("━" * 65)
    print(f"Dalio's pain + reflection = progress. Review what happened. Learn.")
    print("━" * 65)
    print()

    if not window_rumbles:
        print(f"⚠️  No rumbles in the last {window_label}.")
        print(f"   Most recent rumble: {rumbles[-1].get('date', '?') if rumbles else 'none'}")
        print(f"   Consider widening with: .accuracy review 30d / 90d")
        return

    # ═══════════════════════════════════════════════
    # SECTION 1 — What happened
    # ═══════════════════════════════════════════════
    print(f"📊 WHAT HAPPENED — {len(window_rumbles)} rumble(s) this window\n")

    hits, misses, holds, unscored = 0, 0, 0, 0
    scored_lines = []
    for r in window_rumbles:
        ticker = r.get("ticker", "?")
        entry_price = r.get("price")
        verdict = r.get("verdict", "?")
        expected = verdict_to_expected_direction(verdict)
        live = get_live_price(ticker)
        days = days_between(r.get("date", ""))

        if not entry_price or live is None:
            unscored += 1
            scored_lines.append(f"   ⚪ {ticker:<6} {verdict:>12}  (price fetch failed)")
            continue

        ret_pct = (live - entry_price) / entry_price * 100
        if expected == 0:
            tag = "⚪ HOLD"
            holds += 1
        elif (expected > 0 and ret_pct > 0) or (expected < 0 and ret_pct < 0):
            tag = "✅ HIT"
            hits += 1
        else:
            tag = "❌ MISS"
            misses += 1
        scored_lines.append(f"   {tag} {ticker:<6} {verdict:>12}  {ret_pct:+7.2f}% over {days}d")

    for line in scored_lines:
        print(line)

    scored = hits + misses
    hit_rate = f"{hits/scored*100:.1f}%" if scored else "—"
    print()
    print(f"   Hits: {hits}  ·  Misses: {misses}  ·  Holds: {holds}  ·  Unscored: {unscored}")
    print(f"   Hit rate (excluding HOLD): {hit_rate}")
    print()

    # ═══════════════════════════════════════════════
    # SECTION 2 — Hypothesis vs Judge divergence
    # ═══════════════════════════════════════════════
    print("🎯 YOUR CALL vs THE JUDGE (self-scorekeeping — the honest mirror)")
    print()
    divergences = []
    for r in window_rumbles:
        hyp = r.get("user_hypothesis", {})
        hyp_dir = hyp.get("direction", "skip")
        hyp_conv = hyp.get("conviction", "skip")
        verdict = r.get("verdict", "?")
        ticker = r.get("ticker", "?")

        if hyp_dir in ("skip", None):
            continue  # user didn't pre-register

        # Map judge verdict to direction
        judge_dir = "BULL" if verdict_to_expected_direction(verdict) > 0 else ("BEAR" if verdict_to_expected_direction(verdict) < 0 else "NEUTRAL")

        aligned = (hyp_dir.upper() == judge_dir) or (hyp_dir == "NEUTRAL" and judge_dir == "NEUTRAL")
        div_tag = "🟢 ALIGNED" if aligned else "🔴 DIVERGED"
        divergences.append((ticker, hyp_dir, hyp_conv, verdict, judge_dir, aligned))
        print(f"   {div_tag}  {ticker:<6} you={hyp_dir:<7}/{hyp_conv:<4}  judge={verdict:<12}")

    if not divergences:
        print("   (No pre-registered hypotheses in this window — try not --skip next time)")
    else:
        aligned_count = sum(1 for d in divergences if d[5])
        print()
        print(f"   Aligned: {aligned_count}/{len(divergences)}  ·  Diverged: {len(divergences)-aligned_count}")
        print(f"   🧬 Divergence = training signal. If you diverged AND judge was right,")
        print(f"      what did the winning legend see that you missed?")
    print()

    # ═══════════════════════════════════════════════
    # SECTION 3 — This window's legend scorecard
    # ═══════════════════════════════════════════════
    print("🏛️  LEGEND SCORECARD (this window only)")
    print()
    voting_stats = {}
    for r in window_rumbles:
        ticker = r.get("ticker")
        entry = r.get("price")
        if not entry:
            continue
        live = get_live_price(ticker)
        if live is None:
            continue
        ret = (live - entry) / entry * 100
        actual_dir = 1 if ret > 0 else (-1 if ret < 0 else 0)
        for legend, info in r.get("voting_stances", {}).items():
            v = info.get("value", 0)
            if legend not in voting_stats:
                voting_stats[legend] = {"hits": 0, "misses": 0, "neutrals": 0}
            s = voting_stats[legend]
            stance_dir = 1 if v > 0 else (-1 if v < 0 else 0)
            if stance_dir == 0:
                s["neutrals"] += 1
            elif stance_dir == actual_dir:
                s["hits"] += 1
            else:
                s["misses"] += 1

    if voting_stats:
        def rate(s):
            scored = s["hits"] + s["misses"]
            return (s["hits"] / scored) if scored else -1
        top = sorted(voting_stats.items(), key=lambda kv: rate(kv[1]), reverse=True)[:3]
        bottom = sorted(voting_stats.items(), key=lambda kv: rate(kv[1]))[:3]
        print("   🥇 TOP 3 THIS WINDOW:")
        for legend, s in top:
            scored = s["hits"] + s["misses"]
            hr = f"{s['hits']/scored*100:.0f}%" if scored else "—"
            print(f"      {legend:<16} {s['hits']}H/{s['misses']}M/{s['neutrals']}N  → {hr}")
        print()
        print("   🥉 BOTTOM 3 THIS WINDOW (watch for structural bias):")
        for legend, s in bottom:
            scored = s["hits"] + s["misses"]
            hr = f"{s['hits']/scored*100:.0f}%" if scored else "—"
            print(f"      {legend:<16} {s['hits']}H/{s['misses']}M/{s['neutrals']}N  → {hr}")
    print()

    # ═══════════════════════════════════════════════
    # SECTION 4 — Auto-surfaced patterns
    # ═══════════════════════════════════════════════
    print("🔍 PATTERNS CLAUDE NOTICED (pain + reflection fuel)")
    print()
    patterns = []
    if misses > 0:
        patterns.append(f"❗ {misses} miss(es) this window — dig into WHY the judge was wrong")
    if len(divergences) >= 2 and sum(1 for d in divergences if not d[5]) >= 2:
        patterns.append("❗ Multiple divergences between your call and judge — your instinct may need calibration")
    if holds >= len(window_rumbles) / 2:
        patterns.append("⚠️  Half+ were HOLD verdicts — are you rumbling on conviction signals or randomly?")
    if unscored > 0:
        patterns.append(f"⚠️  {unscored} rumble(s) couldn't be scored (price fetch fail) — investigate")
    if hits == scored and scored >= 3:
        patterns.append("🏆 Perfect hit rate this window — BUT — check sample size before celebrating. 3/3 is noise-level.")
    if not patterns:
        patterns.append("  (Thin window — no pattern strong enough to flag.)")
    for p in patterns:
        print(f"   {p}")
    print()

    # ═══════════════════════════════════════════════
    # SECTION 5 — Reflection prompts (user fills in)
    # ═══════════════════════════════════════════════
    print("📝 REFLECTION PROMPTS (fill these in yourself — copy/paste below)")
    print("━" * 65)
    print("""
   1. What SURPRISED me this window? (unexpected outcome — win or loss)
      →

   2. Where did I DISAGREE with a legend in hindsight?
      → legend:
      → my view:

   3. What PATTERN is emerging across my last 5-10 rumbles?
      →

   4. What PAIN POINT deserves action? (bad sizing, slow exec, chase, FOMO)
      →

   5. What will I do DIFFERENTLY next week?
      →
""")
    print("━" * 65)

    # ═══════════════════════════════════════════════
    # SECTION 6 — Persist
    # ═══════════════════════════════════════════════
    reflections_log = Path(__file__).parent.parent / "data" / "reflections.jsonl"
    reflections_log.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "0.1",
        "run_at": now.isoformat(),
        "window_days": window_days,
        "rumbles_in_window": len(window_rumbles),
        "hits": hits,
        "misses": misses,
        "holds": holds,
        "unscored": unscored,
        "hit_rate_pct": round(hits/scored*100, 2) if scored else None,
        "divergences": len(divergences),
        "aligned": sum(1 for d in divergences if d[5]),
        "patterns_surfaced": len(patterns),
    }
    with reflections_log.open("a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"✅ Reflection metadata logged → {reflections_log.relative_to(Path.home())}")
    print(f"   (Your written reflection text is YOURS — paste into your journal,")
    print(f"    notepad, or append to this file manually. Machine tracks metadata only.)")
    print()
    print("🧬 Next review: ~7 days from now. Suggest a recurring Sunday morning slot.")
    print()


def summary():
    """Cross-all aggregate dashboard."""
    rumbles = load_json(PREDICTIONS, {"rumbles": []}).get("rumbles", [])
    comps = load_json(COMPARISONS, {"comparisons": []}).get("comparisons", [])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    print()
    print("📊 ACCURACY TRACKER — SUMMARY DASHBOARD")
    print(f"    Scored at: {now}")
    print("=" * 70)
    print(f"  Single-ticker rumbles logged:     {len(rumbles)}")
    print(f"  Pair-relative verdicts logged:    {len(comps)}")
    print()
    print("  (For detailed scoring, run:)")
    print("    .accuracy rumbles    → single-ticker hit rate")
    print("    .accuracy pairs      → pair-relative hit rate")
    print("    .accuracy TICKER     → one ticker's history")
    print()
    print("  📈 Progress toward v1.0 calibration: 50+ rumbles needed")
    print(f"  Current: {len(rumbles)}/50 ({len(rumbles)*2}%)")
    print("=" * 70)


def log_score(record):
    try:
        with SCORE_LOG.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


def show_log(n=10):
    if not SCORE_LOG.exists():
        print("No scoring runs yet.")
        return
    lines = SCORE_LOG.read_text().strip().split("\n")
    recent = lines[-n:] if len(lines) > n else lines
    print(f"📜 Last {len(recent)} scoring runs:\n")
    for line in recent:
        try:
            r = json.loads(line)
            ts = r.get("run_at", "—")[:19]
            typ = r.get("type", "?")
            hit_rate = r.get("hit_rate_pct", "—")
            scored = r.get("scored", "—")
            print(f"  {ts}  {typ:>10}  {scored} scored · {hit_rate}% hit rate")
        except Exception:
            continue


def main():
    args = sys.argv[1:]

    if not args:
        print(MENU)
        sys.exit(0)

    cmd = args[0].lower()

    if cmd == "summary":
        summary()
    elif cmd == "rumbles":
        score_rumbles()
    elif cmd == "pairs":
        score_pairs()
    elif cmd == "legends":
        score_legends()
    elif cmd == "review":
        # Optional second arg: window like "7d", "14d", "30d"
        window = 7
        if len(args) > 1:
            w = args[1].lower().rstrip("d")
            try:
                window = int(w)
            except ValueError:
                pass
        score_review(window_days=window)
    elif cmd == "log":
        n = 10
        if len(args) > 1:
            try:
                n = int(args[1])
            except ValueError:
                pass
        show_log(n)
    else:
        # Treat as ticker
        score_ticker(args[0])


if __name__ == "__main__":
    main()
