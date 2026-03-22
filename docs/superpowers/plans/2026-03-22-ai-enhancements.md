# Finance Tracker AI Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 6 AI-powered features: ML categorization learning, OCR for scanned documents, weekly AI insights, 3-month forecasting, anomaly explanations, and multi-currency FX handling.

**Architecture:** Claude-centric approach using Claude API for all AI features. New modules in `src/` for each capability, Google Sheets for data storage, Streamlit dashboard for visualization.

**Tech Stack:** Python 3.11+, Claude API (anthropic), Google Sheets (gspread), Streamlit, Pillow/pillow-heif for images, frankfurter.app for FX rates.

**Spec:** `docs/superpowers/specs/2026-03-22-ai-enhancements-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|----------------|
| `src/fx_converter.py` | FX rate fetching, caching, currency conversion to HKD |
| `src/learning.py` | Capture corrections, build learning context, match rules |
| `src/ocr.py` | Image/scanned PDF detection and Claude Vision processing |
| `src/ai_insights.py` | Weekly digest generation, anomaly explanations |
| `src/forecaster.py` | 3-month spending projections |
| `scripts/weekly_digest.py` | Cron job entry point for weekly insights |
| `tests/__init__.py` | Test package init |
| `tests/test_fx_converter.py` | FX converter unit tests |
| `tests/test_learning.py` | Learning module unit tests |
| `tests/test_ocr.py` | OCR module unit tests |
| `tests/test_ai_insights.py` | AI insights unit tests |
| `tests/test_forecaster.py` | Forecaster unit tests |

### Modified Files

| File | Changes |
|------|---------|
| `requirements.txt` | Add Pillow, pillow-heif, requests |
| `src/sheets_sync.py` | Add Learning Rules, Insights, FX Rates sheets |
| `src/parser.py` | Integrate learning context, add vision support |
| `dashboard/app.py` | Learning capture, insights tab, forecasts, FX display |
| `dashboard/sheets_sync.py` | Mirror changes from src/sheets_sync.py |

---

## Phase 1: Foundation

### Task 1: Set Up Test Infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Create tests directory and init**

```bash
mkdir -p /Users/sudhanshu.mohanty/finance-tracker/tests
```

- [ ] **Step 2: Create tests/__init__.py**

```python
# tests/__init__.py
"""Finance Tracker test suite."""
```

- [ ] **Step 3: Create conftest.py with shared fixtures**

```python
# tests/conftest.py
"""Shared pytest fixtures for Finance Tracker tests."""
import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch


@pytest.fixture
def mock_sheets_client():
    """Mock Google Sheets client."""
    with patch('src.sheets_sync.get_sheets_client') as mock:
        yield mock


@pytest.fixture
def sample_transactions():
    """Sample transaction data for testing."""
    return [
        {
            "date": "2026-03-15",
            "description": "UBER EATS* ORDER",
            "amount": -125.00,
            "currency": "HKD",
            "category": "Transportation",
            "merchant": "Uber Eats"
        },
        {
            "date": "2026-03-16",
            "description": "NETFLIX.COM",
            "amount": -78.00,
            "currency": "HKD",
            "category": "Entertainment",
            "merchant": "Netflix"
        },
        {
            "date": "2026-03-17",
            "description": "SALARY DEPOSIT",
            "amount": 50000.00,
            "currency": "HKD",
            "category": "Income",
            "merchant": ""
        }
    ]


@pytest.fixture
def sample_fx_rates():
    """Sample FX rate data."""
    return {
        "USD": 7.82,
        "EUR": 8.45,
        "GBP": 9.85,
        "CNY": 1.08,
        "JPY": 0.052
    }
```

- [ ] **Step 4: Add test dependencies to requirements.txt**

Add to `requirements.txt`:
```
# Testing
pytest>=8.0.0
pytest-mock>=3.12.0

# New dependencies for AI enhancements
Pillow>=10.0.0
pillow-heif>=0.14.0
requests>=2.31.0
```

- [ ] **Step 5: Install dependencies**

Run: `pip install -r /Users/sudhanshu.mohanty/finance-tracker/requirements.txt`

- [ ] **Step 6: Verify pytest works**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/ -v`
Expected: "no tests ran" (empty test suite)

- [ ] **Step 7: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git init  # if not already a repo
git add tests/ requirements.txt
git commit -m "chore: set up test infrastructure"
```

---

### Task 2: FX Converter - Core Functions

**Files:**
- Create: `src/fx_converter.py`
- Create: `tests/test_fx_converter.py`

- [ ] **Step 1: Write failing test for get_fx_rate**

```python
# tests/test_fx_converter.py
"""Tests for FX converter module."""
import pytest
from datetime import date
from unittest.mock import patch, Mock


def test_get_fx_rate_from_cache(mock_sheets_client, sample_fx_rates):
    """Test fetching FX rate from cache."""
    from src.fx_converter import get_fx_rate

    # Mock cached rates
    with patch('src.fx_converter.get_cached_rates') as mock_cache:
        mock_cache.return_value = {
            "2026-03-22": sample_fx_rates
        }

        rate = get_fx_rate("USD", date(2026, 3, 22))
        assert rate == 7.82


def test_get_fx_rate_hkd_returns_one():
    """HKD to HKD should always return 1.0."""
    from src.fx_converter import get_fx_rate

    rate = get_fx_rate("HKD", date(2026, 3, 22))
    assert rate == 1.0


def test_convert_to_hkd():
    """Test currency conversion to HKD."""
    from src.fx_converter import convert_to_hkd

    with patch('src.fx_converter.get_fx_rate') as mock_rate:
        mock_rate.return_value = 7.82

        hkd_amount, fx_rate = convert_to_hkd(100.0, "USD", date(2026, 3, 22))
        assert hkd_amount == 782.0
        assert fx_rate == 7.82
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_fx_converter.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create fx_converter.py with core functions**

```python
# src/fx_converter.py
"""
FX Converter Module
Handles currency conversion to HKD using frankfurter.app API.
"""
import json
import requests
from datetime import date, datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path

# Common currencies to pre-fetch
COMMON_CURRENCIES = ["USD", "EUR", "GBP", "CNY", "JPY", "SGD", "AUD", "CAD"]
BASE_CURRENCY = "HKD"

# Stale rate thresholds (days)
STALE_WARNING_DAYS = 4
STALE_FLAG_DAYS = 8

# API endpoints
FRANKFURTER_API = "https://api.frankfurter.app"


def get_cached_rates() -> Dict[str, Dict[str, float]]:
    """
    Get cached FX rates from Google Sheets.
    Returns dict of {date_str: {currency: rate}}.
    """
    try:
        from .sheets_sync import get_fx_rates_from_sheet
        return get_fx_rates_from_sheet()
    except Exception:
        return {}


def fetch_fx_rate_from_api(from_currency: str, target_date: date) -> Optional[float]:
    """
    Fetch FX rate from frankfurter.app API.
    Returns rate to convert from_currency to HKD.
    """
    if from_currency == BASE_CURRENCY:
        return 1.0

    try:
        # frankfurter.app uses EUR as base, so we need to calculate
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
    """
    Get FX rate to convert from_currency to HKD.
    Checks cache first, then API, with stale rate handling.

    Returns:
        Exchange rate (multiply original amount by this to get HKD)
    """
    if from_currency == BASE_CURRENCY or from_currency == "HKD":
        return 1.0

    date_str = target_date.strftime("%Y-%m-%d")
    cached_rates = get_cached_rates()

    # Check cache for exact date
    if date_str in cached_rates and from_currency in cached_rates[date_str]:
        return cached_rates[date_str][from_currency]

    # Try to fetch from API
    rate = fetch_fx_rate_from_api(from_currency, target_date)
    if rate:
        # Cache the rate
        try:
            from .sheets_sync import save_fx_rate
            save_fx_rate(target_date, from_currency, rate, "frankfurter.app")
        except Exception:
            pass
        return rate

    # Fallback to most recent cached rate
    for days_back in range(1, STALE_FLAG_DAYS + 30):
        check_date = (target_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if check_date in cached_rates and from_currency in cached_rates[check_date]:
            return cached_rates[check_date][from_currency]

    # No rate found - return 1.0 as last resort (will be flagged)
    return 1.0


def convert_to_hkd(amount: float, currency: str, target_date: date) -> Tuple[float, float]:
    """
    Convert amount from given currency to HKD.

    Returns:
        Tuple of (hkd_amount, fx_rate_used)
    """
    fx_rate = get_fx_rate(currency, target_date)
    hkd_amount = round(amount * fx_rate, 2)
    return hkd_amount, fx_rate


def get_rate_staleness(from_currency: str, target_date: date) -> str:
    """
    Check if the rate for a currency is stale.

    Returns:
        "fresh", "warning", or "stale"
    """
    if from_currency == BASE_CURRENCY:
        return "fresh"

    cached_rates = get_cached_rates()
    date_str = target_date.strftime("%Y-%m-%d")

    # Find most recent rate date
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
    """
    Pre-fetch and cache FX rates for common currencies.
    Call this daily via cron.
    """
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_fx_converter.py -v`
Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add src/fx_converter.py tests/test_fx_converter.py
git commit -m "feat: add FX converter module with caching"
```

---

### Task 3: Sheets Sync - FX Rates Sheet

**Files:**
- Modify: `src/sheets_sync.py`
- Create: `tests/test_sheets_sync_fx.py`

- [ ] **Step 1: Write failing test for FX sheet functions**

```python
# tests/test_sheets_sync_fx.py
"""Tests for FX-related sheets_sync functions."""
import pytest
from datetime import date
from unittest.mock import patch, Mock, MagicMock


