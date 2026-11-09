# Blinkit Grocery Assistant

Supporting software for a grocery-shopping assistant that uses **Microsoft Power Automate Desktop (PAD)** for desktop automation.

## Important

- **PAD is the main automation platform** - Python scripts are supporting utilities only
- **No actual Blinkit access** - all data is mock/simulated for development
- **No orders placed, no payments processed, no notifications sent**
- **No credentials, cookies, tokens, or personal addresses stored**

## Project Structure

```
Blinkit-Grocery-Assistant/
├── config/
│   ├── shopping_list.csv       # Grocery items with quantities, prices, brands
│   └── settings.example.json   # Budget, delivery address, currency
├── scripts/
│   ├── validate_config.py      # Validate CSV and JSON configuration
│   ├── validate_cart.py        # Compare cart data with shopping list
│   ├── generate_summary.py     # Generate text and JSON reports
│   └── log_event.py            # Timestamped event logging (JSONL)
├── tests/
│   └── test_project.py         # Unit tests (mock data only)
├── output/
│   ├── shopping_summary.txt    # Human-readable report
│   ├── shopping_summary.json   # Machine-readable report
│   ├── execution_log.jsonl     # Event log
│   └── screenshots/            # PAD screenshots (empty placeholder)
├── docs/
│   └── pad_implementation_checklist.md  # PAD flow documentation
├── setup_instructions.md       # Setup and run instructions
└── README.md                   # This file
```

## Quick Start

```powershell
# 1. Clone/navigate to project
cd C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant

# 2. Validate configuration
python scripts\validate_config.py

# 3. Validate cart (uses mock data)
python scripts\validate_cart.py

# 4. Generate summary reports
python scripts\generate_summary.py

# 5. Run unit tests
python -m pytest tests\test_project.py -v
```

## Configuration

### config/shopping_list.csv
| Field | Description | Example |
|-------|-------------|---------|
| item_name | Grocery item name | Milk |
| requested_quantity | Quantity needed | 2 |
| unit | Unit of measure | L |
| max_unit_price | Maximum acceptable price per unit | 60.00 |
| preferred_brand | Preferred brand | Amul |
| package_size | Package size | 1L |

### config/settings.example.json
```json
{
  "total_budget": 300.00,
  "delivery_address": "123 Fake Street, Mock City, MC 12345 (PLACEHOLDER)",
  "currency": "INR",
  "mock_mode": true
}
```

## Output Reports

- **output/shopping_summary.txt** - Human-readable summary with all items, issues, budget status
- **output/shopping_summary.json** - Machine-readable version for PAD consumption
- **output/execution_log.jsonl** - Timestamped event log (no secrets)

## Power Automate Desktop Integration

See [docs/pad_implementation_checklist.md](docs/pad_implementation_checklist.md) for:
- Main Flow and 4 subflows specification
- Input/output parameters for each flow
- How PAD calls Python scripts
- What remains to be implemented in PAD

## Testing

All tests use mock data only:
```powershell
python -m pytest tests\test_project.py -v
```

Tests cover:
- ✅ Successful validation
- ✅ Missing/unavailable items
- ✅ Quantity mismatches
- ✅ Budget overruns
- ✅ Invalid configuration
- ✅ Secret filtering in logs

## Safety & Compliance

- All prices, quantities, availability are **simulated mock data**
- Delivery address is a **placeholder** - not verified
- No live Blinkit website/app access
- No order placement or payment initiation
- No email/WhatsApp notifications sent
- No credentials stored in code or logs