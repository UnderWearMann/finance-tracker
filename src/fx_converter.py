"""
FX Converter Module
Handles currency conversion to HKD using frankfurter.app API.
"""
import json
import requests
from datetime import date, datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path

COMMON_CURRENCIES = ["USD", "EUR", "GBP", "CNY", "JPY", "SGD", "AUD", "CAD"]
BASE_CURRENCY = "HKD"
STALE_WARNING_DAYS = 4
STALE_FLAG_DAYS = 8
FRANKFURTER_API = "https://api.frankfurter.app"


def get_cached_rates() -> Dict[str, Dict[str, float]]:
    """Get cached FX rates from Google Sheets."""
    try:
        from .sheets_sync import get_fx_rates_from_sheet
        return get_fx_rates_from_sheet()
    except Exception:
        return {}


def fetch_fx_rate_from_api(from_currency: str, target_date: date) -> Optional[float]:
    """Fetch FX rate from frankfurter.app API."""
    if from_currency == BASE_CURRENCY:
        return 1.0
    try:
        date_str = target_date.strftime("%Y-%m-%d")
        url = f"{FRANKFURTER_API}/{date_str}?from={from_currency}&to={BASE_CURRENCY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "rates" in data and BASE_CURRENCY in data["rates"]:
            return data["rates"][BASE_CURRENCY]
        return None
    except Exception as e:
        print(f"FX API error: {e}")
        return None


def get_fx_rate(from_currency: str, target_date: date) -> float:
    """Get FX rate to convert from_currency to HKD."""
    if from_currency == BASE_CURRENCY or from_currency == "HKD":
        return 1.0

    date_str = target_date.strftime("%Y-%m-%d")
    cached_rates = get_cached_rates()

    if date_str in cached_rates and from_currency in cached_rates[date_str]:
        return cached_rates[date_str][from_currency]

    rate = fetch_fx_rate_from_api(from_currency, target_date)
    if rate:
        try:
            from .sheets_sync import save_fx_rate
            save_fx_rate(target_date, from_currency, rate, "frankfurter.app")
        except Exception:
            pass
        return rate

    for days_back in range(1, STALE_FLAG_DAYS + 30):
        check_date = (target_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if check_date in cached_rates and from_currency in cached_rates[check_date]:
            return cached_rates[check_date][from_currency]

    return 1.0


def convert_to_hkd(amount: float, currency: str, target_date: date) -> Tuple[float, float]:
    """Convert amount from given currency to HKD."""
    fx_rate = get_fx_rate(currency, target_date)
    hkd_amount = round(amount * fx_rate, 2)
    return hkd_amount, fx_rate


def get_rate_staleness(from_currency: str, target_date: date) -> str:
    """Check if the rate for a currency is stale."""
    if from_currency == BASE_CURRENCY:
        return "fresh"
    cached_rates = get_cached_rates()
    date_str = target_date.strftime("%Y-%m-%d")
    if date_str in cached_rates and from_currency in cached_rates[date_str]:
        return "fresh"
    for days_back in range(1, STALE_FLAG_DAYS + 1):
        check_date = (target_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if check_date in cached_rates and from_currency in cached_rates[check_date]:
            if days_back <= 3:
                return "fresh"
            elif days_back <= STALE_WARNING_DAYS:
                return "warning"
            else:
                return "stale"
    return "stale"


def update_fx_cache():
    """Pre-fetch and cache FX rates for common currencies."""
    today = date.today()
    rates_fetched = {}
    for currency in COMMON_CURRENCIES:
        rate = fetch_fx_rate_from_api(currency, today)
        if rate:
            rates_fetched[currency] = rate
            try:
                from .sheets_sync import save_fx_rate
                save_fx_rate(today, currency, rate, "frankfurter.app")
            except Exception as e:
                print(f"Failed to cache {currency} rate: {e}")
    return rates_fetched
