"""
Google Sheets Integration
Syncs parsed transactions to Google Sheets
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List
import re
import json

from .config import GOOGLE_SHEETS_CREDENTIALS_FILE, SPREADSHEET_NAME, CATEGORIES


# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def get_sheets_client():
    """Get authenticated Google Sheets client.

    Supports both local credentials.json and Streamlit Cloud secrets.
    """
    # Try Streamlit Cloud secrets first (for deployed dashboard)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
            return gspread.authorize(creds)
    except Exception:
        pass  # Not running in Streamlit or no secrets configured

    # Fall back to local credentials file
    creds = Credentials.from_service_account_file(
        str(GOOGLE_SHEETS_CREDENTIALS_FILE),
        scopes=SCOPES
    )
    return gspread.authorize(creds)


def get_or_create_spreadsheet(client: gspread.Client) -> gspread.Spreadsheet:
    """Get existing spreadsheet or create new one."""
    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        print(f"Found existing spreadsheet: {SPREADSHEET_NAME}")
        # Ensure structure exists for existing spreadsheets
        try:
            spreadsheet.worksheet("Transactions")
        except gspread.WorksheetNotFound:
            setup_spreadsheet_structure(spreadsheet)
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(SPREADSHEET_NAME)
        print(f"Created new spreadsheet: {SPREADSHEET_NAME}")
        setup_spreadsheet_structure(spreadsheet)

    return spreadsheet


def setup_spreadsheet_structure(spreadsheet: gspread.Spreadsheet):
    """Set up initial spreadsheet structure with required sheets."""

    # Transactions sheet - with new columns for CC payment tracking and institution
    try:
        transactions = spreadsheet.worksheet("Transactions")
    except gspread.WorksheetNotFound:
        transactions = spreadsheet.add_worksheet("Transactions", rows=1000, cols=20)

    transactions.update('A1:N1', [[
        "ID", "Date", "Description", "Amount", "Currency", "Category",
        "Merchant", "Account", "Statement Period", "Source File",
        "Parsed At", "Manual Override", "Is CC Payment", "Institution"
    ]])

    # Accounts sheet - with new columns for institution metadata
    try:
        accounts = spreadsheet.worksheet("Accounts")
    except gspread.WorksheetNotFound:
        accounts = spreadsheet.add_worksheet("Accounts", rows=50, cols=12)

    accounts.update('A1:J1', [[
        "Account Name", "Type", "Last Statement Date", "Currency",
        "Current Balance", "Institution Name", "Card Last Four",
        "Card Scheme", "Credit Limit", "Notes"
    ]])

    # Investments sheet
    try:
        investments = spreadsheet.worksheet("Investments")
    except gspread.WorksheetNotFound:
        investments = spreadsheet.add_worksheet("Investments", rows=200, cols=10)

    investments.update('A1:H1', [[
        "Date", "Account", "Symbol", "Action", "Quantity",
        "Price", "Total Value", "Currency"
    ]])

    # Categories sheet (for dynamic category management)
    try:
        categories = spreadsheet.worksheet("Categories")
    except gspread.WorksheetNotFound:
        categories = spreadsheet.add_worksheet("Categories", rows=50, cols=4)

    categories.update('A1:D1', [["Category", "Budget (Monthly)", "Color", "Notes"]])
    category_data = [[cat, "", "", ""] for cat in CATEGORIES]
    if category_data:
        categories.update(f'A2:D{len(category_data)+1}', category_data)

    # Category Rules sheet (for auto-categorization)
    try:
        rules = spreadsheet.worksheet("Category Rules")
    except gspread.WorksheetNotFound:
        rules = spreadsheet.add_worksheet("Category Rules", rows=100, cols=4)

    rules.update('A1:D1', [["Merchant Pattern", "Assigned Category", "Auto Apply", "Notes"]])

    # Monthly Summary sheet
    try:
        summary = spreadsheet.worksheet("Monthly Summary")
    except gspread.WorksheetNotFound:
        summary = spreadsheet.add_worksheet("Monthly Summary", rows=100, cols=20)

    summary.update('A1:D1', [[
        "Month", "Total Income", "Total Expenses", "Net"
    ]])

    # Delete default Sheet1 if it exists
    try:
        default_sheet = spreadsheet.worksheet("Sheet1")
        spreadsheet.del_worksheet(default_sheet)
    except gspread.WorksheetNotFound:
        pass

    print("Spreadsheet structure created successfully")


def generate_transaction_id(date: str, amount: float, description: str) -> str:
    """Generate a unique-ish ID for a transaction."""
    import hashlib
    data = f"{date}|{amount}|{description}"
    return hashlib.md5(data.encode()).hexdigest()[:12]


def sync_parsed_data(parsed_data: dict) -> dict:
    """
    Sync parsed statement data to Google Sheets.
    Returns summary of what was synced.
    """
    client = get_sheets_client()
    spreadsheet = get_or_create_spreadsheet(client)
    transactions_sheet = spreadsheet.worksheet("Transactions")

    # Get existing transaction IDs to avoid duplicates
    existing_data = transactions_sheet.get_all_values()
    existing_ids = set(row[0] for row in existing_data[1:] if row)

    # Prepare new transactions
    new_transactions = []
    duplicates = 0

    statement_info = parsed_data.get("statement_info", {})
    period = f"{statement_info.get('period_start', 'N/A')} to {statement_info.get('period_end', 'N/A')}"
    account_name = parsed_data.get("account_name", "Unknown")
    source_file = parsed_data.get("source_file", "Unknown")
    parsed_at = parsed_data.get("parsed_at", datetime.now().isoformat())
    institution = statement_info.get("institution_name", "")

    for tx in parsed_data.get("transactions", []):
        tx_id = generate_transaction_id(
            tx.get("date", ""),
            tx.get("amount", 0),
            tx.get("description", "")
        )

        if tx_id in existing_ids:
            duplicates += 1
            continue

        new_transactions.append([
            tx_id,
            tx.get("date", ""),
            tx.get("description", ""),
            tx.get("amount", 0),
            tx.get("currency", "HKD"),
            tx.get("category", "Other"),
            tx.get("merchant", ""),
            account_name,
            period,
            source_file,
            parsed_at,
            "",  # Manual Override column
            tx.get("is_cc_payment", False),  # CC Payment flag
            institution
        ])

    # Append new transactions
    if new_transactions:
        transactions_sheet.append_rows(new_transactions)

    # Update account last statement date with enhanced metadata
    update_account_info(spreadsheet, account_name, statement_info)

    return {
        "new_transactions": len(new_transactions),
        "duplicates_skipped": duplicates,
        "account": account_name,
        "period": period,
        "institution": institution,
        "account_type": statement_info.get("account_type", "unknown")
    }


def update_account_info(spreadsheet: gspread.Spreadsheet, account_name: str, statement_info: dict):
    """Update or add account information with enhanced metadata."""
    accounts_sheet = spreadsheet.worksheet("Accounts")
    existing_accounts = accounts_sheet.get_all_values()

    # Find if account exists
    account_row = None
    for i, row in enumerate(existing_accounts[1:], start=2):
        if row and row[0] == account_name:
            account_row = i
            break

    account_data = [
        account_name,
        statement_info.get("account_type", "unknown"),
        statement_info.get("period_end", ""),
        statement_info.get("currency", "HKD"),
        statement_info.get("closing_balance", ""),
        statement_info.get("institution_name", ""),
        statement_info.get("card_last_four", ""),
        statement_info.get("card_scheme", ""),
        statement_info.get("credit_limit", ""),
        ""
    ]

    if account_row:
        accounts_sheet.update(f'A{account_row}:J{account_row}', [account_data])
    else:
        accounts_sheet.append_row(account_data)


def get_all_transactions() -> list:
    """Retrieve all transactions from Google Sheets."""
    client = get_sheets_client()
    spreadsheet = get_or_create_spreadsheet(client)
    transactions_sheet = spreadsheet.worksheet("Transactions")

    data = transactions_sheet.get_all_records()
    return data


def get_account_info() -> list:
    """Retrieve all account information."""
    client = get_sheets_client()
    spreadsheet = get_or_create_spreadsheet(client)
    accounts_sheet = spreadsheet.worksheet("Accounts")

    data = accounts_sheet.get_all_records()
    return data


def get_spreadsheet_url() -> str:
    """Get the URL of the spreadsheet."""
    client = get_sheets_client()
    spreadsheet = get_or_create_spreadsheet(client)
    return spreadsheet.url


# ============================================
# Category Management Functions
# ============================================

def get_categories() -> List[str]:
    """Read categories from Google Sheets Categories sheet."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)

        try:
            categories_sheet = spreadsheet.worksheet("Categories")
            data = categories_sheet.get_all_values()

            # Skip header row, get category names from first column
            categories = [row[0] for row in data[1:] if row and row[0].strip()]
            return categories if categories else CATEGORIES

        except gspread.WorksheetNotFound:
            return CATEGORIES

    except Exception:
        return CATEGORIES


