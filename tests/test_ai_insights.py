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
            result = generate_weekly_digest(date(2026, 3, 16), date(2026, 3, 22))
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
