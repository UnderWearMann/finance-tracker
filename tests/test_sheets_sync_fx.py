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
