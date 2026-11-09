# Power Automate Desktop Implementation Checklist

This document specifies the PAD flows needed for the Blinkit Grocery Assistant.
**Python scripts are supporting utilities only** - PAD is the main automation platform.

---

## Flow Architecture

```
BlinkitGroceryAssistant_Main (Main Flow)
├── ShoppingProcess (Subflow)
├── EmailNotification (Subflow) - NOT YET IMPLEMENTED
├── WhatsAppNotification (Subflow) - NOT YET IMPLEMENTED
└── ErrorHandling (Subflow)
```

---

## 1. Main Flow: `BlinkitGroceryAssistant_Main`

### Purpose
Orchestrate the complete grocery shopping process.

### Input Parameters
| Parameter | Type | Source |
|-----------|------|--------|
| `ShoppingListPath` | Text | `config/shopping_list.csv` |
| `SettingsPath` | Text | `config/settings.example.json` |
| `OutputDir` | Text | `output/` |

### Variables
| Variable | Type | Description |
|----------|------|-------------|
| `ValidationResult` | Text | Output from validate_config.py |
| `CartDataPath` | Text | Path to cart data extracted by ShoppingProcess |
| `CartValidationResult` | Text | Output from validate_cart.py |
| `SummaryJsonPath` | Text | `output/shopping_summary.json` |
| `ErrorOccurred` | Boolean | Error flag |

### Steps
1. **Validate Configuration**
   - Action: "Run PowerShell Script"
   - Script: `python "%ShoppingListPath%\..\scripts\validate_config.py"`
   - Output → `ValidationResult`
   - If error → Call `ErrorHandling` with "Config validation failed"

2. **Execute Shopping Process**
   - Call Subflow: `ShoppingProcess`
   - Input: `ShoppingListPath`, `SettingsPath`
   - Output: `CartDataPath` (path to extracted cart CSV/JSON)
   - If error → Call `ErrorHandling`

3. **Validate Cart**
   - Action: "Run PowerShell Script"
   - Script: `python "%ShoppingListPath%\..\scripts\validate_cart.py" --cart "%CartDataPath%"`
   - Output → `CartValidationResult`
   - If error → Call `ErrorHandling`

4. **Generate Summary**
   - Action: "Run PowerShell Script"
   - Script: `python "%ShoppingListPath%\..\scripts\generate_summary.py"`
   - Output → `SummaryJsonPath` (read `output/shopping_summary.json`)

5. **Check Budget Status**
   - Action: "Read Text from File" → `SummaryJsonPath`
   - Parse JSON, get `budget_status`
   - If `over_budget` → Call `ErrorHandling` with "Budget exceeded"

6. **Conditional Notifications** (FUTURE)
   - If `budget_status == "within_budget"` AND notifications enabled:
     - Call `EmailNotification` with `SummaryJsonPath`
     - Call `WhatsAppNotification` with `SummaryJsonPath`

7. **Log Completion**
   - Action: "Run PowerShell Script"
   - Script: `python "%ShoppingListPath%\..\scripts\log_event.py" --event "main_complete" --message "Shopping assistant completed"`

---

## 2. Subflow: `ShoppingProcess`

### Purpose
**PAD DESKTOP AUTOMATION** - Navigate Blinkit, add items, extract cart data.

### Input Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `ShoppingListPath` | Text | Path to shopping_list.csv |
| `SettingsPath` | Text | Path to settings.example.json |

### Output Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `CartDataPath` | Text | Path to extracted cart data (CSV/JSON) |
| `ItemsProcessed` | Number | Count of items added to cart |
| `Errors` | List | Any errors during automation |

### Steps (TO BE IMPLEMENTED IN PAD)

#### 2.1 Launch Blinkit
- [ ] Action: "Launch New Chrome/Edge" → `https://blinkit.com`
- [ ] Wait for page load (URL contains blinkit.com)
- [ ] Handle location permission popup if appears

#### 2.2 Set Delivery Location
- [ ] Read `delivery_address` from `SettingsPath` (JSON)
- [ ] **NOTE**: Address is PLACEHOLDER - do not use real address
- [ ] Click location input → Type address → Select first suggestion
- [ ] Confirm location

#### 2.3 Process Each Item
- [ ] Read `ShoppingListPath` (CSV) → Loop through rows
- [ ] For each item:
  - [ ] Search: Click search box → Type `item_name` + `preferred_brand`
  - [ ] Wait for results
  - [ ] Find product matching `preferred_brand` and `package_size`
  - [ ] Check price ≤ `max_unit_price`
  - [ ] Click "Add to Cart" × `requested_quantity`
  - [ ] Log event: `log_event("item_added", "Added {item_name} x{quantity}")`
  - [ ] Handle out-of-stock: if unavailable → log, continue

#### 2.4 Extract Cart Data
- [ ] Navigate to cart page
- [ ] For each cart item, extract:
  - `item_name`
  - `observed_quantity`
  - `unit_price`
  - `available` (true/false)
  - `brand`
- [ ] Write to temp file: `%TEMP%\blinkit_cart_%DATE%.csv`
- [ ] Set `CartDataPath` = temp file path

