"""
Finance Tracker Configuration
"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path.home() / "finance-tracker"
STATEMENTS_DIR = BASE_DIR / "statements"
PROCESSED_DIR = BASE_DIR / "processed"

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_FILE = BASE_DIR / "credentials.json"
SPREADSHEET_NAME = "Finance Tracker"

# Design System - Modern Blue Theme
COLORS = {
    "primary": "#1a73e8",
    "success": "#04d38c",
    "danger": "#ef4444",
    "warning": "#f59e0b",
    "background": "#f8fafc",
    "card_bg": "#ffffff",
    "text_primary": "#1e293b",
    "text_secondary": "#64748b",
    "border": "#e2e8f0",
    "accent": "#8b5cf6",
}

# Category colors for consistent chart styling
CATEGORY_COLORS = {
    "Dining & Restaurants": "#ef4444",
    "Groceries": "#f59e0b",
    "Transportation": "#3b82f6",
    "Shopping": "#8b5cf6",
    "Entertainment": "#ec4899",
    "Utilities & Bills": "#6366f1",
    "Healthcare": "#14b8a6",
    "Travel": "#06b6d4",
    "Subscriptions": "#f97316",
    "Cash Withdrawal": "#78716c",
    "Transfer": "#94a3b8",
    "Income": "#22c55e",
    "Investment": "#0ea5e9",
    "Insurance": "#a855f7",
    "Education": "#f472b6",
    "Personal Care": "#fb923c",
    "Home": "#84cc16",
    "Fees & Charges": "#dc2626",
    "Credit Card Payment": "#475569",
    "Other": "#64748b",
}

# Default categories (fallback if sheets unavailable)
DEFAULT_CATEGORIES = [
    "Dining & Restaurants",
    "Groceries",
    "Transportation",
    "Shopping",
    "Entertainment",
    "Utilities & Bills",
    "Healthcare",
    "Travel",
    "Subscriptions",
    "Cash Withdrawal",
    "Transfer",
    "Income",
    "Investment",
    "Insurance",
    "Education",
    "Personal Care",
    "Home",
    "Fees & Charges",
    "Credit Card Payment",
    "Other"
]

# Keep CATEGORIES for backward compatibility (will be dynamically loaded)
CATEGORIES = DEFAULT_CATEGORIES.copy()

# Anomaly detection thresholds
ANOMALY_THRESHOLD_PERCENT = 40  # Flag if spending is 40% above 3-month average
STALENESS_DAYS = 30  # Warn if no statement for this many days

# Account configuration (user should update this)
ACCOUNTS = {
    "main_bank": {
        "name": "Main Bank",
        "type": "bank",
        "sub_accounts": ["checking", "savings"]
    },
    "credit_card_1": {
        "name": "Credit Card 1",
        "type": "credit_card"
    },
    "credit_card_2": {
        "name": "Credit Card 2",
        "type": "credit_card"
    },
    "credit_card_3": {
        "name": "Credit Card 3",
        "type": "credit_card"
    },
    "credit_card_4": {
        "name": "Credit Card 4",
        "type": "credit_card"
    },
    "futubull": {
        "name": "Futubull Investment",
        "type": "investment"
    }
}