def test_get_fx_rates_from_sheet_empty():
    """Test getting FX rates when sheet is empty."""
    from src.sheets_sync import get_fx_rates_from_sheet

    with patch('src.sheets_sync.get_sheets_client') as mock_client:
        mock_spreadsheet = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.get_all_records.return_value = []
        mock_spreadsheet.worksheet.return_value = mock_sheet
        mock_client.return_value.open.return_value = mock_spreadsheet

        rates = get_fx_rates_from_sheet()
        assert rates == {}


def test_save_fx_rate():
    """Test saving an FX rate to the sheet."""
    from src.sheets_sync import save_fx_rate

    with patch('src.sheets_sync.get_sheets_client') as mock_client:
        mock_spreadsheet = MagicMock()
        mock_sheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_sheet
        mock_client.return_value.open.return_value = mock_spreadsheet

        result = save_fx_rate(date(2026, 3, 22), "USD", 7.82, "frankfurter.app")
        assert result is True
        mock_sheet.append_row.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_sheets_sync_fx.py -v`
Expected: FAIL with AttributeError (functions don't exist)

- [ ] **Step 3: Add FX sheet functions to sheets_sync.py**

Add to `src/sheets_sync.py` (after existing functions):

```python
# ============================================
# FX Rates Sheet Functions
# ============================================

def setup_fx_rates_sheet(spreadsheet: gspread.Spreadsheet):
    """Set up FX Rates sheet structure."""
    try:
        fx_sheet = spreadsheet.worksheet("FX Rates")
    except gspread.WorksheetNotFound:
        fx_sheet = spreadsheet.add_worksheet("FX Rates", rows=500, cols=5)
        fx_sheet.update('A1:D1', [["Date", "From Currency", "To HKD Rate", "Source"]])
    return fx_sheet


def get_fx_rates_from_sheet() -> dict:
    """
    Get all cached FX rates from the FX Rates sheet.
    Returns dict of {date_str: {currency: rate}}.
    """
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)

        try:
            fx_sheet = spreadsheet.worksheet("FX Rates")
        except gspread.WorksheetNotFound:
            return {}

        records = fx_sheet.get_all_records()

        rates_by_date = {}
        for record in records:
            date_str = str(record.get("Date", ""))
            currency = record.get("From Currency", "")
            rate = record.get("To HKD Rate", 0)

            if date_str and currency and rate:
                if date_str not in rates_by_date:
                    rates_by_date[date_str] = {}
                rates_by_date[date_str][currency] = float(rate)

        return rates_by_date
    except Exception as e:
        print(f"Error getting FX rates: {e}")
        return {}


