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
        {"Merchant Pattern": "UBER EATS", "Corrected Category": "Dining & Restaurants", "Confidence": 5, "Active": True},
        {"Merchant Pattern": "NETFLIX", "Corrected Category": "Subscriptions", "Confidence": 3, "Active": True}
    ]

    with patch('src.learning.get_learning_rules') as mock_get:
        mock_get.return_value = mock_rules
        context = get_learning_context(limit=10)
        assert "UBER EATS" in context
        assert "Dining & Restaurants" in context


def test_match_learned_rules():
    """Test matching transaction to learned rules."""
    from src.learning import match_learned_rules

    mock_rules = [{"Merchant Pattern": "UBER EATS", "Corrected Category": "Dining & Restaurants", "Confidence": 5, "Active": True}]

    with patch('src.learning.get_learning_rules') as mock_get:
        mock_get.return_value = mock_rules
        category = match_learned_rules("UBER EATS* ORDER #123", "Food delivery")
        assert category == "Dining & Restaurants"


def test_match_learned_rules_requires_confidence():
    """Rules with Confidence < 2 should not be applied."""
    from src.learning import match_learned_rules

    mock_rules = [{"Merchant Pattern": "UBER EATS", "Corrected Category": "Dining & Restaurants", "Confidence": 1, "Active": True}]

    with patch('src.learning.get_learning_rules') as mock_get:
        mock_get.return_value = mock_rules
        category = match_learned_rules("UBER EATS* ORDER", "Food")
        assert category is None
