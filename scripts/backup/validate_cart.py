#!/usr/bin/env python3
"""
Validate observed cart data against shopping list configuration.
Uses mock data for development - does not access Blinkit.
"""

import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Any, Optional
from validate_config import validate_shopping_list, validate_settings


def load_mock_cart_data() -> List[Dict[str, Any]]:
    """Load mock cart data for testing. In PAD, this would come from desktop automation."""
    return [
        {"item_name": "Milk", "observed_quantity": "2", "unit_price": "58.00", "available": "true", "brand": "Amul"},
        {"item_name": "Bread", "observed_quantity": "1", "unit_price": "42.00", "available": "true", "brand": "Britania"},
        {"item_name": "Yogurt", "observed_quantity": "3", "unit_price": "24.00", "available": "true", "brand": "Epigamia"},
    ]


def validate_cart(
    shopping_list: List[Dict[str, Any]],
    cart_data: List[Dict[str, Any]],
    budget: Decimal
) -> Dict[str, Any]:
    """Compare cart data with shopping list and detect issues."""
    
    cart_by_name = {item["item_name"]: item for item in cart_data}
    results = {
        "matched_items": [],
        "unavailable_items": [],
        "quantity_mismatches": [],
        "price_warnings": [],
        "unknown_items": [],
        "cart_total": Decimal("0"),
        "budget_status": "within_budget",
        "warnings": []
    }
    
    for item in shopping_list:
        name = item["item_name"]
        requested_qty = item["requested_quantity"]
        max_price = item["max_unit_price"]
        
        if name not in cart_by_name:
            results["unavailable_items"].append({
                "item_name": name,
                "requested_quantity": str(requested_qty),
                "reason": "Not found in cart (mock data)"
            })
            continue
        
        cart_item = cart_by_name[name]
        
        if cart_item.get("available", "").lower() != "true":
            results["unavailable_items"].append({
                "item_name": name,
                "requested_quantity": str(requested_qty),
                "reason": "Marked unavailable in cart"
            })
            continue
        
        try:
            observed_qty = Decimal(cart_item.get("observed_quantity", "0"))
            unit_price = Decimal(cart_item.get("unit_price", "0"))
        except (InvalidOperation, TypeError):
            results["warnings"].append(f"{name}: Invalid quantity or price in cart data")
            observed_qty = Decimal("0")
            unit_price = Decimal("0")
        
        if observed_qty != requested_qty:
            results["quantity_mismatches"].append({
                "item_name": name,
                "requested": str(requested_qty),
                "observed": str(observed_qty),
                "unit": item["unit"]
            })
        
        if unit_price > max_price:
            results["price_warnings"].append({
                "item_name": name,
                "observed_price": str(unit_price),
                "max_acceptable": str(max_price),
                "exceeds_by": str(unit_price - max_price)
            })
        
        line_total = observed_qty * unit_price
        results["cart_total"] += line_total
        
        results["matched_items"].append({
            "item_name": name,
            "requested_quantity": str(requested_qty),
            "observed_quantity": str(observed_qty),
            "unit": item["unit"],
            "unit_price": str(unit_price),
            "line_total": str(line_total),
            "brand": cart_item.get("brand", "Unknown"),
            "package_size": item["package_size"]
        })
    
    for cart_item in cart_data:
        if cart_item["item_name"] not in [i["item_name"] for i in shopping_list]:
            results["unknown_items"].append({
                "item_name": cart_item["item_name"],
                "quantity": cart_item.get("observed_quantity", "0"),
                "price": cart_item.get("unit_price", "0"),
                "note": "Item in cart but not in shopping list (mock data)"
            })
    
    if results["cart_total"] > budget:
        results["budget_status"] = "over_budget"
        results["warnings"].append(
            f"Cart total {results['cart_total']} exceeds budget {budget} "
            f"by {results['cart_total'] - budget}"
        )
    
    return results


def main():
    """Main cart validation entry point."""
    base_dir = Path(__file__).parent.parent
    csv_path = base_dir / "config" / "shopping_list.csv"
    json_path = base_dir / "config" / "settings.example.json"
    
    shopping_list = validate_shopping_list(csv_path)
    settings = validate_settings(json_path)
    budget = settings.get("total_budget", Decimal("0"))
    
    cart_data = load_mock_cart_data()
    
    results = validate_cart(shopping_list, cart_data, budget)
    
    print("CART VALIDATION RESULTS:")
    print(f"  Matched items: {len(results['matched_items'])}")
    print(f"  Unavailable: {len(results['unavailable_items'])}")
    print(f"  Quantity mismatches: {len(results['quantity_mismatches'])}")
    print(f"  Price warnings: {len(results['price_warnings'])}")
    print(f"  Unknown items: {len(results['unknown_items'])}")
    print(f"  Cart total: {results['cart_total']}")
    print(f"  Budget status: {results['budget_status']}")
    
    return results


if __name__ == "__main__":
    main()