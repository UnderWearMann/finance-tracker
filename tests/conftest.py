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
