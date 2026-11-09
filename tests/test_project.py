#!/usr/bin/env python3
"""
Unit tests for the grocery shopping assistant.
Uses only mock data - does not access Blinkit or send notifications.
"""

import unittest
import tempfile
import csv
import json
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_config import validate_shopping_list, validate_settings
from validate_cart import load_mock_cart_data, validate_cart
from generate_summary import generate_summary
from log_event import log_event


class TestValidateConfig(unittest.TestCase):
    """Tests for configuration validation."""
    
    def create_temp_csv(self, content: str) -> Path:
        """Create a temporary CSV file with given content."""
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="")
        f.write(content)
        f.close()
        return Path(f.name)
    
    def create_temp_json(self, content: dict) -> Path:
        """Create a temporary JSON file with given content."""
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(content, f)
        f.close()
        return Path(f.name)
    
    def test_valid_shopping_list(self):
        """Test successful validation of correct shopping list."""
        csv_content = """item_name,requested_quantity,unit,max_unit_price,preferred_brand,package_size
Milk,2,L,60.00,Amul,1L
Bread,1,loaf,45.00,Britania,400g
"""
        path = self.create_temp_csv(csv_content)
        try:
            items = validate_shopping_list(path)
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0]["item_name"], "Milk")
            self.assertEqual(items[0]["requested_quantity"], Decimal("2"))
            self.assertEqual(items[0]["max_unit_price"], Decimal("60.00"))
            self.assertEqual(items[0]["_errors"], [])
        finally:
            path.unlink()
    
    def test_invalid_quantity_zero(self):
        """Test rejection of zero quantity."""
        csv_content = """item_name,requested_quantity,unit,max_unit_price,preferred_brand,package_size
Milk,0,L,60.00,Amul,1L
"""
        path = self.create_temp_csv(csv_content)
        try:
            items = validate_shopping_list(path)
            self.assertTrue(any("positive" in e for e in items[0]["_errors"]))
        finally:
            path.unlink()
    
    def test_invalid_negative_price(self):
        """Test rejection of negative price."""
        csv_content = """item_name,requested_quantity,unit,max_unit_price,preferred_brand,package_size
Milk,2,L,-10.00,Amul,1L
"""
        path = self.create_temp_csv(csv_content)
        try:
            items = validate_shopping_list(path)
            self.assertTrue(any("negative" in e for e in items[0]["_errors"]))
        finally:
            path.unlink()
    
    def test_invalid_non_numeric_quantity(self):
        """Test rejection of non-numeric quantity."""
        csv_content = """item_name,requested_quantity,unit,max_unit_price,preferred_brand,package_size
Milk,abc,L,60.00,Amul,1L
"""
        path = self.create_temp_csv(csv_content)
        try:
            items = validate_shopping_list(path)
            self.assertTrue(any("valid number" in e for e in items[0]["_errors"]))
        finally:
            path.unlink()
    
    def test_missing_required_column(self):
        """Test detection of missing required column."""
        csv_content = """item_name,requested_quantity,unit
Milk,2,L
"""
        path = self.create_temp_csv(csv_content)
        try:
            with self.assertRaises(ValueError) as ctx:
                validate_shopping_list(path)
            self.assertIn("Missing required columns", str(ctx.exception))
        finally:
            path.unlink()
    
    def test_valid_settings(self):
        """Test successful validation of correct settings."""
        json_content = {
            "total_budget": 300.00,
            "delivery_address": "123 Test St",
            "currency": "INR"
        }
        path = self.create_temp_json(json_content)
        try:
            settings = validate_settings(path)
            self.assertEqual(settings["total_budget"], Decimal("300.00"))
            self.assertEqual(settings["_errors"], [])
        finally:
            path.unlink()
    
    def test_invalid_settings_negative_budget(self):
        """Test rejection of negative budget."""
        json_content = {
            "total_budget": -50.00,
            "delivery_address": "123 Test St"
        }
        path = self.create_temp_json(json_content)
        try:
            settings = validate_settings(path)
            self.assertTrue(any("negative" in e for e in settings["_errors"]))
        finally:
            path.unlink()
    
    def test_missing_settings_fields(self):
        """Test detection of missing required settings fields."""
        json_content = {"currency": "INR"}
        path = self.create_temp_json(json_content)
        try:
            settings = validate_settings(path)
            self.assertTrue(any("total_budget is required" in e for e in settings["_errors"]))
            self.assertTrue(any("delivery_address is required" in e for e in settings["_errors"]))
        finally:
            path.unlink()


