#!/usr/bin/env python3
"""
Main script to process PDF statements.
Watches the statements folder and processes new PDFs.
"""
import sys
import shutil
import re
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import process_pdf
from src.sheets_sync import sync_parsed_data
from src.config import STATEMENTS_DIR, PROCESSED_DIR


def generate_smart_filename(parsed_data: dict, original_filename: str) -> str:
    """Generate smart filename: {Institution}_{AccountLast4}_{YYYY-MM}.pdf"""
    statement_info = parsed_data.get("statement_info", {})
    institution = statement_info.get("institution_name", "")
    account_last_four = statement_info.get("account_last_four", "") or statement_info.get("card_last_four", "")
    period_end = statement_info.get("period_end", "")

    if not all([institution, account_last_four, period_end]):
        return original_filename

    clean_institution = re.sub(r'[^a-zA-Z0-9]', '', institution)

    try:
        date_obj = datetime.strptime(period_end, "%Y-%m-%d")
        month_str = date_obj.strftime("%Y-%m")
    except:
        return original_filename

    return f"{clean_institution}_{account_last_four}_{month_str}.pdf"


def process_all_statements():
    """Process all PDF files in the statements folder."""
    pdf_files = list(STATEMENTS_DIR.glob("*.pdf")) + list(STATEMENTS_DIR.glob("*.PDF"))

    if not pdf_files:
        print("No PDF files found in statements folder.")
        return

    print(f"Found {len(pdf_files)} PDF file(s) to process\n")

    results = []
    for pdf_path in pdf_files:
        try:
            # Parse the PDF
            parsed_data = process_pdf(pdf_path)

            if "error" in parsed_data:
                print(f"  Skipping due to error: {parsed_data['error']}")
                continue

            # Sync to Google Sheets
            sync_result = sync_parsed_data(parsed_data)
            results.append(sync_result)

            print(f"  Synced: {sync_result['new_transactions']} new transactions")
            if sync_result['duplicates_skipped'] > 0:
                print(f"  Skipped {sync_result['duplicates_skipped']} duplicates")

            # Generate smart filename and move
            smart_name = generate_smart_filename(parsed_data, pdf_path.name)
            dest_path = PROCESSED_DIR / smart_name

            # Handle duplicates (if same file reprocessed)
            if dest_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                smart_name = f"{timestamp}_{smart_name}"
                dest_path = PROCESSED_DIR / smart_name

            shutil.move(str(pdf_path), str(dest_path))
            print(f"  → Renamed: {smart_name}\n")

        except Exception as e:
            print(f"  ERROR processing {pdf_path.name}: {e}\n")

    # Summary
    print("=" * 50)
    print("PROCESSING COMPLETE")
    print("=" * 50)
    total_new = sum(r['new_transactions'] for r in results)
    total_dupes = sum(r['duplicates_skipped'] for r in results)
    print(f"Total new transactions: {total_new}")
    print(f"Total duplicates skipped: {total_dupes}")
    print(f"Files processed: {len(results)}")


if __name__ == "__main__":
    process_all_statements()