def save_fx_rate(rate_date: 'date', from_currency: str, rate: float, source: str) -> bool:
    """Save an FX rate to the FX Rates sheet."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        fx_sheet = setup_fx_rates_sheet(spreadsheet)

        date_str = rate_date.strftime("%Y-%m-%d")
        fx_sheet.append_row([date_str, from_currency, rate, source])
        return True
    except Exception as e:
        print(f"Error saving FX rate: {e}")
        return False
```

- [ ] **Step 4: Add import for date type at top of sheets_sync.py**

Add to imports in `src/sheets_sync.py`:
```python
from datetime import date
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_sheets_sync_fx.py -v`
Expected: 2 tests PASSED

- [ ] **Step 6: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add src/sheets_sync.py tests/test_sheets_sync_fx.py
git commit -m "feat: add FX rates sheet support"
```

---

### Task 4: Learning Module - Core Functions

**Files:**
- Create: `src/learning.py`
- Create: `tests/test_learning.py`

- [ ] **Step 1: Write failing tests for learning module**

```python
# tests/test_learning.py
"""Tests for learning module."""
import pytest
from unittest.mock import patch, MagicMock


def test_capture_correction():
    """Test capturing a category correction."""
    from src.learning import capture_correction

    with patch('src.learning.save_learning_rule') as mock_save:
        mock_save.return_value = True

        result = capture_correction(
            merchant="UBER EATS* ORDER",
            description="Food delivery",
            old_category="Transportation",
            new_category="Dining & Restaurants"
        )
        assert result is True


def test_get_learning_context():
    """Test building learning context from rules."""
    from src.learning import get_learning_context

    mock_rules = [
        {
            "Merchant Pattern": "UBER EATS",
            "Corrected Category": "Dining & Restaurants",
            "Confidence": 5,
            "Active": True
        },
        {
            "Merchant Pattern": "NETFLIX",
            "Corrected Category": "Subscriptions",
            "Confidence": 3,
            "Active": True
        }
    ]

    with patch('src.learning.get_learning_rules') as mock_get:
        mock_get.return_value = mock_rules

        context = get_learning_context(limit=10)
        assert "UBER EATS" in context
        assert "Dining & Restaurants" in context
        assert "NETFLIX" in context


def test_match_learned_rules():
    """Test matching transaction to learned rules."""
    from src.learning import match_learned_rules

    mock_rules = [
        {
            "Merchant Pattern": "UBER EATS",
            "Corrected Category": "Dining & Restaurants",
            "Confidence": 5,
            "Active": True
        }
    ]

    with patch('src.learning.get_learning_rules') as mock_get:
        mock_get.return_value = mock_rules

        category = match_learned_rules("UBER EATS* ORDER #123", "Food delivery")
        assert category == "Dining & Restaurants"


def test_match_learned_rules_requires_confidence():
    """Rules with Confidence < 2 should not be applied."""
    from src.learning import match_learned_rules

    mock_rules = [
        {
            "Merchant Pattern": "UBER EATS",
            "Corrected Category": "Dining & Restaurants",
            "Confidence": 1,  # Too low
            "Active": True
        }
    ]

    with patch('src.learning.get_learning_rules') as mock_get:
        mock_get.return_value = mock_rules

        category = match_learned_rules("UBER EATS* ORDER", "Food")
        assert category is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_learning.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create learning.py module**

```python
# src/learning.py
"""
Learning Module
Captures user corrections and builds in-context learning for categorization.
"""
import re
from datetime import datetime
from typing import Optional, List, Dict


def get_learning_rules() -> List[Dict]:
    """Get all learning rules from Google Sheets."""
    try:
        from .sheets_sync import get_learning_rules_from_sheet
        return get_learning_rules_from_sheet()
    except Exception:
        return []


def save_learning_rule(
    merchant_pattern: str,
    description_pattern: str,
    old_category: str,
    new_category: str
) -> bool:
    """Save a learning rule to Google Sheets."""
    try:
        from .sheets_sync import save_learning_rule_to_sheet
        return save_learning_rule_to_sheet(
            merchant_pattern, description_pattern,
            old_category, new_category
        )
    except Exception as e:
        print(f"Error saving learning rule: {e}")
        return False


def capture_correction(
    merchant: str,
    description: str,
    old_category: str,
    new_category: str
) -> bool:
    """
    Capture a category correction for learning.

    Args:
        merchant: Merchant name from transaction
        description: Transaction description
        old_category: Category before correction
        new_category: Category after correction

    Returns:
        True if successfully saved
    """
    if old_category == new_category:
        return False

    # Clean merchant pattern (remove trailing order numbers, etc.)
    merchant_pattern = re.sub(r'[#*]\s*\d+.*$', '', merchant).strip()
    if not merchant_pattern:
        merchant_pattern = merchant[:20] if merchant else ""

    return save_learning_rule(
        merchant_pattern=merchant_pattern,
        description_pattern=description[:50] if description else "",
        old_category=old_category,
        new_category=new_category
    )


def get_learning_context(limit: int = 50) -> str:
    """
    Build prompt context from top learned corrections.

    Args:
        limit: Maximum number of rules to include

    Returns:
        Formatted string for injection into categorization prompt
    """
    rules = get_learning_rules()

    # Filter active rules with Confidence >= 2, sort by confidence
    active_rules = [
        r for r in rules
        if r.get("Active", True) and r.get("Confidence", 0) >= 2
    ]
    active_rules.sort(key=lambda x: x.get("Confidence", 0), reverse=True)
    active_rules = active_rules[:limit]

    if not active_rules:
        return ""

    lines = ["Based on past corrections, apply these learned rules:"]
    for rule in active_rules:
        merchant = rule.get("Merchant Pattern", "")
        category = rule.get("Corrected Category", "")
        if merchant and category:
            lines.append(f"- '{merchant}' should be categorized as '{category}'")

    return "\n".join(lines)


def match_learned_rules(merchant: str, description: str) -> Optional[str]:
    """
    Check if a transaction matches any learned rules.

    Args:
        merchant: Merchant name from transaction
        description: Transaction description

    Returns:
        Matched category or None
    """
    rules = get_learning_rules()

    # Filter active rules with Confidence >= 2
    active_rules = [
        r for r in rules
        if r.get("Active", True) and r.get("Confidence", 0) >= 2
    ]

    # Sort by confidence (highest first) and specificity
    active_rules.sort(key=lambda x: (x.get("Confidence", 0), len(x.get("Merchant Pattern", ""))), reverse=True)

    text_to_match = f"{merchant} {description}".upper()

    for rule in active_rules:
        pattern = rule.get("Merchant Pattern", "").upper()
        if pattern and pattern in text_to_match:
            return rule.get("Corrected Category")

    return None


def get_conflicting_rules() -> List[Dict]:
    """
    Find rules with conflicting categories for the same merchant.

    Returns:
        List of conflict groups
    """
    rules = get_learning_rules()

    # Group by merchant pattern
    by_merchant = {}
    for rule in rules:
        pattern = rule.get("Merchant Pattern", "").upper()
        if pattern:
            if pattern not in by_merchant:
                by_merchant[pattern] = []
            by_merchant[pattern].append(rule)

    # Find conflicts
    conflicts = []
    for pattern, pattern_rules in by_merchant.items():
        categories = set(r.get("Corrected Category") for r in pattern_rules)
        if len(categories) > 1:
            conflicts.append({
                "pattern": pattern,
                "rules": pattern_rules,
                "categories": list(categories)
            })

    return conflicts
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_learning.py -v`
Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add src/learning.py tests/test_learning.py
git commit -m "feat: add learning module for category corrections"
```

---

### Task 5: Sheets Sync - Learning Rules Sheet

**Files:**
- Modify: `src/sheets_sync.py`
- Create: `tests/test_sheets_sync_learning.py`

- [ ] **Step 1: Write failing tests for learning sheet functions**

```python
# tests/test_sheets_sync_learning.py
"""Tests for learning-related sheets_sync functions."""
import pytest
from unittest.mock import patch, MagicMock


def test_get_learning_rules_from_sheet_empty():
    """Test getting learning rules when sheet is empty."""
    from src.sheets_sync import get_learning_rules_from_sheet

    with patch('src.sheets_sync.get_sheets_client') as mock_client:
        mock_spreadsheet = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.get_all_records.return_value = []
        mock_spreadsheet.worksheet.return_value = mock_sheet
        mock_client.return_value.open.return_value = mock_spreadsheet

        rules = get_learning_rules_from_sheet()
        assert rules == []


def test_save_learning_rule_to_sheet_new():
    """Test saving a new learning rule."""
    from src.sheets_sync import save_learning_rule_to_sheet

    with patch('src.sheets_sync.get_sheets_client') as mock_client:
        mock_spreadsheet = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.get_all_records.return_value = []
        mock_spreadsheet.worksheet.return_value = mock_sheet
        mock_client.return_value.open.return_value = mock_spreadsheet

        result = save_learning_rule_to_sheet(
            "UBER EATS",
            "Food delivery",
            "Transportation",
            "Dining & Restaurants"
        )
        assert result is True
        mock_sheet.append_row.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_sheets_sync_learning.py -v`
Expected: FAIL with AttributeError

- [ ] **Step 3: Add learning sheet functions to sheets_sync.py**

Add to `src/sheets_sync.py`:

```python
# ============================================
# Learning Rules Sheet Functions
# ============================================

def setup_learning_rules_sheet(spreadsheet: gspread.Spreadsheet):
    """Set up Learning Rules sheet structure."""
    try:
        rules_sheet = spreadsheet.worksheet("Learning Rules")
    except gspread.WorksheetNotFound:
        rules_sheet = spreadsheet.add_worksheet("Learning Rules", rows=500, cols=10)
        rules_sheet.update('A1:I1', [[
            "Merchant Pattern", "Description Pattern", "Original Category",
            "Corrected Category", "Confidence", "Created At", "Last Used",
            "Version", "Active"
        ]])
    return rules_sheet


def get_learning_rules_from_sheet() -> list:
    """Get all learning rules from the Learning Rules sheet."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)

        try:
            rules_sheet = spreadsheet.worksheet("Learning Rules")
        except gspread.WorksheetNotFound:
            return []

        return rules_sheet.get_all_records()
    except Exception as e:
        print(f"Error getting learning rules: {e}")
        return []


def save_learning_rule_to_sheet(
    merchant_pattern: str,
    description_pattern: str,
    old_category: str,
    new_category: str
) -> bool:
    """
    Save a learning rule to the Learning Rules sheet.
    If rule exists for same pattern, update it; otherwise create new.
    """
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        rules_sheet = setup_learning_rules_sheet(spreadsheet)

        # Check if rule exists
        existing_rules = rules_sheet.get_all_records()
        row_to_update = None
        existing_version = 0
        existing_confidence = 0

        for i, rule in enumerate(existing_rules, start=2):
            if rule.get("Merchant Pattern", "").upper() == merchant_pattern.upper():
                if rule.get("Corrected Category") == new_category:
                    # Same correction, increment confidence
                    row_to_update = i
                    existing_confidence = rule.get("Confidence", 0)
                    existing_version = rule.get("Version", 1)
                    break
                else:
                    # Different correction - add new version
                    existing_version = max(existing_version, rule.get("Version", 1))

        now = datetime.now().isoformat()

        if row_to_update:
            # Update existing rule - increment confidence
            rules_sheet.update(f'E{row_to_update}', [[existing_confidence + 1]])
            rules_sheet.update(f'G{row_to_update}', [[now]])
            return True
        else:
            # Add new rule
            rules_sheet.append_row([
                merchant_pattern,
                description_pattern,
                old_category,
                new_category,
                1,  # Confidence starts at 1
                now,  # Created At
                now,  # Last Used
                existing_version + 1,  # Version
                True  # Active
            ])
            return True
    except Exception as e:
        print(f"Error saving learning rule: {e}")
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_sheets_sync_learning.py -v`
Expected: 2 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add src/sheets_sync.py tests/test_sheets_sync_learning.py
git commit -m "feat: add learning rules sheet support"
```

---

## Phase 2: OCR

### Task 6: OCR Module - Image Detection

**Files:**
- Create: `src/ocr.py`
- Create: `tests/test_ocr.py`

- [ ] **Step 1: Write failing tests for OCR detection**

