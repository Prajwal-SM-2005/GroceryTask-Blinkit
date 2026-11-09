#!/usr/bin/env python3
"""
Validate configuration files for the grocery shopping assistant.
Uses only standard library modules.
"""

import csv
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Any


def validate_shopping_list(csv_path: Path) -> List[Dict[str, Any]]:
    """Validate shopping list CSV and return list of validated items."""
    required_fields = [
        "item_name",
        "requested_quantity",
        "unit",
        "max_unit_price",
        "preferred_brand",
        "package_size"
    ]
    items = []
    
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or missing headers")
        
        missing = set(required_fields) - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        for row_num, row in enumerate(reader, start=2):
            item = {}
            errors = []
            
            item_name = row.get("item_name", "").strip()
            if not item_name:
                errors.append("item_name is required")
            item["item_name"] = item_name
            
            try:
                qty = Decimal(row.get("requested_quantity", "0"))
                if qty <= 0:
                    errors.append("requested_quantity must be positive")
                item["requested_quantity"] = qty
            except (InvalidOperation, TypeError):
                errors.append("requested_quantity must be a valid number")
                item["requested_quantity"] = Decimal("0")
            
            unit = row.get("unit", "").strip()
            if not unit:
                errors.append("unit is required")
            item["unit"] = unit
            
            try:
                price = Decimal(row.get("max_unit_price", "0"))
                if price < 0:
                    errors.append("max_unit_price cannot be negative")
                item["max_unit_price"] = price
            except (InvalidOperation, TypeError):
                errors.append("max_unit_price must be a valid number")
                item["max_unit_price"] = Decimal("0")
            
            item["preferred_brand"] = row.get("preferred_brand", "").strip()
            item["package_size"] = row.get("package_size", "").strip()
            
            item["_errors"] = errors
            item["_row"] = row_num
            items.append(item)
    
    return items


def validate_settings(json_path: Path) -> Dict[str, Any]:
    """Validate settings JSON file."""
    with open(json_path, encoding="utf-8") as f:
        settings = json.load(f)
    
    errors = []
    
    if "total_budget" not in settings:
        errors.append("total_budget is required")
    else:
        try:
            budget = Decimal(str(settings["total_budget"]))
            if budget < 0:
                errors.append("total_budget cannot be negative")
            settings["total_budget"] = budget
        except (InvalidOperation, TypeError):
            errors.append("total_budget must be a valid number")
            settings["total_budget"] = Decimal("0")
    
    if "delivery_address" not in settings:
        errors.append("delivery_address is required")
    elif not settings["delivery_address"].strip():
        errors.append("delivery_address cannot be empty")
    
    settings["_errors"] = errors
    return settings


def main():
    """Main validation entry point."""
    base_dir = Path(__file__).parent.parent
    csv_path = base_dir / "config" / "shopping_list.csv"
    json_path = base_dir / "config" / "settings.example.json"
    
    all_errors = []
    
    try:
        items = validate_shopping_list(csv_path)
        for item in items:
            if item["_errors"]:
                for err in item["_errors"]:
                    all_errors.append(f"Row {item['_row']} ({item['item_name']}): {err}")
    except Exception as e:
        all_errors.append(f"Shopping list validation failed: {e}")
        items = []
    
    try:
        settings = validate_settings(json_path)
        if settings["_errors"]:
            for err in settings["_errors"]:
                all_errors.append(f"Settings: {err}")
    except Exception as e:
        all_errors.append(f"Settings validation failed: {e}")
        settings = {}
    
    if all_errors:
        print("VALIDATION FAILED:")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        print(f"  Items: {len(items)}")
        print(f"  Budget: {settings.get('total_budget', 'N/A')}")
        sys.exit(0)


if __name__ == "__main__":
    main()