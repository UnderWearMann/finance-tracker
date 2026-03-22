#!/usr/bin/env python3
"""Weekly Digest Generator - Run via launchd on Sundays at 9am."""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_insights import generate_weekly_digest, save_weekly_digest
from src.forecaster import generate_forecast


def get_week_dates():
    """Get start (Monday) and end (Sunday) of the previous week."""
    today = date.today()
    days_since_sunday = (today.weekday() + 1) % 7
    week_end = today - timedelta(days=days_since_sunday)
    week_start = week_end - timedelta(days=6)
    return week_start, week_end


def main():
    print("=" * 50)
    print("Finance Tracker - Weekly Digest Generator")
    print("=" * 50)

    week_start, week_end = get_week_dates()
    print(f"\nGenerating digest for: {week_start} to {week_end}")

    print("\n1. Generating weekly digest...")
    digest = generate_weekly_digest(week_start, week_end)

    if "error" in digest:
        print(f"   Error: {digest['error']}")
    else:
        print(f"   Transactions analyzed: {digest.get('transaction_count', 0)}")
        print(f"   Summary: {digest.get('summary', 'N/A')[:100]}...")
        if save_weekly_digest(digest):
            print("   Digest saved to Google Sheets")
        else:
            print("   Warning: Failed to save digest")

    print("\n2. Generating 3-month forecast...")
    forecast = generate_forecast(months_ahead=3)

    if "error" in forecast:
        print(f"   Error: {forecast['error']}")
    elif forecast.get("need_more_data"):
        print(f"   {forecast.get('message')}")
    else:
        print(f"   Data months: {forecast.get('data_months', 0)}")
        for fm in forecast.get("forecast_months", []):
            print(f"   {fm['month']}: HK${fm['projected_total']:,.0f} ({fm['confidence']} confidence)")

    print("\n" + "=" * 50)
    print("Done!")


if __name__ == "__main__":
    main()