class TestValidateCart(unittest.TestCase):
    """Tests for cart validation against shopping list."""
    
    def setUp(self):
        self.shopping_list = [
            {"item_name": "Milk", "requested_quantity": Decimal("2"), "unit": "L", "max_unit_price": Decimal("60.00"), "preferred_brand": "Amul", "package_size": "1L", "_errors": [], "_row": 2},
            {"item_name": "Bread", "requested_quantity": Decimal("1"), "unit": "loaf", "max_unit_price": Decimal("45.00"), "preferred_brand": "Britania", "package_size": "400g", "_errors": [], "_row": 3},
            {"item_name": "Yogurt", "requested_quantity": Decimal("3"), "unit": "cup", "max_unit_price": Decimal("25.00"), "preferred_brand": "Epigamia", "package_size": "100g", "_errors": [], "_row": 4},
        ]
        self.budget = Decimal("300.00")
    
    def test_successful_validation(self):
        """Test successful cart validation with matching items."""
        cart_data = [
            {"item_name": "Milk", "observed_quantity": "2", "unit_price": "58.00", "available": "true", "brand": "Amul"},
            {"item_name": "Bread", "observed_quantity": "1", "unit_price": "42.00", "available": "true", "brand": "Britania"},
            {"item_name": "Yogurt", "observed_quantity": "3", "unit_price": "24.00", "available": "true", "brand": "Epigamia"},
        ]
        results = validate_cart(self.shopping_list, cart_data, self.budget)
        
        self.assertEqual(len(results["matched_items"]), 3)
        self.assertEqual(len(results["unavailable_items"]), 0)
        self.assertEqual(len(results["quantity_mismatches"]), 0)
        self.assertEqual(len(results["price_warnings"]), 0)
        self.assertEqual(results["budget_status"], "within_budget")
        self.assertEqual(results["cart_total"], Decimal("2") * Decimal("58") + Decimal("1") * Decimal("42") + Decimal("3") * Decimal("24"))
    
    def test_missing_item_unavailable(self):
        """Test detection of unavailable item."""
        cart_data = [
            {"item_name": "Milk", "observed_quantity": "2", "unit_price": "58.00", "available": "true", "brand": "Amul"},
            {"item_name": "Bread", "observed_quantity": "1", "unit_price": "42.00", "available": "false", "brand": "Britania"},
            {"item_name": "Yogurt", "observed_quantity": "3", "unit_price": "24.00", "available": "true", "brand": "Epigamia"},
        ]
        results = validate_cart(self.shopping_list, cart_data, self.budget)
        
        self.assertEqual(len(results["unavailable_items"]), 1)
        self.assertEqual(results["unavailable_items"][0]["item_name"], "Bread")
    
    def test_quantity_mismatch(self):
        """Test detection of quantity mismatch."""
        cart_data = [
            {"item_name": "Milk", "observed_quantity": "1", "unit_price": "58.00", "available": "true", "brand": "Amul"},
            {"item_name": "Bread", "observed_quantity": "1", "unit_price": "42.00", "available": "true", "brand": "Britania"},
            {"item_name": "Yogurt", "observed_quantity": "3", "unit_price": "24.00", "available": "true", "brand": "Epigamia"},
        ]
        results = validate_cart(self.shopping_list, cart_data, self.budget)
        
        self.assertEqual(len(results["quantity_mismatches"]), 1)
        self.assertEqual(results["quantity_mismatches"][0]["item_name"], "Milk")
        self.assertEqual(results["quantity_mismatches"][0]["requested"], "2")
        self.assertEqual(results["quantity_mismatches"][0]["observed"], "1")
    
    def test_price_warning_exceeds_max(self):
        """Test detection of price exceeding maximum acceptable."""
        cart_data = [
            {"item_name": "Milk", "observed_quantity": "2", "unit_price": "65.00", "available": "true", "brand": "Amul"},
            {"item_name": "Bread", "observed_quantity": "1", "unit_price": "42.00", "available": "true", "brand": "Britania"},
            {"item_name": "Yogurt", "observed_quantity": "3", "unit_price": "24.00", "available": "true", "brand": "Epigamia"},
        ]
        results = validate_cart(self.shopping_list, cart_data, self.budget)
        
        self.assertEqual(len(results["price_warnings"]), 1)
        self.assertEqual(results["price_warnings"][0]["item_name"], "Milk")
        self.assertEqual(results["price_warnings"][0]["exceeds_by"], "5.00")
    
    def test_budget_overrun(self):
        """Test detection of budget overrun."""
        cart_data = [
            {"item_name": "Milk", "observed_quantity": "10", "unit_price": "58.00", "available": "true", "brand": "Amul"},
            {"item_name": "Bread", "observed_quantity": "10", "unit_price": "42.00", "available": "true", "brand": "Britania"},
            {"item_name": "Yogurt", "observed_quantity": "10", "unit_price": "24.00", "available": "true", "brand": "Epigamia"},
        ]
        results = validate_cart(self.shopping_list, cart_data, self.budget)
        
        self.assertEqual(results["budget_status"], "over_budget")
        self.assertTrue(any("exceeds budget" in w for w in results["warnings"]))
    
    def test_unknown_item_in_cart(self):
        """Test detection of unknown item not in shopping list."""
        cart_data = [
            {"item_name": "Milk", "observed_quantity": "2", "unit_price": "58.00", "available": "true", "brand": "Amul"},
            {"item_name": "Bread", "observed_quantity": "1", "unit_price": "42.00", "available": "true", "brand": "Britania"},
            {"item_name": "Yogurt", "observed_quantity": "3", "unit_price": "24.00", "available": "true", "brand": "Epigamia"},
            {"item_name": "Cheese", "observed_quantity": "1", "unit_price": "120.00", "available": "true", "brand": "Amul"},
        ]
        results = validate_cart(self.shopping_list, cart_data, self.budget)
        
        self.assertEqual(len(results["unknown_items"]), 1)
        self.assertEqual(results["unknown_items"][0]["item_name"], "Cheese")


