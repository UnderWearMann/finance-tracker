"""
PDF Statement Parser using Claude AI
Extracts transactions from bank and credit card statements
"""
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional
import anthropic
from pypdf import PdfReader

from .config import CATEGORIES, INSTITUTION_MAPPINGS
from .ocr import is_scanned_pdf, process_scanned_pdf, process_receipt, is_supported_image
from .learning import get_learning_context, match_learned_rules


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text content from PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def get_categories_from_sheets() -> list:
    """Try to get categories from Google Sheets, fall back to config."""
    try:
        from .sheets_sync import get_categories
        categories = get_categories()
        if categories:
            return categories
    except Exception:
        pass
    return CATEGORIES


def parse_statement_with_ai(pdf_path: Path, account_name: str = "Unknown") -> dict:
    """
    Use Claude AI to parse a bank/credit card statement PDF.
    Returns structured transaction data with enhanced account detection.
    """
    client = anthropic.Anthropic()

    # Extract text from PDF
    statement_text = extract_text_from_pdf(pdf_path)

    # Get dynamic categories
    categories = get_categories_from_sheets()

    # Get learning context
    learning_context = get_learning_context(limit=50)

    prompt = f"""Analyze this bank/credit card statement and extract all transactions with detailed account information.

Statement from account: {account_name}
{learning_context}
Statement text:
{statement_text}

## Transaction Extraction
Extract each transaction with the following fields:
- date: Transaction date in YYYY-MM-DD format
- description: Original transaction description
- amount: Transaction amount (positive for credits/income, negative for debits/expenses)
- currency: Currency code (e.g., HKD, USD)
- category: Best matching category from this list: {', '.join(categories)}
- merchant: Cleaned up merchant name if identifiable (e.g., "UBER *TRIP" -> "Uber")
- is_cc_payment: boolean - TRUE if this transaction appears to be a credit card payment/repayment
  (look for keywords like "credit card", "card payment", "autopay", masked card numbers like "XXXX1234")

## Account Detection
Carefully analyze the statement to determine:

1. account_type: Must be one of:
   - "bank_checking" - Checking/current account with regular transactions
   - "bank_savings" - Savings account with interest
   - "credit_card" - Credit card statement (look for credit limit, minimum payment, statement balance)
   - "investment" - Investment/brokerage account

2. institution_name: The bank or card issuer name. Common ones:
   - "HSBC", "Hang Seng Bank", "Standard Chartered", "Bank of China", "DBS", "Citibank"
   - "American Express", "AMEX", "Visa", "Mastercard"
   - Identify from letterhead, logo text, or statement header

3. For credit cards specifically:
   - card_last_four: Last 4 digits of card number if visible (e.g., "1234")
   - card_scheme: "Visa", "Mastercard", "AMEX", "UnionPay", or "Unknown"
   - credit_limit: Credit limit if shown
   - minimum_payment: Minimum payment due if shown
   - statement_balance: Total statement balance

4. For all statements:
   - opening_balance: Opening/previous balance
   - closing_balance: Closing/new balance
   - currency: Primary currency (HKD, USD, etc.)

## Credit Card Payment Detection
In bank statements, identify credit card payments by looking for:
- Keywords: "credit card", "card payment", "autopay", "bill payment"
- Card company names: "HSBC Card", "AMEX", "Standard Chartered CC"
- Masked card numbers in description: "XXXX1234", "****5678"
Mark these transactions with is_cc_payment: true and category: "Credit Card Payment"

Return as JSON with this structure:
{{
    "statement_info": {{
        "period_start": "YYYY-MM-DD",
        "period_end": "YYYY-MM-DD",
        "account_type": "bank_checking|bank_savings|credit_card|investment",
        "institution_name": "Bank/Card Name",
        "card_last_four": "1234" or null,
        "card_scheme": "Visa|Mastercard|AMEX|UnionPay" or null,
        "opening_balance": number or null,
        "closing_balance": number or null,
        "credit_limit": number or null,
        "minimum_payment": number or null,
        "currency": "HKD"
    }},
    "transactions": [
        {{
            "date": "YYYY-MM-DD",
            "description": "original description",
            "amount": -123.45,
            "currency": "HKD",
            "category": "Category Name",
            "merchant": "Clean Merchant Name",
            "is_cc_payment": false
        }}
    ]
}}

If you cannot determine a field, use null. Be thorough - extract ALL transactions."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Extract JSON from response
    response_text = message.content[0].text

    # Try to parse JSON from response
    try:
        # Look for JSON block in response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text

        result = json.loads(json_str.strip())
        result["source_file"] = str(pdf_path.name)
        result["account_name"] = account_name
        result["parsed_at"] = datetime.now().isoformat()

        # Apply category rules if available
        try:
            from .sheets_sync import apply_category_rules
            if "transactions" in result:
                result["transactions"] = apply_category_rules(result["transactions"])
        except Exception:
            pass

        return result

    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse AI response: {e}",
            "raw_response": response_text,
            "source_file": str(pdf_path.name)
        }


def process_image(image_path: Path) -> dict:
    """Process a receipt image."""
    if not is_supported_image(image_path):
        return {"error": "unsupported_format", "message": f"Unsupported: {image_path.suffix}"}
    print(f"Processing receipt: {image_path.name}")
    result = process_receipt(image_path)
    if "error" not in result:
        print(f"  Merchant: {result.get('merchant', 'Unknown')}")
        print(f"  Total: {result.get('currency', '')} {result.get('total', 0)}")
    else:
        print(f"  Error: {result.get('error')}")
    return result


def detect_account_from_filename(filename: str) -> str:
    """
    Try to detect account name from filename.
    Users can name files like: "hsbc_jan2024.pdf" or "amex_statement.pdf"
    """
    filename_lower = filename.lower()

    # Use institution mappings from config
    for keyword, name in INSTITUTION_MAPPINGS.items():
        if keyword in filename_lower:
            return name

    return "Unknown Account"


def process_pdf(pdf_path: Path, account_name: Optional[str] = None) -> dict:
    """
    Main entry point for processing a PDF statement.
    """
    if account_name is None:
        account_name = detect_account_from_filename(pdf_path.name)

    print(f"Processing: {pdf_path.name} (Account: {account_name})")

    # Check if it's a scanned PDF
    if is_scanned_pdf(pdf_path):
        print(f"  Detected scanned PDF, using OCR...")
        result = process_scanned_pdf(pdf_path)
    else:
        result = parse_statement_with_ai(pdf_path, account_name)

    # Apply learning rules if no error
    if "error" not in result and "transactions" in result:
        for tx in result["transactions"]:
            learned_cat = match_learned_rules(
                tx.get("merchant", ""),
                tx.get("description", "")
            )
            if learned_cat:
                tx["category"] = learned_cat
                tx["category_source"] = "learned"

    if "error" not in result:
        tx_count = len(result.get("transactions", []))
        statement_info = result.get("statement_info", {})
        account_type = statement_info.get("account_type", "unknown")
        institution = statement_info.get("institution_name", "Unknown")

        print(f"  Detected: {institution} ({account_type})")
        print(f"  Extracted {tx_count} transactions")

        # Report CC payments found
        cc_payments = [t for t in result.get("transactions", []) if t.get("is_cc_payment")]
        if cc_payments:
            print(f"  Found {len(cc_payments)} credit card payment(s)")
    else:
        print(f"  Error: {result['error']}")

    return result
