#!/usr/bin/env python3
"""
Generate shopping summary reports in text and JSON format.
Uses mock data - does not connect to Blinkit or send notifications.
"""

import json
import re
from decimal import Decimal
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from validate_config import validate_shopping_list, validate_settings
from validate_cart import load_mock_cart_data, validate_cart


COMPARISON_FILE = Path(__file__).parent.parent / "output" / "blinkit_comparison.txt"


def read_comparison_report() -> Optional[str]:
    """Read the blinkit comparison report if it exists."""
    if COMPARISON_FILE.exists():
        return COMPARISON_FILE.read_text(encoding="utf-8")
    return None


def parse_comparison_report(report_text: str) -> Dict[str, Any]:
    """Parse the comparison report into structured data."""
    result = {
        "products_parsed": 0,
        "disclaimer": "Prices are from extracted page text; verify on Blinkit.",
        "items": {}
    }
    
    # Extract products parsed count
    match = re.search(r"Products parsed:\s*(\d+)", report_text)
    if match:
        result["products_parsed"] = int(match.group(1))
    
    # Split by ITEM: to get each product section
    # The report has sections starting with "ITEM: <name>"
    item_blocks = re.split(r"\n(?=ITEM: )", report_text)
    
    for block in item_blocks:
        block = block.strip()
        if not block.startswith("ITEM:"):
            continue
        
        lines = block.split("\n")
        item_name = lines[0].replace("ITEM:", "").strip()
        
        # Find the category (Milk, Bread, Yogurt)
        category = None
        if "milk" in item_name.lower():
            category = "Milk"
        elif "bread" in item_name.lower():
            category = "Bread"
        elif "yogurt" in item_name.lower():
            category = "Yogurt"
        
        if not category:
            continue
        
        item_data = {
            "requested_quantity": "",
            "preferred_brand": "",
            "preferred_package": "",
            "max_price": "",
            "price_limit_violations": [],
            "package_size_mismatches": [],
            "alternative_brands": []
        }
        
        current_section = None
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Requested quantity:"):
                item_data["requested_quantity"] = line.replace("Requested quantity:", "").strip()
            elif line.startswith("Preferred brand:"):
                item_data["preferred_brand"] = line.replace("Preferred brand:", "").strip()
            elif line.startswith("Preferred package:"):
                item_data["preferred_package"] = line.replace("Preferred package:", "").strip()
            elif line.startswith("Maximum price per pack:"):
                item_data["max_price"] = line.replace("Maximum price per pack:", "").strip()
            elif "PRICE-LIMIT VIOLATIONS" in line:
                current_section = "price_limit_violations"
            elif "PACKAGE-SIZE MISMATCHES" in line:
                current_section = "package_size_mismatches"
            elif "ALTERNATIVE BRANDS" in line:
                current_section = "alternative_brands"
            elif line.startswith("- ") and current_section:
                # Parse product line
                product_line = line[2:].strip()
                item_data[current_section].append(product_line)
        
        result["items"][category] = item_data
    
    return result