def add_category(name: str) -> bool:
    """Add a new category to the Categories sheet."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)

        try:
            categories_sheet = spreadsheet.worksheet("Categories")
        except gspread.WorksheetNotFound:
            categories_sheet = spreadsheet.add_worksheet("Categories", rows=50, cols=4)
            categories_sheet.update('A1:D1', [["Category", "Budget (Monthly)", "Color", "Notes"]])

        # Check if category already exists
        existing = get_categories()
        if name in existing:
            return False

        # Append new category
        categories_sheet.append_row([name, "", "", ""])
        return True

    except Exception:
        return False


# ============================================
# Category Rules Functions
# ============================================

def get_category_rules() -> List[dict]:
    """Get all category rules from the Category Rules sheet."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)

        try:
            rules_sheet = spreadsheet.worksheet("Category Rules")
            data = rules_sheet.get_all_records()
            return data
        except gspread.WorksheetNotFound:
            return []

    except Exception:
        return []


def add_category_rule(merchant_pattern: str, category: str, auto_apply: bool = True) -> bool:
    """Add a new category rule."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)

        try:
            rules_sheet = spreadsheet.worksheet("Category Rules")
        except gspread.WorksheetNotFound:
            rules_sheet = spreadsheet.add_worksheet("Category Rules", rows=100, cols=4)
            rules_sheet.update('A1:D1', [["Merchant Pattern", "Assigned Category", "Auto Apply", "Notes"]])

        rules_sheet.append_row([merchant_pattern, category, auto_apply, ""])
        return True

    except Exception:
        return False


def apply_category_rules(transactions: List[dict]) -> List[dict]:
    """Apply category rules to a list of transactions."""
    rules = get_category_rules()
    if not rules:
        return transactions

    # Build compiled regex patterns
    compiled_rules = []
    for rule in rules:
        if rule.get('Auto Apply'):
            try:
                pattern = re.compile(rule['Merchant Pattern'], re.IGNORECASE)
                compiled_rules.append((pattern, rule['Assigned Category']))
            except re.error:
                continue

    # Apply rules to transactions
    for tx in transactions:
        merchant = tx.get('merchant', '') or tx.get('description', '')
        for pattern, category in compiled_rules:
            if pattern.search(merchant):
                tx['category'] = category
                break

    return transactions


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
    """Get all cached FX rates. Returns {date_str: {currency: rate}}."""
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


def save_fx_rate(rate_date: date, from_currency: str, rate: float, source: str) -> bool:
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


def save_learning_rule_to_sheet(merchant_pattern: str, description_pattern: str, old_category: str, new_category: str) -> bool:
    """Save a learning rule. If exists for same pattern+category, increment confidence."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        rules_sheet = setup_learning_rules_sheet(spreadsheet)

        existing_rules = rules_sheet.get_all_records()
        row_to_update = None
        existing_version = 0
        existing_confidence = 0

        for i, rule in enumerate(existing_rules, start=2):
            if rule.get("Merchant Pattern", "").upper() == merchant_pattern.upper():
                if rule.get("Corrected Category") == new_category:
                    row_to_update = i
                    existing_confidence = rule.get("Confidence", 0)
                    existing_version = rule.get("Version", 1)
                    break
                else:
                    existing_version = max(existing_version, rule.get("Version", 1))

        now = datetime.now().isoformat()

        if row_to_update:
            rules_sheet.update(f'E{row_to_update}', [[existing_confidence + 1]])
            rules_sheet.update(f'G{row_to_update}', [[now]])
            return True
        else:
            rules_sheet.append_row([
                merchant_pattern, description_pattern, old_category, new_category,
                1, now, now, existing_version + 1, True
            ])
            return True
    except Exception as e:
        print(f"Error saving learning rule: {e}")
        return False


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
        return list(reversed(records[-limit:]))
    except Exception as e:
        print(f"Error getting insights: {e}")
        return []