```python
# tests/test_ocr.py
"""Tests for OCR module."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile


def test_is_scanned_pdf_text_pdf():
    """Text PDFs should return False."""
    from src.ocr import is_scanned_pdf

    # Create a mock text PDF
    with patch('src.ocr.extract_text_from_pdf') as mock_extract:
        mock_extract.return_value = "This is some text content from the PDF"

        result = is_scanned_pdf(Path("/fake/path.pdf"))
        assert result is False


def test_is_scanned_pdf_image_pdf():
    """Scanned PDFs (no text) should return True."""
    from src.ocr import is_scanned_pdf

    with patch('src.ocr.extract_text_from_pdf') as mock_extract:
        mock_extract.return_value = ""  # No extractable text

        result = is_scanned_pdf(Path("/fake/path.pdf"))
        assert result is True


def test_is_supported_image():
    """Test image format detection."""
    from src.ocr import is_supported_image

    assert is_supported_image(Path("receipt.jpg")) is True
    assert is_supported_image(Path("receipt.jpeg")) is True
    assert is_supported_image(Path("receipt.png")) is True
    assert is_supported_image(Path("receipt.heic")) is True
    assert is_supported_image(Path("document.pdf")) is False
    assert is_supported_image(Path("file.txt")) is False


def test_validate_image_size():
    """Test image size validation."""
    from src.ocr import validate_image_size

    # Test with mock file sizes
    with patch('pathlib.Path.stat') as mock_stat:
        mock_stat.return_value.st_size = 5 * 1024 * 1024  # 5MB
        result, error = validate_image_size(Path("/fake/image.jpg"))
        assert result is True

        mock_stat.return_value.st_size = 15 * 1024 * 1024  # 15MB
        result, error = validate_image_size(Path("/fake/image.jpg"))
        assert result is False
        assert "10MB" in error
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_ocr.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create ocr.py with detection functions**

```python
# src/ocr.py
"""
OCR Module
Handles scanned PDFs and receipt images using Claude Vision.
"""
import base64
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
import anthropic

# Supported image formats
SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def is_scanned_pdf(pdf_path: Path) -> bool:
    """
    Check if a PDF is scanned (image-based) vs text-based.

    Returns:
        True if PDF has no extractable text (likely scanned)
    """
    try:
        text = extract_text_from_pdf(pdf_path)
        # If very little text extracted, probably scanned
        return len(text.strip()) < 50
    except Exception:
        return True


def is_supported_image(file_path: Path) -> bool:
    """Check if file is a supported image format."""
    return file_path.suffix.lower() in SUPPORTED_IMAGES


def validate_image_size(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate image file size.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE:
            return False, f"File size {size / 1024 / 1024:.1f}MB exceeds maximum 10MB"
        return True, None
    except Exception as e:
        return False, str(e)


def convert_heic_to_jpeg(heic_path: Path) -> Path:
    """
    Convert HEIC image to JPEG for Claude API compatibility.

    Returns:
        Path to converted JPEG file
    """
    try:
        import pillow_heif
        from PIL import Image

        heif_file = pillow_heif.read_heif(heic_path)
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
        )

        jpeg_path = heic_path.with_suffix('.jpg')
        image.save(jpeg_path, "JPEG", quality=95)
        return jpeg_path
    except Exception as e:
        raise ValueError(f"Failed to convert HEIC: {e}")


def encode_image_base64(image_path: Path) -> str:
    """Encode image to base64 for Claude API."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: Path) -> str:
    """Get media type for image."""
    suffix = image_path.suffix.lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.heic': 'image/jpeg',  # After conversion
    }
    return media_types.get(suffix, 'image/jpeg')


def process_image_with_vision(image_path: Path, prompt: str) -> str:
    """
    Process an image using Claude Vision API.

    Args:
        image_path: Path to image file
        prompt: Extraction prompt for Claude

    Returns:
        Extracted text/data from image
    """
    client = anthropic.Anthropic()

    # Handle HEIC conversion
    if image_path.suffix.lower() == '.heic':
        image_path = convert_heic_to_jpeg(image_path)

    image_data = encode_image_base64(image_path)
    media_type = get_image_media_type(image_path)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    )

    return message.content[0].text


def process_receipt(image_path: Path) -> Dict:
    """
    Process a receipt photo and extract transaction data.

    Returns:
        Dict with merchant, date, total, currency, items, etc.
    """
    # Validate file
    valid, error = validate_image_size(image_path)
    if not valid:
        return {"error": "file_size", "message": error, "needs_manual_review": True}

    if not is_supported_image(image_path):
        return {"error": "unsupported_format", "message": f"Unsupported format: {image_path.suffix}"}

    prompt = """Analyze this receipt image and extract the transaction details.

Return a JSON object with:
{
    "merchant": "Store/restaurant name",
    "date": "YYYY-MM-DD format",
    "total": 123.45,
    "currency": "HKD/USD/etc",
    "items": [{"name": "Item name", "price": 10.00}],
    "confidence": "high/medium/low"
}

If you cannot read the receipt clearly, set confidence to "low" and extract what you can.
If the image is too blurry or dark to read, return:
{"error": "image_quality", "suggestion": "Retake photo with better lighting"}

Return ONLY the JSON, no explanation."""

    try:
        response = process_image_with_vision(image_path, prompt)

        # Parse JSON from response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        else:
            json_str = response

        result = json.loads(json_str.strip())
        result["source_file"] = str(image_path.name)
        return result
    except json.JSONDecodeError:
        return {
            "error": "parse_error",
            "raw_response": response,
            "needs_manual_review": True
        }
    except Exception as e:
        return {
            "error": "processing_error",
            "message": str(e),
            "needs_manual_review": True
        }


def process_scanned_pdf(pdf_path: Path) -> Dict:
    """
    Process a scanned PDF using Claude Vision.
    Converts PDF pages to images and extracts text.

    Returns:
        Dict with statement_info and transactions
    """
    from pypdf import PdfReader
    import io

    try:
        # For PDFs, we need to convert pages to images
        # This requires pdf2image library
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, first_page=1, last_page=5)  # Limit pages
        except ImportError:
            return {
                "error": "dependency_missing",
                "message": "pdf2image required for scanned PDFs. Install with: pip install pdf2image",
                "needs_manual_review": True
            }

        if not images:
            return {"error": "no_pages", "needs_manual_review": True}

        # Process first page with Claude Vision
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            images[0].save(tmp.name, 'JPEG')
            tmp_path = Path(tmp.name)

        # Use standard parser prompt for bank statements
        from .parser import parse_statement_with_ai
        from .config import CATEGORIES

        prompt = f"""This is a scanned bank statement image. Extract all transactions.

For each transaction, identify:
- date (YYYY-MM-DD format)
- description
- amount (positive for income, negative for expenses)
- currency
- category (choose from: {', '.join(CATEGORIES)})

Also identify:
- Account type (bank_checking, bank_savings, credit_card, investment)
- Institution name
- Statement period

