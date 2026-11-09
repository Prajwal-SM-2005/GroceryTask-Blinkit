# Setup Instructions

## Prerequisites

- **Windows 10/11** with **Python 3.9+** installed
- **Microsoft Power Automate Desktop (PAD)** installed
- **Git** (optional, for version control)

Verify Python installation:
```powershell
python --version
# Should show Python 3.9.x or higher
```

## Project Setup

### 1. Navigate to Project Directory
```powershell
cd C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant
```

### 2. Verify Project Structure
```powershell
Get-ChildItem -Recurse | Where-Object { -not $_.PSIsContainer } | Select-Object FullName
```
Expected files:
- `config/shopping_list.csv`
- `config/settings.example.json`
- `scripts/validate_config.py`
- `scripts/validate_cart.py`
- `scripts/generate_summary.py`
- `scripts/log_event.py`
- `tests/test_project.py`
- `README.md`
- `setup_instructions.md`
- `docs/pad_implementation_checklist.md`

### 3. Run Configuration Validation
```powershell
python scripts\validate_config.py
```
Expected output:
```
VALIDATION PASSED
  Items: 3
  Budget: 300
```

### 4. Run Cart Validation (Mock Data)
```powershell
python scripts\validate_cart.py
```
Expected output:
```
CART VALIDATION RESULTS:
  Matched items: 3
  Unavailable: 0
  Quantity mismatches: 0
  Price warnings: 0
  Unknown items: 0
  Cart total: 260
  Budget status: within_budget
```

### 5. Generate Summary Reports
```powershell
python scripts\generate_summary.py
```
Expected output:
```
Summary written to:
  C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant\output\shopping_summary.txt
  C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant\output\shopping_summary.json
```

### 6. Verify Generated Reports
```powershell
Get-Content output\shopping_summary.txt
Get-Content output\shopping_summary.json | ConvertFrom-Json | Format-List
```

### 7. Run Unit Tests
```powershell
python -m pytest tests\test_project.py -v
```
Expected: All tests pass (17 tests)

Alternative without pytest:
```powershell
python tests\test_project.py
```

### 8. Test Event Logging
```powershell
python scripts\log_event.py
Get-Content output\execution_log.jsonl
```

## Power Automate Desktop Setup

### 1. Open Power Automate Desktop
- Launch PAD from Start Menu
- Create new flow: `BlinkitGroceryAssistant_Main`

### 2. Create Subflows (see docs/pad_implementation_checklist.md)
| Subflow | Purpose |
|---------|---------|
| `ShoppingProcess` | Navigate Blinkit, add items to cart, extract cart data |
| `EmailNotification` | Send email with summary (future) |
| `WhatsAppNotification` | Send WhatsApp message (future) |
| `ErrorHandling` | Catch errors, log, notify |

### 3. Call Python Scripts from PAD
Use **"Run PowerShell Script"** action:
```powershell
python C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant\scripts\validate_config.py
```
Capture output via `StandardOutput` variable.

### 4. Pass Data Between PAD and Python
- **PAD → Python**: Write cart data to temp CSV, pass path as argument
- **Python → PAD**: Read `output/shopping_summary.json` with "Read Text from File" action

## Configuration Customization

### Edit Shopping List
```powershell
notepad config\shopping_list.csv
```
Add/modify items following the CSV format.

### Edit Settings
```powershell
notepad config\settings.example.json
```
Update budget, address, currency. **Never use real addresses or credentials.**

## Troubleshooting

### Python not found
```powershell
# Add Python to PATH or use full path
C:\Python311\python.exe scripts\validate_config.py
```

### Permission denied
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Module import errors
```powershell
# Ensure running from project root
cd C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant
python scripts\validate_config.py
```

### Tests fail
```powershell
# Check Python path includes scripts folder
python -c "import sys; print('\n'.join(sys.path))"
```

## Development Workflow

1. **Modify mock data** in `config/` for different test scenarios
2. **Run validation** to check configuration
3. **Run cart validation** to simulate PAD cart extraction
4. **Generate summary** to verify report output
5. **Run tests** to ensure no regressions
6. **Update PAD flows** per `docs/pad_implementation_checklist.md`

## Safety Checklist Before PAD Automation

- [ ] All Python scripts tested with mock data
- [ ] No real Blinkit credentials in config
- [ ] Delivery address is placeholder only
- [ ] `mock_mode: true` in settings
- [ ] Output directory writable
- [ ] PAD flows use "Run PowerShell Script" for Python calls
- [ ] ErrorHandling subflow catches all exceptions
- [ ] No "Click" or "Type" actions on live Blinkit until approved

## Next Steps

1. Implement PAD `ShoppingProcess` subflow to:
   - Launch Blinkit website/app
   - Search/add each item from shopping_list.csv
   - Extract cart data to CSV/JSON
   - Call `validate_cart.py` with extracted data

2. Implement `ErrorHandling` subflow for:
   - Network errors
   - Element not found
   - Price changes
   - Budget exceeded

3. Implement notification subflows when approved:
   - `EmailNotification` using Outlook/Gmail actions
   - `WhatsAppNotification` using WhatsApp Web automation