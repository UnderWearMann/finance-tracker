"""
Google Sheets Integration
Syncs parsed transactions to Google Sheets
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict
import re
import json

from config import GOOGLE_SHEETS_CREDENTIALS_FILE, SPREADSHEET_NAME, CATEGORIES


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

    accounts.update('A1:K1', [[
        "Account ID", "Account Name", "Type", "Last Statement Date", "Currency",
        "Current Balance", "Institution Name", "Account Last Four",
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

    # Cash Transactions sheet
    try:
        cash_sheet = spreadsheet.worksheet("Cash Transactions")
    except gspread.WorksheetNotFound:
        cash_sheet = spreadsheet.add_worksheet("Cash Transactions", rows=500, cols=13)
        cash_sheet.update('A1:M1', [[
            "Cash TX ID", "Date", "Type", "Description", "Amount", "Currency",
            "Category", "Linked Withdrawal ID", "Withdrawal Date",
            "Withdrawal Amount", "Remaining Balance", "Source Account", "Created At"
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

    # Generate unique account ID from institution + account number
    account_last_four = statement_info.get("account_last_four", "") or statement_info.get("card_last_four", "")
    account_id = f"{institution}_{account_last_four}" if account_last_four else account_name

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
            account_id,
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

    # Auto-sync cash withdrawals to Cash Transactions sheet
    try:
        cash_count = sync_cash_withdrawals_to_cash_sheet(spreadsheet)
        if cash_count > 0:
            print(f"  Synced {cash_count} cash withdrawal(s) to Cash Transactions sheet")
    except Exception as e:
        print(f"  Warning: Could not sync cash withdrawals: {e}")

    return {
        "new_transactions": len(new_transactions),
        "duplicates_skipped": duplicates,
        "account": account_name,
        "period": period,
        "institution": institution,
        "account_type": statement_info.get("account_type", "unknown")
    }


def update_account_info(spreadsheet: gspread.Spreadsheet, account_name: str, statement_info: dict):
    """Update or add account information using Institution + Account Last 4 as unique key."""
    accounts_sheet = spreadsheet.worksheet("Accounts")
    existing_accounts = accounts_sheet.get_all_values()

    institution = statement_info.get("institution_name", "Unknown")
    account_last_four = statement_info.get("account_last_four", "") or statement_info.get("card_last_four", "")
    account_id = f"{institution}_{account_last_four}" if account_last_four else account_name

    # Generate friendly display name
    account_type = statement_info.get("account_type", "unknown")
    type_map = {
        "bank_checking": "Checking",
        "bank_savings": "Savings",
        "credit_card": "Credit Card",
        "investment": "Investment"
    }
    friendly_type = type_map.get(account_type, account_type)
    display_name = f"{institution} {friendly_type} ({account_last_four})" if account_last_four else account_name

    # Find if account exists by Account ID (column A)
    account_row = None
    for i, row in enumerate(existing_accounts[1:], start=2):
        if row and row[0] == account_id:
            account_row = i
            break

    account_data = [
        account_id,
        display_name,
        statement_info.get("account_type", "unknown"),
        statement_info.get("period_end", ""),
        statement_info.get("currency", "HKD"),
        statement_info.get("closing_balance", ""),
        institution,
        account_last_four,
        statement_info.get("card_scheme", ""),
        statement_info.get("credit_limit", ""),
        ""
    ]

    if account_row:
        accounts_sheet.update(f'A{account_row}:K{account_row}', [account_data])
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


def update_transaction_category(tx_id: str, new_category: str) -> bool:
    """Update the category of a single transaction."""
    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        transactions_sheet = spreadsheet.worksheet("Transactions")

        data = transactions_sheet.get_all_values()
        header = data[0]

        try:
            cat_col_idx = header.index("Category")
        except ValueError:
            cat_col_idx = 5

        for i, row in enumerate(data[1:], start=2):
            if row and row[0] == tx_id:
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

        try:
            cat_col_idx = header.index("Category")
        except ValueError:
            cat_col_idx = 5

        col_letter = chr(ord('A') + cat_col_idx)

        updates = []
        for i, row in enumerate(data[1:], start=2):
            if row and row[0] in tx_ids:
                updates.append({
                    'range': f'{col_letter}{i}',
                    'values': [[new_category]]
                })

        if updates:
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


def save_learning_rules_bulk(rules: List[dict]) -> bool:
    """
    Save multiple learning rules in one batch operation.

    Args:
        rules: List of {merchant_pattern, description_pattern, old_category, new_category}
    """
    if not rules:
        return False

    try:
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        rules_sheet = setup_learning_rules_sheet(spreadsheet)

        existing_rules = rules_sheet.get_all_records()
        now = datetime.now().isoformat()

        # Build lookup of existing rules
        existing_lookup = {}
        for i, rule in enumerate(existing_rules, start=2):
            key = (rule.get("Merchant Pattern", "").upper(), rule.get("Corrected Category", ""))
            existing_lookup[key] = {
                'row': i,
                'confidence': rule.get("Confidence", 0),
                'version': rule.get("Version", 1)
            }

        # Track version numbers per merchant
        version_by_merchant = {}
        for rule in existing_rules:
            merchant = rule.get("Merchant Pattern", "").upper()
            version = rule.get("Version", 1)
            version_by_merchant[merchant] = max(version_by_merchant.get(merchant, 0), version)

        # Prepare batch updates and new rows
        batch_updates = []
        new_rows = []

        for rule_data in rules:
            merchant_pattern = rule_data['merchant_pattern']
            key = (merchant_pattern.upper(), rule_data['new_category'])

            if key in existing_lookup:
                # Update existing rule - increment confidence
                existing = existing_lookup[key]
                row_num = existing['row']
                new_confidence = existing['confidence'] + 1
                batch_updates.append({
                    'range': f'E{row_num}',
                    'values': [[new_confidence]]
                })
                batch_updates.append({
                    'range': f'G{row_num}',
                    'values': [[now]]
                })
            else:
                # New rule
                merchant_upper = merchant_pattern.upper()
                version = version_by_merchant.get(merchant_upper, 0) + 1
                version_by_merchant[merchant_upper] = version

                new_rows.append([
                    rule_data['merchant_pattern'],
                    rule_data['description_pattern'],
                    rule_data['old_category'],
                    rule_data['new_category'],
                    1,  # Confidence
                    now,  # Created At
                    now,  # Last Used
                    version,  # Version
                    True  # Active
                ])

        # Execute batch operations
        if batch_updates:
            rules_sheet.batch_update(batch_updates)
        if new_rows:
            rules_sheet.append_rows(new_rows)

        return True
    except Exception as e:
        print(f"Error saving learning rules in bulk: {e}")
        return False


def get_conflicting_rules() -> List[Dict]:
    """Find rules with conflicting categories for the same merchant."""
    rules = get_learning_rules()
    by_merchant = {}
    for rule in rules:
        pattern = rule.get("Merchant Pattern", "").upper()
        if pattern:
            if pattern not in by_merchant:
                by_merchant[pattern] = []
            by_merchant[pattern].append(rule)
    conflicts = []
    for pattern, pattern_rules in by_merchant.items():
        categories = set(r.get("Corrected Category") for r in pattern_rules)
        if len(categories) > 1:
            conflicts.append({"pattern": pattern, "rules": pattern_rules, "categories": list(categories)})
    return conflicts


# ============================================
# Cash Transactions Functions
# ============================================

def sync_cash_withdrawals_to_cash_sheet(spreadsheet: gspread.Spreadsheet) -> int:
    """Auto-populate Cash Transactions with ATM withdrawals from Transactions sheet."""
    transactions_sheet = spreadsheet.worksheet("Transactions")
    cash_sheet = spreadsheet.worksheet("Cash Transactions")

    all_txs = transactions_sheet.get_all_records()
    withdrawals = [tx for tx in all_txs if tx.get("Category") == "Cash Withdrawal" and tx.get("Amount", 0) < 0]

    existing_cash = cash_sheet.get_all_records()
    existing_ids = set(row.get("Cash TX ID") for row in existing_cash if row.get("Type") == "Withdrawal")

    new_cash_txs = []
    for wtx in withdrawals:
        cash_tx_id = f"W_{wtx['ID']}"
        if cash_tx_id in existing_ids:
            continue

        withdrawal_amount = abs(wtx.get("Amount", 0))
        new_cash_txs.append([
            cash_tx_id,
            wtx.get("Date", ""),
            "Withdrawal",
            wtx.get("Description", ""),
            withdrawal_amount,
            wtx.get("Currency", "HKD"),
            "Cash Withdrawal",
            "",
            wtx.get("Date", ""),
            withdrawal_amount,
            withdrawal_amount,
            wtx.get("Account", ""),
            datetime.now().isoformat()
        ])

    if new_cash_txs:
        cash_sheet.append_rows(new_cash_txs)

    return len(new_cash_txs)


def get_cash_withdrawals_with_balance() -> list:
    """Get withdrawals with calculated remaining balance."""
    client = get_sheets_client()
    spreadsheet = get_or_create_spreadsheet(client)
    cash_sheet = spreadsheet.worksheet("Cash Transactions")

    records = cash_sheet.get_all_records()
    withdrawals = [r for r in records if r.get("Type") == "Withdrawal"]

    for w in withdrawals:
        w_id = w["Cash TX ID"]
        linked_spends = [r for r in records if r.get("Linked Withdrawal ID") == w_id]
        spent = sum(s.get("Amount", 0) for s in linked_spends)
        w["Actual Remaining"] = w.get("Withdrawal Amount", 0) - spent
        w["Fully Allocated"] = w["Actual Remaining"] <= 0

    return withdrawals


def get_cash_spends_for_withdrawal(withdrawal_id: str) -> list:
    """Get spends for a specific withdrawal."""
    client = get_sheets_client()
    spreadsheet = get_or_create_spreadsheet(client)
    cash_sheet = spreadsheet.worksheet("Cash Transactions")

    records = cash_sheet.get_all_records()
    return [r for r in records if r.get("Linked Withdrawal ID") == withdrawal_id]


def add_cash_spend(withdrawal_id: str, date: str, description: str, amount: float, category: str, currency: str = "HKD") -> dict:
    """Add manual cash spend linked to withdrawal."""
    import hashlib

    client = get_sheets_client()
    spreadsheet = get_or_create_spreadsheet(client)
    cash_sheet = spreadsheet.worksheet("Cash Transactions")

    cash_records = cash_sheet.get_all_records()
    withdrawal = next((r for r in cash_records if r.get("Cash TX ID") == withdrawal_id), None)

    if not withdrawal:
        return {"success": False, "message": "Withdrawal not found"}

    # Calculate current remaining
    linked_spends = [r for r in cash_records if r.get("Linked Withdrawal ID") == withdrawal_id]
    spent = sum(s.get("Amount", 0) for s in linked_spends)
    current_remaining = withdrawal.get("Withdrawal Amount", 0) - spent

    if amount > current_remaining:
        return {"success": False, "message": f"Insufficient cash. Remaining: ${current_remaining:,.2f}", "remaining_balance": current_remaining}

    spend_id = f"S_{hashlib.md5(f'{date}{description}{amount}'.encode()).hexdigest()[:8]}"

    cash_sheet.append_row([
        spend_id, date, "Spend", description, amount, currency, category,
        withdrawal_id, withdrawal.get("Withdrawal Date", ""),
        withdrawal.get("Withdrawal Amount", 0), 0,
        withdrawal.get("Source Account", ""), datetime.now().isoformat()
    ])

    return {"success": True, "remaining_balance": current_remaining - amount, "message": f"Added. Remaining: ${current_remaining - amount:,.2f}"}


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