Return as JSON:
{{
    "statement_info": {{
        "period_start": "YYYY-MM-DD",
        "period_end": "YYYY-MM-DD",
        "account_type": "...",
        "institution_name": "...",
        "currency": "HKD"
    }},
    "transactions": [
        {{"date": "...", "description": "...", "amount": -123.45, "currency": "HKD", "category": "..."}}
    ]
}}"""

        response = process_image_with_vision(tmp_path, prompt)

        # Clean up temp file
        tmp_path.unlink()

        # Parse response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        else:
            json_str = response

        result = json.loads(json_str.strip())
        result["source_file"] = str(pdf_path.name)
        result["ocr_processed"] = True
        return result

    except Exception as e:
        return {
            "error": "ocr_failed",
            "message": str(e),
            "needs_manual_review": True
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_ocr.py -v`
Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add src/ocr.py tests/test_ocr.py
git commit -m "feat: add OCR module with image detection"
```

---

### Task 7: Integrate OCR with Parser

**Files:**
- Modify: `src/parser.py`

- [ ] **Step 1: Read current parser.py to understand structure**

```bash
cat /Users/sudhanshu.mohanty/finance-tracker/src/parser.py
```

- [ ] **Step 2: Add OCR integration to parser.py**

Add to `src/parser.py` imports:
```python
from .ocr import is_scanned_pdf, process_scanned_pdf, process_receipt, is_supported_image
from .learning import get_learning_context, match_learned_rules
```

- [ ] **Step 3: Modify process_pdf function to handle scanned PDFs**

Update `process_pdf` function in `src/parser.py`:

```python
def process_pdf(pdf_path: Path, account_name: Optional[str] = None) -> dict:
    """
    Main entry point for processing a PDF statement.
    Handles both text-based and scanned PDFs.
    """
    if account_name is None:
        account_name = detect_account_from_filename(pdf_path.name)

    print(f"Processing: {pdf_path.name} (Account: {account_name})")

    # Check if it's a scanned PDF
    if is_scanned_pdf(pdf_path):
        print(f"  Detected scanned PDF, using OCR...")
        result = process_scanned_pdf(pdf_path)
    else:
        result = parse_statement_with_ai(pdf_path, account_name)

    # Apply learning rules if no error
    if "error" not in result and "transactions" in result:
        for tx in result["transactions"]:
            learned_cat = match_learned_rules(
                tx.get("merchant", ""),
                tx.get("description", "")
            )
            if learned_cat:
                tx["category"] = learned_cat
                tx["category_source"] = "learned"

    if "error" not in result:
        tx_count = len(result.get("transactions", []))
        statement_info = result.get("statement_info", {})
        account_type = statement_info.get("account_type", "unknown")
        institution = statement_info.get("institution_name", "Unknown")

        print(f"  Detected: {institution} ({account_type})")
        print(f"  Extracted {tx_count} transactions")

        cc_payments = [t for t in result.get("transactions", []) if t.get("is_cc_payment")]
        if cc_payments:
            print(f"  Found {len(cc_payments)} credit card payment(s)")
    else:
        print(f"  Error: {result['error']}")

    return result


def process_image(image_path: Path) -> dict:
    """
    Process a receipt image.
    """
    if not is_supported_image(image_path):
        return {"error": "unsupported_format", "message": f"Unsupported: {image_path.suffix}"}

    print(f"Processing receipt: {image_path.name}")
    result = process_receipt(image_path)

    if "error" not in result:
        print(f"  Merchant: {result.get('merchant', 'Unknown')}")
        print(f"  Total: {result.get('currency', '')} {result.get('total', 0)}")
    else:
        print(f"  Error: {result.get('error')}")

    return result
```

- [ ] **Step 4: Add learning context to parse_statement_with_ai**

Update the prompt in `parse_statement_with_ai` to include learning context:

```python
def parse_statement_with_ai(pdf_path: Path, account_name: str = "Unknown") -> dict:
    """
    Use Claude AI to parse a bank/credit card statement PDF.
    Returns structured transaction data with enhanced account detection.
    """
    client = anthropic.Anthropic()

    # Extract text from PDF
    statement_text = extract_text_from_pdf(pdf_path)

    # Get dynamic categories
    categories = get_categories_from_sheets()

    # Get learning context
    learning_context = get_learning_context(limit=50)

    prompt = f"""Analyze this bank/credit card statement and extract all transactions with detailed account information.

Statement from account: {account_name}

{learning_context}

Statement text:
{statement_text}

## Transaction Extraction
...  # rest of existing prompt
"""
    # ... rest of function remains the same
```

- [ ] **Step 5: Test OCR integration manually**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -c "from src.parser import process_pdf; print('Import OK')"`
Expected: "Import OK"

- [ ] **Step 6: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add src/parser.py
git commit -m "feat: integrate OCR and learning into parser"
```

---

## Phase 3: Insights

### Task 8: AI Insights Module

**Files:**
- Create: `src/ai_insights.py`
- Create: `tests/test_ai_insights.py`

- [ ] **Step 1: Write failing tests for AI insights**

```python
# tests/test_ai_insights.py
"""Tests for AI insights module."""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock


def test_generate_weekly_digest_structure(sample_transactions):
    """Test weekly digest returns correct structure."""
    from src.ai_insights import generate_weekly_digest

    with patch('src.ai_insights.get_transactions_for_period') as mock_txns:
        with patch('src.ai_insights.call_claude_for_digest') as mock_claude:
            mock_txns.return_value = sample_transactions
            mock_claude.return_value = {
                "summary": "Test summary",
                "highlights": ["highlight 1"],
                "recommendations": ["rec 1"],
                "unusual_patterns": []
            }

            result = generate_weekly_digest(
                date(2026, 3, 16),
                date(2026, 3, 22)
            )

            assert "summary" in result
            assert "highlights" in result
            assert "recommendations" in result


def test_explain_anomaly(sample_transactions):
    """Test anomaly explanation generation."""
    from src.ai_insights import explain_anomaly

    with patch('src.ai_insights.call_claude_for_explanation') as mock_claude:
        mock_claude.return_value = "Dining is 45% above average due to 2 restaurant visits."

        explanation = explain_anomaly(
            category="Dining & Restaurants",
            current=5000.0,
            average=3500.0,
            transactions=sample_transactions
        )

        assert "Dining" in explanation or len(explanation) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_ai_insights.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create ai_insights.py module**

```python
# src/ai_insights.py
"""
AI Insights Module
Generates weekly digests and anomaly explanations using Claude.
"""
import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import anthropic


def get_transactions_for_period(start_date: date, end_date: date) -> List[Dict]:
    """Get transactions for a date range from Google Sheets."""
    try:
        from .sheets_sync import get_all_transactions
        all_transactions = get_all_transactions()

        # Filter by date range
        filtered = []
        for tx in all_transactions:
            tx_date_str = tx.get("Date", "")
            try:
                tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d").date()
                if start_date <= tx_date <= end_date:
                    filtered.append(tx)
            except ValueError:
                continue

        return filtered
    except Exception as e:
        print(f"Error getting transactions: {e}")
        return []


def call_claude_for_digest(transactions: List[Dict], week_start: date, week_end: date) -> Dict:
    """Call Claude to generate weekly digest."""
    client = anthropic.Anthropic()

    # Summarize transactions for prompt
    total_spent = sum(abs(t.get("Amount", 0)) for t in transactions if t.get("Amount", 0) < 0)
    total_income = sum(t.get("Amount", 0) for t in transactions if t.get("Amount", 0) > 0)
    tx_count = len(transactions)

    # Group by category
    by_category = {}
    for tx in transactions:
        cat = tx.get("Category", "Other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tx)

    category_summary = "\n".join([
        f"- {cat}: HK${sum(abs(t.get('Amount', 0)) for t in txs if t.get('Amount', 0) < 0):,.0f} ({len(txs)} transactions)"
        for cat, txs in sorted(by_category.items(), key=lambda x: sum(abs(t.get('Amount', 0)) for t in x[1]), reverse=True)
    ])

    prompt = f"""Analyze this week's spending data and generate insights.

Week: {week_start} to {week_end}
Total Transactions: {tx_count}
Total Spent: HK${total_spent:,.0f}
Total Income: HK${total_income:,.0f}

Spending by Category:
{category_summary}

Generate a JSON response with:
{{
    "summary": "1-2 sentence overview of the week",
    "highlights": ["3-4 key observations"],
    "recommendations": ["1-2 actionable suggestions"],
    "unusual_patterns": ["any unusual activity detected"]
}}

Focus on actionable insights, not just repeating numbers. Be concise and helpful."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text

    # Parse JSON
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0]
    else:
        json_str = response_text

    return json.loads(json_str.strip())


def generate_weekly_digest(week_start: date, week_end: date) -> Dict:
    """
    Generate AI-powered weekly spending analysis.

    Args:
        week_start: Start of week (Monday)
        week_end: End of week (Sunday)

    Returns:
        Dict with summary, highlights, recommendations, unusual_patterns
    """
    transactions = get_transactions_for_period(week_start, week_end)

    if not transactions:
        return {
            "summary": f"No transactions found for week of {week_start}",
            "highlights": [],
            "recommendations": [],
            "unusual_patterns": [],
            "week_start": str(week_start),
            "week_end": str(week_end),
            "transaction_count": 0
        }

    try:
        digest = call_claude_for_digest(transactions, week_start, week_end)
        digest["week_start"] = str(week_start)
        digest["week_end"] = str(week_end)
        digest["transaction_count"] = len(transactions)
        digest["generated_at"] = datetime.now().isoformat()
        return digest
    except Exception as e:
        return {
            "error": str(e),
            "week_start": str(week_start),
            "week_end": str(week_end)
        }


