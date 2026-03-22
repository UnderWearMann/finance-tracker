"""Tests for forecaster module."""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock


def test_calculate_confidence_level():
    """Test confidence level calculation."""
    from src.forecaster import calculate_confidence_level
    assert calculate_confidence_level(months=8, variance=0.10) == "high"
    assert calculate_confidence_level(months=4, variance=0.25) == "medium"
    assert calculate_confidence_level(months=2, variance=0.10) == "low"
    assert calculate_confidence_level(months=12, variance=0.40) == "low"


def test_generate_forecast_insufficient_data():
    """Test forecast with insufficient data."""
    from src.forecaster import generate_forecast
    with patch('src.forecaster.get_historical_data') as mock_data:
        mock_data.return_value = []
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
                "forecast_months": [{"month": "2026-04", "projected_total": 41000, "confidence": "medium"}],
                "trends": {"overall": "Stable spending"},
                "seasonality_notes": ""
            }
            result = generate_forecast(months_ahead=1)
            assert "forecast_months" in result
            assert "trends" in result
