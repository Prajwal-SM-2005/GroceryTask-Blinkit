# PAD WhatsApp Integration Guide

This document explains how to integrate the Python WhatsApp notification script into the existing Power Automate Desktop `WhatsAppNotification` subflow.

## Prerequisites

- Python script tested and working via `--dry-run` and `--send`
- `.env` file configured with valid credentials
- Meta WhatsApp Cloud API app set up and test recipient verified

## PAD `Run Application` Configuration

Add a **Run application** action to your `WhatsAppNotification` subflow with these exact values:

### Action Parameters

| Field | Value |
|-------|-------|
| **Application path** | `python.exe` (or full path like `C:\Python311\python.exe`) |
| **Command line arguments** | `scripts\send_whatsapp_notification.py --send` |
| **Working folder** | `C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant` |
| **Wait for completion** | `Yes` |
| **Window state** | `Normal` |
| **Run as administrator** | `No` |

### Alternative: Full Python Path

If `python` is not in system PATH for the PAD runtime user, use full path:

| Field | Value |
|-------|-------|
| **Application path** | `C:\Users\smpra\AppData\Local\Programs\Python\Python311\python.exe` |
| **Command line arguments** | `C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant\scripts\send_whatsapp_notification.py --send` |
| **Working folder** | `C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant` |

## Capturing Exit Code and Output

### Method 1: Capture Exit Code (Recommended)

1. In the **Run application** action, enable **Capture exit code**
2. Store result in variable: `WhatsAppExitCode`
3. Add **If** condition after:
   ```
   If WhatsAppExitCode = 0
       Log "WHATSAPP_API_ACCEPTED" to execution log
   Else
       Log "WHATSAPP_NOTIFICATION_FAILED" to execution log
   ```

### Method 2: Capture Console Output

1. In the **Run application** action, enable **Capture console output**
2. Store result in variable: `WhatsAppOutput`
3. Parse output for "Message ID:" or "Error:"

### Method 3: Read Execution Log (Best for Audit Trail)

The Python script writes structured events to `output/execution_log.jsonl`. After the Run application action:

1. Add **Read text from file** action:
   - File: `C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant\output\execution_log.jsonl`
2. Parse last line as JSON
3. Check `event_type` field for:
   - `WHATSAPP_API_ACCEPTED` → API accepted message
   - `WHATSAPP_NOTIFICATION_FAILED` → Send failed
   - `WHATSAPP_DEMO_STARTED` → Dry run was executed

## Integrating into Existing `WhatsAppNotification` Subflow

### Current Flow (Demo Actions)
```
WhatsAppNotification Subflow
├── Demo: Display message "WhatsApp notification sent"
├── Demo: Wait 1 second
└── Set WhatsAppSent = True
```

### Updated Flow (Real + Demo Parallel)

**Option A: Replace Demo with Real (After Verification)**
```
WhatsAppNotification Subflow
├── Run application: python scripts/send_whatsapp_notification.py --send
│   ├── Working folder: C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant
│   ├── Wait for completion: Yes
│   └── Capture exit code → WhatsAppExitCode
├── If WhatsAppExitCode = 0
│   ├── Log "WHATSAPP_API_ACCEPTED" with message ID
│   └── Set WhatsAppSent = True
├── Else
│   ├── Log "WHATSAPP_NOTIFICATION_FAILED" with error
│   └── Set WhatsAppSent = False
└── (Optional) Keep demo actions as fallback/disabled
```

**Option B: Keep Both During Transition**
```
WhatsAppNotification Subflow
├── Run application: python scripts/send_whatsapp_notification.py --send
│   └── Capture exit code → WhatsAppExitCode
├── If WhatsAppExitCode = 0
│   ├── Log "WHATSAPP_API_ACCEPTED"
│   └── Set RealWhatsAppSent = True
├── Else
│   └── Log "WHATSAPP_NOTIFICATION_FAILED"
├── Demo actions (keep for now, disabled or conditional)
│   └── If RealWhatsAppSent = False
│       └── Display "Fallback: Demo notification"
```

## Execution Log Events

The Python script writes these events to `output/execution_log.jsonl`:

| Event Type | When | Extra Fields |
|------------|------|--------------|
| `WHATSAPP_DEMO_STARTED` | `--dry-run` executed | `recipient`, `phone_number_id`, `template`, `mode: "dry_run"` |
| `WHATSAPP_API_ACCEPTED` | Live send, API returned 200 | `message_id`, `recipient` |
| `WHATSAPP_NOTIFICATION_FAILED` | Live send failed (any error) | `recipient`, `error` (sanitized) |

