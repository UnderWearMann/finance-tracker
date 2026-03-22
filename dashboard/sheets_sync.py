"""
Google Sheets Integration
Syncs parsed transactions to Google Sheets
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from config import GOOGLE_SHEETS_CREDENTIALS_FILE, SPREADSHEET_NAME, DEFAULT_CATEGORIES


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
    except ImportError:
        pass  # Not running in Streamlit

    # Fall back to local credentials file
    if Path(GOOGLE_SHEETS_CREDENTIALS_FILE).exists():
        creds = Credentials.from_service_account_file(
            str(GOOGLE_SHEETS_CREDENTIALS_FILE),
            scopes=SCOPES
        )
        return gspread.authorize(creds)

    # If neither secrets nor file available, raise error
    raise FileNotFoundError(
        "No credentials found. Either set up Streamlit secrets or provide credentials.json"
    )


def get_or_create_spreadsheet(client: gspread.Client) -> gspread.Spreadsheet:
    """Get existing spreadsheet or create new one."""
    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        # Ensure structure exists for existing spreadsheets
        try:
            spreadsheet.worksheet("Transactions")
        except gspread.WorksheetNotFound:
            setup_spreadsheet_structure(spreadsheet)
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(SPREADSHEET_NAME)
        setup_spreadsheet_structure(spreadsheet)

    return spreadsheet


def setup_spreadsheet_structure(spreadsheet: gspread.Spreadsheet):
    """Set up initial spreadsheet structure with required sheets."""

    # Transactions sheet - with new columns for CC payment tracking
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
    category_data = [[cat, "", "", ""] for cat in DEFAULT_CATEGORIES]
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

    # Update account last statement date
    update_account_info(spreadsheet, account_name, statement_info)

    return {
        "new_transactions": len(new_transactions),
        "duplicates_skipped": duplicates,
        "account": account_name,
        "period": period
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
            return categories if categories else DEFAULT_CATEGORIES

        except gspread.WorksheetNotFound:
            return DEFAULT_CATEGORIES

    except Exception:
        return DEFAULT_CATEGORIES


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


def delete_category(name: str) -> bool:
    """Delete a category from the Categories sheet."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        categories_sheet = spreadsheet.worksheet("Categories")

        data = categories_sheet.get_all_values()

        # Find and delete the row
        for i, row in enumerate(data[1:], start=2):
            if row and row[0] == name:
                categories_sheet.delete_rows(i)
                return True

        return False

    except Exception:
        return False


def update_transaction_category(tx_id: str, new_category: str) -> bool:
    """Update the category of a single transaction."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        transactions_sheet = spreadsheet.worksheet("Transactions")

        data = transactions_sheet.get_all_values()
        header = data[0]

        # Find the category column index
        try:
            cat_col_idx = header.index("Category")
        except ValueError:
            cat_col_idx = 5  # Default position

        # Find the transaction row
        for i, row in enumerate(data[1:], start=2):
            if row and row[0] == tx_id:
                # Update category cell (column is 1-indexed in gspread)
                col_letter = chr(ord('A') + cat_col_idx)
                transactions_sheet.update(f'{col_letter}{i}', [[new_category]])
                return True

        return False

    except Exception:
        return False


def update_transaction_categories_bulk(tx_ids: List[str], new_category: str) -> bool:
    """Update the category of multiple transactions."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        transactions_sheet = spreadsheet.worksheet("Transactions")

        data = transactions_sheet.get_all_values()
        header = data[0]

        # Find the category column index
        try:
            cat_col_idx = header.index("Category")
        except ValueError:
            cat_col_idx = 5

        col_letter = chr(ord('A') + cat_col_idx)

        # Batch update - collect all updates
        updates = []
        for i, row in enumerate(data[1:], start=2):
            if row and row[0] in tx_ids:
                updates.append({
                    'range': f'{col_letter}{i}',
                    'values': [[new_category]]
                })

        if updates:
            # Use batch_update for efficiency
            transactions_sheet.batch_update(updates)
            return True

        return False

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
    import re

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
