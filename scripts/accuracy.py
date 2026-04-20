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

5. 🔍 Score one ticker's history
     .accuracy TICKER             (all rumbles on that ticker)

6. 📜 Show score log
     .accuracy log [N]            (last N scoring runs)

7. ❓ This menu
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