### Log Format Example

```json
{
  "timestamp": "2026-10-28T14:30:00.123456",
  "level": "INFO",
  "event_type": "WHATSAPP_API_ACCEPTED",
  "message": "WhatsApp API accepted message",
  "extra": {
    "message_id": "wamid.HBgMMTU1NTYyOTIxNThVAgASGBQzQkUwMkQ0NzY5QzREMkYyQzQ3",
    "recipient": "+15556292158"
  }
}
```

## Distinguishing API Acceptance vs Delivery

**Important:** The WhatsApp Cloud API returns a message ID when the message is **accepted for delivery**, not when it's **delivered to the recipient's device**.

| Status | Meaning | How to Detect |
|--------|---------|---------------|
| API Accepted | Meta accepted the message for processing | `event_type: WHATSAPP_API_ACCEPTED` + `message_id` present |
| Delivered | Message reached recipient's device | Requires webhook (not implemented in this script) |
| Read | Recipient opened the message | Requires webhook (not implemented) |
| Failed | Message failed to send | `event_type: WHATSAPP_NOTIFICATION_FAILED` |

### For Delivery Confirmation

To track actual delivery, you would need to:
1. Set up a webhook endpoint (HTTPS URL)
2. Configure it in Meta App Dashboard → WhatsApp → Configuration → Webhooks
3. Handle `message_template_sent`, `message_delivered`, `message_read` events

This is **not implemented** in the current Python script. The script only confirms API acceptance.

## Testing the Integration

### 1. Test Dry Run in PAD
Change arguments to `--dry-run` and verify:
- Exit code = 0
- Log shows `WHATSAPP_DEMO_STARTED`
- No message sent to recipient

### 2. Test Live Send in PAD
Use `--send` and verify:
- Exit code = 0
- Log shows `WHATSAPP_API_ACCEPTED`
- Message ID captured
- Recipient receives message

### 3. Test Failure Handling
Temporarily use invalid token and verify:
- Exit code = 1
- Log shows `WHATSAPP_NOTIFICATION_FAILED`
- Error message sanitized (no token in logs)

## Credentials in PAD

**Do not hardcode credentials in PAD actions.**

Options for providing credentials to the Python script:

### Option 1: User Environment Variables (Recommended)
Set `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEST_RECIPIENT` as **User Environment Variables** on the machine running PAD. The script reads them automatically.

### Option 2: .env File in Working Folder
Place `.env` file in `C:\Users\smpra\OneDrive\Desktop\Blinkit-Grocery-Assistant\`. The script auto-loads it.

### Option 3: PAD Environment Variables
In PAD flow variables, set:
- `EnvVar_WHATSAPP_ACCESS_TOKEN`
- `EnvVar_WHATSAPP_PHONE_NUMBER_ID`
- `EnvVar_WHATSAPP_TEST_RECIPIENT`

Then in Run Application action, add to **Environment variables** section (if supported) or use a wrapper script.

## Troubleshooting PAD Integration

| Issue | Solution |
|-------|----------|
| Exit code 2, "Missing environment variables" | Ensure env vars are set for the PAD runtime user |
| Exit code 1, "HTTP 401: Invalid token" | Token expired; regenerate in Meta dashboard |
| Exit code 1, "HTTP 400: Invalid recipient" | Recipient not verified in Meta test numbers |
| "python.exe not found" | Use full path to python.exe in Application path |
| Script runs but no message received | Check Meta dashboard for message status; verify recipient is test number |

## Rollback Plan

If issues arise:
1. Disable the new Run Application action
2. Re-enable the original demo actions
3. Check `output/execution_log.jsonl` for error details
4. Fix credentials/token and re-test manually via PowerShell first

## Files Reference

| File | Purpose |
|------|---------|
| `scripts/send_whatsapp_notification.py` | Main script (supports `--dry-run`, `--send`) |
| `docs/whatsapp_cloud_api_setup.md` | Credential setup guide |
| `output/execution_log.jsonl` | Structured event log |
| `.env` | Local credentials (gitignored) |

## Safety Checklist Before Going Live

- [ ] Dry-run works in PAD (exit code 0, no message sent)
- [ ] Live send works in PowerShell (recipient receives message)
- [ ] Live send works in PAD (exit code 0, message ID logged)
- [ ] Failure case tested (invalid token → exit code 1, error logged)
- [ ] `.env` file in `.gitignore`
- [ ] No credentials in PAD actions or variables
- [ ] Old token revoked, new token in use
- [ ] Demo actions preserved as fallback