def call_claude_for_explanation(category: str, current: float, average: float, transactions: List[Dict]) -> str:
    """Call Claude to explain an anomaly."""
    client = anthropic.Anthropic()

    # Get top transactions for this category
    cat_transactions = [t for t in transactions if t.get("Category") == category]
    cat_transactions.sort(key=lambda x: abs(x.get("Amount", 0)), reverse=True)
    top_txns = cat_transactions[:5]

    txn_details = "\n".join([
        f"- {t.get('Merchant', t.get('Description', 'Unknown'))}: HK${abs(t.get('Amount', 0)):,.0f}"
        for t in top_txns
    ])

    pct_change = ((current - average) / average) * 100 if average > 0 else 0

    prompt = f"""Explain this spending anomaly in 1-2 sentences:

Category: {category}
This month: HK${current:,.0f}
Average: HK${average:,.0f}
Change: {pct_change:+.0f}%

Top transactions:
{txn_details}

Explain WHY spending is {'higher' if pct_change > 0 else 'lower'} than usual.
Be specific about the transactions causing this. Keep it brief and insightful."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


def explain_anomaly(category: str, current: float, average: float, transactions: List[Dict]) -> str:
    """
    Generate natural language explanation for a spending spike.

    Args:
        category: Spending category
        current: Current period spending
        average: Historical average spending
        transactions: List of transactions in the period

    Returns:
        Human-readable explanation string
    """
    try:
        return call_claude_for_explanation(category, current, average, transactions)
    except Exception as e:
        pct_change = ((current - average) / average) * 100 if average > 0 else 0
        return f"{category} spending is {pct_change:+.0f}% compared to average."


def save_weekly_digest(digest: Dict) -> bool:
    """Save weekly digest to Google Sheets Insights sheet."""
    try:
        from .sheets_sync import save_insight_to_sheet
        return save_insight_to_sheet(digest)
    except Exception as e:
        print(f"Error saving digest: {e}")
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_ai_insights.py -v`
Expected: 2 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add src/ai_insights.py tests/test_ai_insights.py
git commit -m "feat: add AI insights module"
```

---

### Task 9: Forecaster Module

**Files:**
- Create: `src/forecaster.py`
- Create: `tests/test_forecaster.py`

- [ ] **Step 1: Write failing tests for forecaster**

```python
# tests/test_forecaster.py
"""Tests for forecaster module."""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock


def test_calculate_confidence_level():
    """Test confidence level calculation."""
    from src.forecaster import calculate_confidence_level

    # 6+ months, low variance = high
    assert calculate_confidence_level(months=8, variance=0.10) == "high"

    # 3-6 months, moderate variance = medium
    assert calculate_confidence_level(months=4, variance=0.25) == "medium"

    # < 3 months = low
    assert calculate_confidence_level(months=2, variance=0.10) == "low"

    # High variance = low
    assert calculate_confidence_level(months=12, variance=0.40) == "low"


def test_generate_forecast_insufficient_data():
    """Test forecast with insufficient data."""
    from src.forecaster import generate_forecast

    with patch('src.forecaster.get_historical_data') as mock_data:
        mock_data.return_value = []  # No data

        result = generate_forecast()
        assert "need_more_data" in result or result.get("forecast_months") == []


def test_generate_forecast_structure():
    """Test forecast returns correct structure."""
    from src.forecaster import generate_forecast

    mock_monthly = [
        {"month": "2026-01", "total": 40000, "by_category": {"Dining": 8000}},
        {"month": "2026-02", "total": 42000, "by_category": {"Dining": 8500}},
        {"month": "2026-03", "total": 38000, "by_category": {"Dining": 7500}},
    ]

    with patch('src.forecaster.get_historical_data') as mock_data:
        with patch('src.forecaster.call_claude_for_forecast') as mock_claude:
            mock_data.return_value = mock_monthly
            mock_claude.return_value = {
                "forecast_months": [
                    {"month": "2026-04", "projected_total": 41000, "confidence": "medium"}
                ],
                "trends": {"overall": "Stable spending"},
                "seasonality_notes": ""
            }

            result = generate_forecast(months_ahead=1)

            assert "forecast_months" in result
            assert "trends" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_forecaster.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create forecaster.py module**

```python
# src/forecaster.py
"""
Forecaster Module
Generates 3-month spending projections using historical patterns.
"""
import json
from datetime import date, datetime
from typing import Dict, List, Optional
import anthropic


def get_historical_data() -> List[Dict]:
    """
    Get monthly spending summaries from Google Sheets.

    Returns:
        List of {month: "YYYY-MM", total: float, by_category: {cat: amount}}
    """
    try:
        from .sheets_sync import get_all_transactions
        transactions = get_all_transactions()

        # Group by month
        by_month = {}
        for tx in transactions:
            tx_date_str = tx.get("Date", "")
            try:
                tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d")
                month_key = tx_date.strftime("%Y-%m")
            except ValueError:
                continue

            if month_key not in by_month:
                by_month[month_key] = {"total": 0, "by_category": {}}

            amount = abs(tx.get("Amount", 0)) if tx.get("Amount", 0) < 0 else 0
            category = tx.get("Category", "Other")

            by_month[month_key]["total"] += amount
            if category not in by_month[month_key]["by_category"]:
                by_month[month_key]["by_category"][category] = 0
            by_month[month_key]["by_category"][category] += amount

        # Convert to list sorted by month
        result = [
            {"month": month, **data}
            for month, data in sorted(by_month.items())
        ]

        return result
    except Exception as e:
        print(f"Error getting historical data: {e}")
        return []


def calculate_variance(monthly_totals: List[float]) -> float:
    """Calculate coefficient of variation (CV) for spending."""
    if len(monthly_totals) < 2:
        return 1.0

    mean = sum(monthly_totals) / len(monthly_totals)
    if mean == 0:
        return 1.0

    variance = sum((x - mean) ** 2 for x in monthly_totals) / len(monthly_totals)
    std_dev = variance ** 0.5

    return std_dev / mean


def calculate_confidence_level(months: int, variance: float) -> str:
    """
    Calculate forecast confidence level.

    Args:
        months: Number of months of historical data
        variance: Coefficient of variation

    Returns:
        "high", "medium", or "low"
    """
    if months < 3 or variance > 0.30:
        return "low"
    elif months >= 6 and variance < 0.15:
        return "high"
    else:
        return "medium"


def call_claude_for_forecast(historical: List[Dict], months_ahead: int) -> Dict:
    """Call Claude to generate spending forecast."""
    client = anthropic.Anthropic()

    # Prepare historical summary
    history_summary = "\n".join([
        f"- {m['month']}: HK${m['total']:,.0f} (top: {', '.join(f'{k}: ${v:,.0f}' for k, v in sorted(m['by_category'].items(), key=lambda x: x[1], reverse=True)[:3])})"
        for m in historical[-12:]  # Last 12 months
    ])

    # Get variance
    totals = [m["total"] for m in historical]
    variance = calculate_variance(totals)
    confidence = calculate_confidence_level(len(historical), variance)

    prompt = f"""Based on this spending history, forecast the next {months_ahead} months.

Historical monthly spending:
{history_summary}

Data points: {len(historical)} months
Variance: {variance:.1%}

Return a JSON forecast:
{{
    "forecast_months": [
        {{"month": "YYYY-MM", "projected_total": 45000, "confidence": "{confidence}", "by_category": {{"Dining": 8000, "Shopping": 12000}}}}
    ],
    "trends": {{
        "overall": "Brief trend description",
        "categories": {{"category": "trend for that category"}}
    }},
    "seasonality_notes": "Any seasonal patterns noted"
}}

Be conservative with projections. Note any uncertainty."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text

    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0]
    else:
        json_str = response_text

    return json.loads(json_str.strip())


