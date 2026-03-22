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

# Institution name mappings for filename detection
INSTITUTION_MAPPINGS = {
    # Banks
    "hsbc": "HSBC",
    "hangseng": "Hang Seng Bank",
    "hang_seng": "Hang Seng Bank",
    "hangsen": "Hang Seng Bank",
    "boc": "Bank of China",
    "bankofchina": "Bank of China",
    "scb": "Standard Chartered",
    "standardchartered": "Standard Chartered",
    "sc_": "Standard Chartered",
    "dbs": "DBS Bank",
    "citi": "Citibank",
    "citibank": "Citibank",
    "bea": "Bank of East Asia",

    # Credit Cards
    "amex": "American Express",
    "americanexpress": "American Express",
    "visa": "Visa Card",
    "mastercard": "Mastercard",
    "mc_": "Mastercard",
    "unionpay": "UnionPay",

    # Investment
    "futu": "Futubull",
    "futubull": "Futubull",
    "interactive": "Interactive Brokers",
    "ibkr": "Interactive Brokers",
    "tiger": "Tiger Brokers",
    "schwab": "Charles Schwab",
}

# Card scheme detection keywords
CARD_SCHEME_KEYWORDS = {
    "visa": "Visa",
    "mastercard": "Mastercard",
    "master card": "Mastercard",
    "amex": "AMEX",
    "american express": "AMEX",
    "unionpay": "UnionPay",
    "union pay": "UnionPay",
    "discover": "Discover",
    "jcb": "JCB",
}

# Account type detection keywords
ACCOUNT_TYPE_KEYWORDS = {
    "credit_card": [
        "credit card", "card statement", "credit limit", "minimum payment",
        "payment due", "statement balance", "available credit"
    ],
    "bank_savings": [
        "savings account", "interest earned", "savings statement"
    ],
    "bank_checking": [
        "checking account", "current account", "cheque account"
    ],
    "investment": [
        "investment", "brokerage", "portfolio", "securities", "trading"
    ]
}

# Categories for transaction classification
CATEGORIES = [
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

# Credit card payment detection keywords
CC_PAYMENT_KEYWORDS = [
    "credit card",
    "card payment",
    "autopay",
    "bill payment",
    "cc payment",
    "card bill",
    "hsbc card",
    "amex",
    "sc card",
    "dbs card",
    "citi card",
]

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
