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

        result = save_learning_rule_to_sheet("UBER EATS", "Food delivery", "Transportation", "Dining & Restaurants")
        assert result is True
        mock_sheet.append_row.assert_called_once()
