"""
Learning Module
Captures user corrections and builds in-context learning for categorization.
"""
import re
from datetime import datetime
from typing import Optional, List, Dict


def get_learning_rules() -> List[Dict]:
    """Get all learning rules from Google Sheets."""
    try:
        from .sheets_sync import get_learning_rules_from_sheet
        return get_learning_rules_from_sheet()
    except Exception:
        return []


def save_learning_rule(merchant_pattern: str, description_pattern: str, old_category: str, new_category: str) -> bool:
    """Save a learning rule to Google Sheets."""
    try:
        from .sheets_sync import save_learning_rule_to_sheet
        return save_learning_rule_to_sheet(merchant_pattern, description_pattern, old_category, new_category)
    except Exception as e:
        print(f"Error saving learning rule: {e}")
        return False


def capture_correction(merchant: str, description: str, old_category: str, new_category: str) -> bool:
    """Capture a category correction for learning."""
    if old_category == new_category:
        return False
    merchant_pattern = re.sub(r'[#*]\s*\d+.*$', '', merchant).strip()
    if not merchant_pattern:
        merchant_pattern = merchant[:20] if merchant else ""
    return save_learning_rule(
        merchant_pattern=merchant_pattern,
        description_pattern=description[:50] if description else "",
        old_category=old_category,
        new_category=new_category
    )


def get_learning_context(limit: int = 50) -> str:
    """Build prompt context from top learned corrections."""
    rules = get_learning_rules()
    active_rules = [r for r in rules if r.get("Active", True) and r.get("Confidence", 0) >= 2]
    active_rules.sort(key=lambda x: x.get("Confidence", 0), reverse=True)
    active_rules = active_rules[:limit]
    if not active_rules:
        return ""
    lines = ["Based on past corrections, apply these learned rules:"]
    for rule in active_rules:
        merchant = rule.get("Merchant Pattern", "")
        category = rule.get("Corrected Category", "")
        if merchant and category:
            lines.append(f"- '{merchant}' should be categorized as '{category}'")
    return "\n".join(lines)


def match_learned_rules(merchant: str, description: str) -> Optional[str]:
    """Check if a transaction matches any learned rules."""
    rules = get_learning_rules()
    active_rules = [r for r in rules if r.get("Active", True) and r.get("Confidence", 0) >= 2]
    active_rules.sort(key=lambda x: (x.get("Confidence", 0), len(x.get("Merchant Pattern", ""))), reverse=True)
    text_to_match = f"{merchant} {description}".upper()
    for rule in active_rules:
        pattern = rule.get("Merchant Pattern", "").upper()
        if pattern and pattern in text_to_match:
            return rule.get("Corrected Category")
    return None


def capture_corrections_bulk(corrections: List[Dict]) -> bool:
    """
    Capture multiple category corrections at once.

    Args:
        corrections: List of dicts with merchant, description, old_category, new_category

    Returns:
        True if successful
    """
    if not corrections:
        return False

    # Process each correction to extract patterns
    rules_to_save = []
    for corr in corrections:
        if corr['old_category'] == corr['new_category']:
            continue

        merchant = corr['merchant']
        merchant_pattern = re.sub(r'[#*]\s*\d+.*$', '', merchant).strip()
        if not merchant_pattern:
            merchant_pattern = merchant[:20] if merchant else ""

        rules_to_save.append({
            'merchant_pattern': merchant_pattern,
            'description_pattern': corr['description'][:50] if corr['description'] else "",
            'old_category': corr['old_category'],
            'new_category': corr['new_category']
        })

    if not rules_to_save:
        return False

    try:
        from .sheets_sync import save_learning_rules_bulk
        return save_learning_rules_bulk(rules_to_save)
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