def generate_forecast(months_ahead: int = 3) -> Dict:
    """
    Generate spending forecast using historical patterns.

    Args:
        months_ahead: Number of months to forecast (default 3)

    Returns:
        Dict with forecast_months, trends, confidence, seasonality_notes
    """
    historical = get_historical_data()

    if len(historical) < 1:
        return {
            "need_more_data": True,
            "message": "No historical data available. Process some statements first.",
            "forecast_months": []
        }

    if len(historical) < 3:
        # Simple average projection for sparse data
        avg_total = sum(m["total"] for m in historical) / len(historical)

        # Generate simple forecast
        forecast_months = []
        last_month = datetime.strptime(historical[-1]["month"], "%Y-%m")

        for i in range(1, months_ahead + 1):
            next_month = date(last_month.year, last_month.month, 1)
            # Handle month overflow
            month = last_month.month + i
            year = last_month.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1

            forecast_months.append({
                "month": f"{year}-{month:02d}",
                "projected_total": round(avg_total, 0),
                "confidence": "low",
                "by_category": {}
            })

        return {
            "forecast_months": forecast_months,
            "trends": {"overall": "Insufficient data for trend analysis"},
            "seasonality_notes": "",
            "data_months": len(historical),
            "generated_at": datetime.now().isoformat()
        }

    try:
        forecast = call_claude_for_forecast(historical, months_ahead)
        forecast["data_months"] = len(historical)
        forecast["generated_at"] = datetime.now().isoformat()
        return forecast
    except Exception as e:
        return {
            "error": str(e),
            "forecast_months": []
        }


def identify_trends(transactions: List[Dict]) -> Dict:
    """Identify spending trends by category."""
    historical = get_historical_data()

    if len(historical) < 3:
        return {"insufficient_data": True}

    trends = {}
    recent_3 = historical[-3:]

    # Calculate trend for each category
    all_categories = set()
    for m in historical:
        all_categories.update(m["by_category"].keys())

    for category in all_categories:
        amounts = [m["by_category"].get(category, 0) for m in recent_3]
        if amounts[0] == 0:
            continue

        change = (amounts[-1] - amounts[0]) / amounts[0] * 100
        if change > 10:
            trends[category] = f"Increasing (+{change:.0f}%)"
        elif change < -10:
            trends[category] = f"Decreasing ({change:.0f}%)"
        else:
            trends[category] = "Stable"

    return trends
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/test_forecaster.py -v`
Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add src/forecaster.py tests/test_forecaster.py
git commit -m "feat: add forecaster module for 3-month projections"
```

---

### Task 10: Weekly Digest Cron Script

**Files:**
- Create: `scripts/weekly_digest.py`
- Create: `com.finance-tracker.weekly-digest.plist`

- [ ] **Step 1: Create weekly digest script**

```python
# scripts/weekly_digest.py
#!/usr/bin/env python3
"""
Weekly Digest Generator
Run via launchd on Sundays at 9am to generate weekly spending insights.
"""
import sys
from pathlib import Path
from datetime import date, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_insights import generate_weekly_digest, save_weekly_digest
from src.forecaster import generate_forecast


def get_week_dates():
    """Get start (Monday) and end (Sunday) of the previous week."""
    today = date.today()
    # Find last Sunday (end of previous week)
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

    # Generate weekly digest
    print("\n1. Generating weekly digest...")
    digest = generate_weekly_digest(week_start, week_end)

    if "error" in digest:
        print(f"   Error: {digest['error']}")
    else:
        print(f"   Transactions analyzed: {digest.get('transaction_count', 0)}")
        print(f"   Summary: {digest.get('summary', 'N/A')[:100]}...")

        # Save digest
        if save_weekly_digest(digest):
            print("   Digest saved to Google Sheets")
        else:
            print("   Warning: Failed to save digest")

    # Generate forecast
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
```

- [ ] **Step 2: Make script executable**

```bash
chmod +x /Users/sudhanshu.mohanty/finance-tracker/scripts/weekly_digest.py
```

- [ ] **Step 3: Create launchd plist file**

```xml
<!-- /Users/sudhanshu.mohanty/finance-tracker/com.finance-tracker.weekly-digest.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.finance-tracker.weekly-digest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/sudhanshu.mohanty/finance-tracker/scripts/weekly_digest.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/sudhanshu.mohanty/finance-tracker/logs/digest.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/sudhanshu.mohanty/finance-tracker/logs/digest_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

- [ ] **Step 4: Test the script manually**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker && python scripts/weekly_digest.py
```

- [ ] **Step 5: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add scripts/weekly_digest.py com.finance-tracker.weekly-digest.plist
git commit -m "feat: add weekly digest cron job"
```

---

## Phase 4: Dashboard

### Task 11: Sheets Sync - Insights Sheet

**Files:**
- Modify: `src/sheets_sync.py`

- [ ] **Step 1: Add Insights sheet functions to sheets_sync.py**

Add to `src/sheets_sync.py`:

```python
# ============================================
# Insights Sheet Functions
# ============================================

def setup_insights_sheet(spreadsheet: gspread.Spreadsheet):
    """Set up Insights sheet structure."""
    try:
        insights_sheet = spreadsheet.worksheet("Insights")
    except gspread.WorksheetNotFound:
        insights_sheet = spreadsheet.add_worksheet("Insights", rows=200, cols=8)
        insights_sheet.update('A1:G1', [[
            "Week Start", "Week End", "Digest", "Top Insights",
            "Forecast 3M", "Anomalies", "Generated At"
        ]])
    return insights_sheet


def save_insight_to_sheet(digest: dict) -> bool:
    """Save a weekly digest to the Insights sheet."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        insights_sheet = setup_insights_sheet(spreadsheet)

        insights_sheet.append_row([
            digest.get("week_start", ""),
            digest.get("week_end", ""),
            digest.get("summary", ""),
            json.dumps(digest.get("highlights", [])),
            json.dumps(digest.get("forecast", {})),
            json.dumps(digest.get("unusual_patterns", [])),
            digest.get("generated_at", datetime.now().isoformat())
        ])
        return True
    except Exception as e:
        print(f"Error saving insight: {e}")
        return False


def get_latest_insights(limit: int = 5) -> list:
    """Get the most recent insights."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)

        try:
            insights_sheet = spreadsheet.worksheet("Insights")
        except gspread.WorksheetNotFound:
            return []

        records = insights_sheet.get_all_records()
        # Return most recent first
        return list(reversed(records[-limit:]))
    except Exception as e:
        print(f"Error getting insights: {e}")
        return []
```

- [ ] **Step 2: Add json import at top of sheets_sync.py if not present**

```python
import json
```

- [ ] **Step 3: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add src/sheets_sync.py
git commit -m "feat: add insights sheet support"
```

---

### Task 12: Dashboard - Learning Capture

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Read current app.py structure**

Understand the existing `render_transaction_editor` function.

- [ ] **Step 2: Add learning capture to category edits**

Add to imports in `dashboard/app.py`:
```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from learning import capture_correction
```

- [ ] **Step 3: Modify transaction editor to capture corrections**

Update the category change handling in `render_transaction_editor`:

```python
# After detecting category changes, add:
if changes:
    if st.button("Save Category Changes", type="primary"):
        success_count = 0
        for tx_id, new_category in changes:
            # Get original category
            original_cat = display_df[display_df['ID'] == tx_id]['Category'].iloc[0]
            merchant = display_df[display_df['ID'] == tx_id]['Merchant'].iloc[0]
            description = display_df[display_df['ID'] == tx_id]['Description'].iloc[0]

            if update_transaction_category(tx_id, new_category):
                success_count += 1
                # Capture for learning
                capture_correction(
                    merchant=merchant,
                    description=description,
                    old_category=original_cat,
                    new_category=new_category
                )
```

- [ ] **Step 4: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add dashboard/app.py
git commit -m "feat: capture category corrections for learning"
```

---

### Task 13: Dashboard - Insights Tab

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Add Insights tab to dashboard**

Add new function to `dashboard/app.py`:

```python
def render_insights_tab():
    """Render the Insights tab with weekly digests and forecasts."""
    st.markdown('<div class="section-header"><h2>AI Insights</h2></div>', unsafe_allow_html=True)

    # Get latest insights
    from sheets_sync import get_latest_insights
    insights = get_latest_insights(limit=4)

    if not insights:
        st.info("No insights generated yet. Weekly digests are generated every Sunday at 9am.")
        return

    # Show latest digest
    latest = insights[0]

    st.markdown(f"""
    <div class="insight-card">
        <div class="insight-title">Week of {latest.get('Week Start', '')} to {latest.get('Week End', '')}</div>
        <div class="insight-text">{latest.get('Digest', 'No summary available')}</div>
    </div>
    """, unsafe_allow_html=True)

    # Show highlights
    try:
        highlights = json.loads(latest.get('Top Insights', '[]'))
        if highlights:
            st.subheader("Highlights")
            for h in highlights:
                st.markdown(f"- {h}")
    except json.JSONDecodeError:
        pass

    # Show forecast
    from forecaster import generate_forecast
    with st.expander("3-Month Forecast", expanded=True):
        forecast = generate_forecast(months_ahead=3)

        if forecast.get("need_more_data"):
            st.warning(forecast.get("message", "Need more data"))
        elif "error" in forecast:
            st.error(forecast["error"])
        else:
            # Create forecast chart
            forecast_data = []
            for fm in forecast.get("forecast_months", []):
                forecast_data.append({
                    "Month": fm["month"],
                    "Projected": fm["projected_total"],
                    "Confidence": fm["confidence"]
                })

            if forecast_data:
                df_forecast = pd.DataFrame(forecast_data)
                fig = px.bar(
                    df_forecast, x="Month", y="Projected",
                    title="Spending Forecast",
                    color="Confidence",
                    color_discrete_map={"high": "#04d38c", "medium": "#f59e0b", "low": "#ef4444"}
                )
                st.plotly_chart(fig, use_container_width=True)

            # Show trends
            trends = forecast.get("trends", {})
            if trends.get("overall"):
                st.markdown(f"**Trend:** {trends['overall']}")