class TestGenerateSummary(unittest.TestCase):
    """Tests for summary generation."""
    
    def test_generate_summary_structure(self):
        """Test that summary has all required fields."""
        summary = generate_summary()
        
        required_fields = [
            "timestamp", "mode", "requested_items", "observed_items",
            "unavailable_items", "quantity_mismatches", "price_warnings",
            "unknown_items", "cart_total", "budget", "budget_status",
            "delivery_address", "address_verified", "warnings",
            "order_placed", "payment_initiated", "notification_sent", "notes"
        ]
        for field in required_fields:
            self.assertIn(field, summary, f"Missing field: {field}")
        
        self.assertEqual(summary["mode"], "MOCK DATA - NOT LIVE BLINKIT DATA")
        self.assertFalse(summary["order_placed"])
        self.assertFalse(summary["payment_initiated"])
        self.assertFalse(summary["notification_sent"])
        self.assertEqual(summary["address_verified"], "PLACEHOLDER - NOT VERIFIED")


class TestLogEvent(unittest.TestCase):
    """Tests for event logging."""
    
    def setUp(self):
        # Add scripts directory to path for imports
        import sys
        scripts_path = Path(__file__).parent.parent / "scripts"
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))
    
    def test_log_event_writes_file(self):
        """Test that log_event creates log file with correct format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test_log.jsonl"
            
            import log_event as log_module
            original_path = log_module.LOG_PATH
            log_module.LOG_PATH = log_path
            
            try:
                log_event("test_event", "Test message", "INFO", {"key": "value"})
                
                self.assertTrue(log_path.exists())
                content = log_path.read_text(encoding="utf-8").strip()
                entry = json.loads(content)
                
                self.assertEqual(entry["event_type"], "test_event")
                self.assertEqual(entry["message"], "Test message")
                self.assertEqual(entry["level"], "INFO")
                self.assertEqual(entry["extra"]["key"], "value")
                self.assertIn("timestamp", entry)
            finally:
                log_module.LOG_PATH = original_path
    
    def test_log_event_filters_secrets(self):
        """Test that log_event filters out sensitive fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test_log.jsonl"
            
            import log_event as log_module
            original_path = log_module.LOG_PATH
            log_module.LOG_PATH = log_path
            
            try:
                log_event("test", "Message with secret", "INFO", {"password": "secret123", "safe_field": "value"})
                
                content = log_path.read_text(encoding="utf-8").strip()
                entry = json.loads(content)
                
                self.assertNotIn("password", entry.get("extra", {}))
                self.assertEqual(entry["extra"]["safe_field"], "value")
            finally:
                log_module.LOG_PATH = original_path


if __name__ == "__main__":
    unittest.main()