def generate_summary() -> Dict[str, Any]:
    """Generate complete shopping summary from validation results."""
    base_dir = Path(__file__).parent.parent
    csv_path = base_dir / "config" / "shopping_list.csv"
    json_path = base_dir / "config" / "settings.example.json"
    
    shopping_list = validate_shopping_list(csv_path)
    settings = validate_settings(json_path)
    budget = settings.get("total_budget", Decimal("0"))
    delivery_address = settings.get("delivery_address", "")
    
    cart_data = load_mock_cart_data()
    validation = validate_cart(shopping_list, cart_data, budget)
    
    # Read and parse comparison report
    comparison_text = read_comparison_report()
    comparison_data = None
    if comparison_text:
        comparison_data = parse_comparison_report(comparison_text)
    
    # Derive price warnings from extracted comparison report
    # Check for price-limit violations in preferred brand + package matches
    extracted_price_warnings = []
    no_suitable_within_budget = []
    if comparison_data:
        for category in ["Milk", "Bread", "Yogurt"]:
            item_data = comparison_data.get("items", {}).get(category)
            if not item_data:
                continue
            
            violations = item_data.get("price_limit_violations", [])
            if violations:
                for v in violations:
                    extracted_price_warnings.append(
                        f"{category}: {v} (from extracted webpage comparison)"
                    )
            
            # Check if there are any affordable exact matches (brand + package + within budget)
            # The comparison report doesn't explicitly list affordable matches, but we can infer
            # from the absence of violations and presence of alternatives
            alternatives = item_data.get("alternative_brands", [])
            mismatches = item_data.get("package_size_mismatches", [])
            # If there are violations but no affordable exact match mentioned, flag it
            if violations and not alternatives and not mismatches:
                no_suitable_within_budget.append(
                    f"{category}: No preferred-brand/package match found within max price "
                    f"({item_data.get('max_price', '')})"
                )
    
    # Combine validation price warnings with extracted price warnings
    all_price_warnings = list(validation["price_warnings"])  # mock cart warnings
    for ew in extracted_price_warnings:
        all_price_warnings.append({
            "item_name": ew.split(":")[0],
            "observed_price": "N/A (webpage)",
            "max_acceptable": "N/A (config)",
            "exceeds_by": "N/A",
            "source": "extracted_comparison",
            "detail": ew
        })
    
    # Build warnings list
    all_warnings = list(validation["warnings"])
    for nsb in no_suitable_within_budget:
        all_warnings.append(nsb)
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "mode": "MOCK DATA - NOT LIVE BLINKIT DATA",
        "requested_items": [
            {
                "item_name": item["item_name"],
                "requested_quantity": str(item["requested_quantity"]),
                "unit": item["unit"],
                "max_unit_price": str(item["max_unit_price"]),
                "preferred_brand": item["preferred_brand"],
                "package_size": item["package_size"]
            }
            for item in shopping_list
        ],
        "observed_items": validation["matched_items"],
        "unavailable_items": validation["unavailable_items"],
        "quantity_mismatches": validation["quantity_mismatches"],
        "price_warnings": all_price_warnings,
        "unknown_items": validation["unknown_items"],
        "cart_total": str(validation["cart_total"]),
        "budget": str(budget),
        "budget_status": validation["budget_status"],
        "delivery_address": delivery_address,
        "address_verified": "PLACEHOLDER - NOT VERIFIED",
        "warnings": all_warnings,
        "order_placed": False,
        "payment_initiated": False,
        "notification_sent": False,
        "extracted_product_comparison": comparison_data,
        "notes": [
            "This summary uses MOCK DATA for development purposes only.",
            "Webpage text was extracted for product comparison; prices, availability, and cart contents were not independently verified.",
            "No order was placed and no payment was processed.",
            "PAD email and WhatsApp notifications are demo-only; no real messages were sent.",
            "All prices, quantities, and availability in the cart section are simulated.",
            "Delivery address is a placeholder and not verified.",
            "Extracted product comparison is from webpage text only - not verified live prices or cart contents."
        ]
    }
    
    return summary