```

- [ ] **Step 2: Add tab to main function**

Update the main dashboard layout to include Insights tab:

```python
# In main(), after existing content:
tab1, tab2, tab3 = st.tabs(["Overview", "Transactions", "Insights"])

with tab1:
    # Existing overview content
    ...

with tab2:
    render_transaction_editor(filtered_df, categories)

with tab3:
    render_insights_tab()
```

- [ ] **Step 3: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add dashboard/app.py
git commit -m "feat: add Insights tab to dashboard"
```

---

### Task 14: Dashboard - Multi-Currency Display

**Files:**
- Modify: `dashboard/app.py`
- Modify: `dashboard/sheets_sync.py`

- [ ] **Step 1: Update transaction table to show currency columns**

Add to transaction table config:

```python
# In render_transaction_editor, update column config:
column_config={
    ...
    "Original Currency": st.column_config.TextColumn("Orig. Currency", width="small"),
    "Original Amount": st.column_config.NumberColumn("Orig. Amount", format="%.2f"),
    "HKD Amount": st.column_config.NumberColumn("HKD Amount", format="$%.2f"),
    ...
}
```

- [ ] **Step 2: Add currency filter to sidebar**

Add to sidebar filters:

```python
# Currency filter
if 'Original Currency' in df.columns:
    currencies = ['All'] + sorted(df['Original Currency'].dropna().unique().tolist())
    selected_currency = st.sidebar.selectbox("Currency", currencies)

    if selected_currency != 'All':
        mask &= df['Original Currency'] == selected_currency
```

- [ ] **Step 3: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add dashboard/app.py
git commit -m "feat: add multi-currency display to dashboard"
```

---

### Task 15: Dashboard - Anomaly Explanations

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Update anomaly alerts to include AI explanations**

Update `render_alerts` function:

```python
def render_alerts(staleness_alerts: list, anomalies: list, df: pd.DataFrame):
    """Render alert banners with AI explanations."""
    if not staleness_alerts and not anomalies:
        return

    st.markdown('<div class="section-header"><h2>Alerts</h2></div>', unsafe_allow_html=True)

    # Staleness alerts (unchanged)
    for alert in staleness_alerts:
        st.markdown(f"""
        <div class="alert-box alert-warning">
            <span class="alert-icon"></span>
            <div class="alert-content">
                <div class="alert-title">Statement Overdue</div>
                <div class="alert-text"><strong>{alert['account']}</strong> has no statement for {alert['days_old']} days</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Anomaly alerts with AI explanation
    for anomaly in anomalies[:3]:
        # Get explanation (with caching)
        cache_key = f"anomaly_{anomaly['name']}_{anomaly['current']}"
        if cache_key not in st.session_state:
            from ai_insights import explain_anomaly
            cat_transactions = df[df['Category'] == anomaly['name']].to_dict('records')
            st.session_state[cache_key] = explain_anomaly(
                anomaly['name'],
                anomaly['current'],
                anomaly['average'],
                cat_transactions
            )

        explanation = st.session_state[cache_key]

        st.markdown(f"""
        <div class="alert-box alert-info">
            <span class="alert-icon"></span>
            <div class="alert-content">
                <div class="alert-title">Spending Spike: {anomaly['name']}</div>
                <div class="alert-text">{explanation}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
```

- [ ] **Step 2: Update render_alerts call in main()**

```python
# Update the call to pass df
render_alerts(staleness_alerts, anomalies, filtered_df)
```

- [ ] **Step 3: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add dashboard/app.py
git commit -m "feat: add AI anomaly explanations to dashboard"
```

---

## Phase 5: Polish

### Task 16: Update Requirements

**Files:**
- Modify: `requirements.txt`
- Modify: `dashboard/requirements.txt`

- [ ] **Step 1: Update main requirements.txt**

Final `requirements.txt`:

```
# PDF Processing
anthropic>=0.39.0
pypdf>=4.0.0

# Google Sheets
gspread>=6.0.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0

# Dashboard
streamlit>=1.30.0
plotly>=5.18.0
pandas>=2.0.0

# Utilities
python-dateutil>=2.8.0

# Image Processing (AI Enhancements)
Pillow>=10.0.0
pillow-heif>=0.14.0

# HTTP Requests (FX API)
requests>=2.31.0

# Testing
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Update dashboard requirements.txt**

```
streamlit>=1.30.0
plotly>=5.18.0
pandas>=2.0.0
gspread>=6.0.0
google-auth>=2.0.0
anthropic>=0.39.0
requests>=2.31.0
```

- [ ] **Step 3: Commit**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
git add requirements.txt dashboard/requirements.txt
git commit -m "chore: update requirements for AI enhancements"
```

---

### Task 17: Run All Tests

**Files:**
- All test files

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker && python -m pytest tests/ -v
```

Expected: All tests PASSED

- [ ] **Step 2: Fix any failing tests**

If any tests fail, fix them before proceeding.

- [ ] **Step 3: Commit any fixes**

```bash
git add .
git commit -m "fix: test fixes"
```

---

### Task 18: Manual Integration Test

- [ ] **Step 1: Test FX conversion**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker
python -c "
from src.fx_converter import convert_to_hkd
from datetime import date
hkd, rate = convert_to_hkd(100, 'USD', date.today())
print(f'100 USD = {hkd} HKD (rate: {rate})')
"
```

- [ ] **Step 2: Test learning capture**

```bash
python -c "
from src.learning import capture_correction, get_learning_context
capture_correction('UBER EATS', 'Food delivery', 'Transportation', 'Dining')
print(get_learning_context())
"
```

- [ ] **Step 3: Test weekly digest (manual run)**

```bash
python /Users/sudhanshu.mohanty/finance-tracker/scripts/weekly_digest.py
```

- [ ] **Step 4: Test dashboard locally**

```bash
cd /Users/sudhanshu.mohanty/finance-tracker/dashboard
streamlit run app.py
```

Verify:
- Insights tab appears
- Category edits are captured
- Anomaly alerts show AI explanations

---

### Task 19: Final Commit

- [ ] **Step 1: Review all changes**

```bash
git status
git diff --stat HEAD~10
```

- [ ] **Step 2: Create final commit**

```bash
git add .
git commit -m "feat: complete AI enhancements implementation

- ML categorization learning from dashboard edits
- OCR support for scanned PDFs and receipt photos
- Weekly AI-generated spending digests
- 3-month spending forecasts
- AI-powered anomaly explanations
- Multi-currency FX handling (HKD base)

Closes: finance-tracker-ai-enhancement"
```

---

## Summary

This plan implements all 6 AI enhancements in 5 phases:

1. **Phase 1: Foundation** - FX converter, learning module, test infrastructure
2. **Phase 2: OCR** - Image detection, Claude Vision integration
3. **Phase 3: Insights** - AI insights, forecaster, weekly digest cron
4. **Phase 4: Dashboard** - Learning capture, insights tab, FX display, anomaly explanations
5. **Phase 5: Polish** - Requirements, testing, integration verification

Total: 19 tasks with ~100 steps

**Test commands:**
- Unit tests: `pytest tests/ -v`
- Dashboard: `streamlit run dashboard/app.py`
- Weekly digest: `python scripts/weekly_digest.py`