#### 2.5 Error Handling Within Subflow
- [ ] Wrap each item in Try/Catch
- [ ] On error: Log to `Errors` list, continue to next item
- [ ] If critical error (browser crash, login required): Throw to Main Flow

---

## 3. Subflow: `EmailNotification` (NOT YET IMPLEMENTED)

### Purpose
Send email with shopping summary.

### Input Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `SummaryJsonPath` | Text | Path to shopping_summary.json |
| `RecipientEmail` | Text | From settings (placeholder) |
| `SenderEmail` | Text | From settings (placeholder) |

### Steps (FUTURE)
- [ ] Read `SummaryJsonPath` → Parse JSON
- [ ] Compose email body from summary
- [ ] Action: "Send Email" (Outlook/Gmail connector)
- [ ] Attach `shopping_summary.txt`
- [ ] Log event: `email_sent`

### Blockers
- Requires approved email credentials
- Requires notification policy approval
- **DO NOT IMPLEMENT YET**

---

## 4. Subflow: `WhatsAppNotification` (NOT YET IMPLEMENTED)

### Purpose
Send WhatsApp message with shopping summary.

### Input Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `SummaryJsonPath` | Text | Path to shopping_summary.json |
| `RecipientPhone` | Text | From settings (placeholder) |

### Steps (FUTURE)
- [ ] Read `SummaryJsonPath` → Parse JSON
- [ ] Compose short message
- [ ] Action: "Launch New Chrome" → `web.whatsapp.com`
- [ ] Wait for QR code scan (manual) or use saved session
- [ ] Search contact → Send message
- [ ] Log event: `whatsapp_sent`

### Blockers
- Requires approved phone number
- Requires WhatsApp Web session management
- **DO NOT IMPLEMENT YET**

---

## 5. Subflow: `ErrorHandling`

### Purpose
Centralized error handling, logging, and recovery.

### Input Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `ErrorMessage` | Text | Description of error |
| `ErrorSource` | Text | Which flow/subflow failed |
| `ErrorDetails` | Text | Stack trace or details |

### Steps
1. **Log Error**
   - Action: "Run PowerShell Script"
   - Script: `python "scripts\log_event.py" --event "error" --level "ERROR" --message "%ErrorMessage%" --extra "{"source": "%ErrorSource%", "details": "%ErrorDetails%"}"`

2. **Take Screenshot**
   - Action: "Take Screenshot" → Save to `output/screenshots/error_%DATETIME%.png`

3. **Determine Recovery Action**
   - If `ErrorSource == "ShoppingProcess"`:
     - [ ] Retry logic (max 2 retries)
     - [ ] If persistent → Skip item, continue
   - If `ErrorSource == "validate_config"`:
     - [ ] Stop flow - configuration must be fixed manually
   - If `ErrorSource == "budget_check"`:
     - [ ] Stop flow - requires human decision

4. **Notify (Future)**
   - [ ] Call `EmailNotification` with error details (when implemented)
   - [ ] Call `WhatsAppNotification` with error details (when implemented)

5. **Set Main Flow Error Flag**
   - Set `ErrorOccurred = True`
   - Return to Main Flow for graceful exit

---

## Data Flow Summary

```
config/shopping_list.csv
       │
       ▼
validate_config.py (Python) ──→ ValidationResult
       │
       ▼
ShoppingProcess (PAD) ──→ CartDataPath (CSV/JSON)
       │
       ▼
validate_cart.py (Python) ──→ CartValidationResult
       │
       ▼
generate_summary.py (Python) ──→ output/shopping_summary.{txt,json}
       │
       ▼
Main Flow: Check budget_status
       │
       ├── within_budget ──→ (Future) EmailNotification, WhatsAppNotification
       │
       └── over_budget ──→ ErrorHandling
```

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Python: validate_config.py | ✅ Done | Tests pass |
| Python: validate_cart.py | ✅ Done | Tests pass |
| Python: generate_summary.py | ✅ Done | Tests pass |
| Python: log_event.py | ✅ Done | Tests pass |
| PAD: Main Flow | 📋 Planned | See steps above |
| PAD: ShoppingProcess | 📋 Planned | Core automation - highest priority |
| PAD: EmailNotification | ⏸ Blocked | Awaiting approval |
| PAD: WhatsAppNotification | ⏸ Blocked | Awaiting approval |
| PAD: ErrorHandling | 📋 Planned | Basic structure defined |

---

## PAD Development Guidelines

1. **Never hardcode credentials** - use PAD variables/input parameters
2. **Use explicit waits** - not fixed delays
3. **Handle dynamic selectors** - Blinkit UI may change
4. **Log every step** - call `log_event.py` for audit trail
5. **Test with mock data first** - use `mock_mode: true` in settings
6. **No live Blinkit access** until explicit approval
7. **Screenshots on error** - save to `output/screenshots/`

---

## Next Actions

1. [ ] Create PAD Main Flow skeleton
2. [ ] Implement ShoppingProcess subflow (start with 1 item)
3. [ ] Test cart data extraction format matches Python expectations
4. [ ] Implement ErrorHandling subflow
5. [ ] Integrate Python script calls via "Run PowerShell Script"
6. [ ] End-to-end test with mock data
7. [ ] Get approval for live Blinkit access
8. [ ] Implement notifications (separate approval cycle)