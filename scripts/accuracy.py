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

4. 🔍 Score one ticker's history
     .accuracy TICKER             (all rumbles on that ticker)

5. 📜 Show score log
     .accuracy log [N]            (last N scoring runs)

6. ❓ This menu
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
