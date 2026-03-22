"""Tests for FX converter module."""
import pytest
from datetime import date
from unittest.mock import patch, Mock


def test_get_fx_rate_from_cache(mock_sheets_client, sample_fx_rates):
    """Test fetching FX rate from cache."""
    from src.fx_converter import get_fx_rate

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