def write_text_report(summary: Dict[str, Any], output_path: Path):
    """Write human-readable text report."""
    lines = []
    lines.append("=" * 60)
    lines.append("BLINKIT GROCERY ASSISTANT - SHOPPING SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Generated: {summary['timestamp']}")
    lines.append(f"Mode: {summary['mode']}")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("REQUESTED ITEMS (from shopping_list.csv)")
    lines.append("-" * 60)
    for item in summary["requested_items"]:
        lines.append(f"  {item['item_name']}: {item['requested_quantity']} {item['unit']} "
                     f"@ max {item['max_unit_price']} {item['unit']} "
                     f"(brand: {item['preferred_brand']}, size: {item['package_size']})")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("OBSERVED ITEMS IN CART (MOCK DATA - NOT LIVE BLINKIT CART DATA)")
    lines.append("-" * 60)
    if summary["observed_items"]:
        for item in summary["observed_items"]:
            lines.append(f"  {item['item_name']}: {item['observed_quantity']} {item['unit']} "
                         f"@ {item['unit_price']} = {item['line_total']} "
                         f"(brand: {item['brand']})")
    else:
        lines.append("  (none)")
    lines.append("")
    
    # Extracted Product Comparison section
    comparison = summary.get("extracted_product_comparison")
    if comparison:
        lines.append("=" * 60)
        lines.append("EXTRACTED PRODUCT COMPARISON")
        lines.append("=" * 60)
        lines.append(f"Products parsed from webpage: {comparison.get('products_parsed', 0)}")
        lines.append(f"Disclaimer: {comparison.get('disclaimer', '')}")
        lines.append("")
        
        for category in ["Milk", "Bread", "Yogurt"]:
            item_data = comparison.get("items", {}).get(category)
            if not item_data:
                continue
            
            lines.append(f"ITEM: {category}")
            lines.append(f"  Requested: {item_data.get('requested_quantity', '')}")
            lines.append(f"  Preferred brand: {item_data.get('preferred_brand', '')}")
            lines.append(f"  Preferred package: {item_data.get('preferred_package', '')}")
            lines.append(f"  Max price per pack: {item_data.get('max_price', '')}")
            lines.append("")
            
            violations = item_data.get("price_limit_violations", [])
            if violations:
                lines.append("  PRICE-LIMIT VIOLATIONS (brand + package match, over budget):")
                for v in violations:
                    lines.append(f"    - {v}")
                lines.append("")
            
            mismatches = item_data.get("package_size_mismatches", [])
            if mismatches:
                lines.append("  PACKAGE-SIZE MISMATCHES (brand matches, different package):")
                for m in mismatches:
                    lines.append(f"    - {m}")
                lines.append("")
            
            alternatives = item_data.get("alternative_brands", [])
            if alternatives:
                lines.append("  ALTERNATIVE BRANDS (matching package size):")
                for a in alternatives:
                    lines.append(f"    - {a}")
                lines.append("")
            
            lines.append("-" * 40)
        
        lines.append("")
        lines.append("NOTE: Above data is from extracted webpage text only.")
        lines.append("Not verified live prices or cart contents.")
        lines.append("")
    
    lines.append("-" * 60)
    lines.append("ISSUES DETECTED")
    lines.append("-" * 60)
    
    if summary["unavailable_items"]:
        lines.append("  Unavailable Items:")
        for item in summary["unavailable_items"]:
            lines.append(f"    - {item['item_name']} (requested: {item['requested_quantity']}): {item['reason']}")
    else:
        lines.append("  Unavailable Items: (none)")
    
    if summary["quantity_mismatches"]:
        lines.append("  Quantity Mismatches:")
        for item in summary["quantity_mismatches"]:
            lines.append(f"    - {item['item_name']}: requested {item['requested']}, observed {item['observed']} {item['unit']}")
    else:
        lines.append("  Quantity Mismatches: (none)")
    
    # Price warnings - include both mock cart warnings and extracted comparison warnings
    price_warnings = summary.get("price_warnings", [])
    extracted_warnings = [w for w in price_warnings if isinstance(w, dict) and w.get("source") == "extracted_comparison"]
    mock_warnings = [w for w in price_warnings if not (isinstance(w, dict) and w.get("source") == "extracted_comparison")]
    
    if extracted_warnings:
        lines.append("  Price Warnings (from extracted webpage comparison - preferred brand + package over max price):")
        for w in extracted_warnings:
            lines.append(f"    - {w.get('detail', w)}")
    elif mock_warnings:
        lines.append("  Price Warnings (exceeds max acceptable in mock cart):")
        for w in mock_warnings:
            if isinstance(w, dict):
                lines.append(f"    - {w['item_name']}: observed {w['observed_price']}, max {w['max_acceptable']} (+{w['exceeds_by']})")
            else:
                lines.append(f"    - {w}")
    else:
        lines.append("  Price Warnings: (none)")
    
    if summary["unknown_items"]:
        lines.append("  Unknown Items in Cart (not in shopping list):")
        for item in summary["unknown_items"]:
            lines.append(f"    - {item['item_name']}: {item['quantity']} @ {item['price']} - {item['note']}")
    else:
        lines.append("  Unknown Items: (none)")
    
    lines.append("")
    lines.append("-" * 60)
    lines.append("FINANCIAL SUMMARY")
    lines.append("-" * 60)
    lines.append(f"  Cart Total (MOCK DATA - NOT LIVE BLINKIT CART): {summary['cart_total']}")
    lines.append(f"  Budget: {summary['budget']}")
    lines.append(f"  Status: {summary['budget_status'].upper()}")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("DELIVERY ADDRESS")
    lines.append("-" * 60)
    lines.append(f"  {summary['delivery_address']}")
    lines.append(f"  Verification: {summary['address_verified']}")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("ACTIONS PERFORMED")
    lines.append("-" * 60)
    lines.append(f"  Order Placed: {summary['order_placed']}")
    lines.append(f"  Payment Initiated: {summary['payment_initiated']}")
    lines.append(f"  Notification Sent: {summary['notification_sent']} (PAD email/WhatsApp are demo-only; no real messages sent)")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("WARNINGS")
    lines.append("-" * 60)
    
    # Count extracted-comparison price warnings
    extracted_warning_count = 0
    for w in summary.get("price_warnings", []):
        if isinstance(w, dict) and w.get("source") == "extracted_comparison":
            extracted_warning_count += 1
    
    warning_messages = []
    
    if extracted_warning_count > 0:
        warning_messages.append(
            f"{extracted_warning_count} preferred-brand/package price-limit violations "
            f"found in extracted webpage text; verify prices before selecting products."
        )
    
    # Add any other warnings from summary["warnings"]
    for w in summary.get("warnings", []):
        warning_messages.append(w)
    
    if warning_messages:
        for msg in warning_messages:
            lines.append(f"  - {msg}")
    else:
        lines.append("  (none)")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("IMPORTANT NOTES")
    lines.append("-" * 60)
    for note in summary["notes"]:
        lines.append(f"  - {note}")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_json_report(summary: Dict[str, Any], output_path: Path):
    """Write machine-readable JSON report."""
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main():
    """Main summary generation entry point."""
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    summary = generate_summary()
    
    txt_path = output_dir / "shopping_summary.txt"
    json_path = output_dir / "shopping_summary.json"
    
    write_text_report(summary, txt_path)
    write_json_report(summary, json_path)
    
    print(f"Summary written to:")
    print(f"  {txt_path}")
    print(f"  {json_path}")


if __name__ == "__main__":
    main()