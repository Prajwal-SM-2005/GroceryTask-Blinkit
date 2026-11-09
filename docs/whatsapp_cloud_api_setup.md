# WhatsApp Cloud API Setup Guide

This document explains how to configure and use the WhatsApp Cloud API integration for the Blinkit Grocery Assistant project.

## Prerequisites

- A Meta Developer account
- A Meta Business account (or create one during setup)
- Admin access to a Meta Business Portfolio
- A verified phone number for WhatsApp Business

## Step 1: Create a Meta App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Click **My Apps** → **Create App**
3. Choose **Business** as the app type
4. Fill in the app name (e.g., "Blinkit Grocery Assistant") and your email
5. Click **Create App**

## Step 2: Add WhatsApp Product

1. In your app dashboard, click **Add Product** or **Set Up** next to **WhatsApp**
2. This creates a WhatsApp Business Account (WABA) if you don't have one
3. Follow the onboarding flow:
   - Select or create a Meta Business Portfolio
   - Select or create a WhatsApp Business Account
   - Choose a phone number (you'll get a test number initially)

## Step 3: Get Test Credentials

After WhatsApp setup, you'll see a **Getting Started** page with:

- **Phone Number ID** (e.g., `1311740252032810`) — this is your `WHATSAPP_PHONE_NUMBER_ID`
- **Access Token** (temporary, expires in 24 hours) — this is your `WHATSAPP_ACCESS_TOKEN`
- **Test Recipient** — add your own phone number here for testing

**Important:** The test recipient must be verified in the Meta dashboard before you can send messages to it.

### Your Configured Values
- **Phone Number ID**: `1311740252032810`
- **Test Recipient**: `+15556292158`
- **Messaging Account ID**: `39495530250093892`

## Step 4: Configure Environment Variables

### Option A: .env File (Recommended for Local Development)

1. Copy the example file:
   ```powershell
   copy .env.example .env
   ```

2. Edit `.env` with your actual credentials:
   ```env
   WHATSAPP_ACCESS_TOKEN=your_actual_access_token_here
   WHATSAPP_PHONE_NUMBER_ID=1311740252032810
   WHATSAPP_TEST_RECIPIENT=+15556292158
   ```

3. The script automatically loads `.env` from the project root.

**Security:** The `.env` file is listed in `.gitignore` and will never be committed.

### Option B: PowerShell (Current Session)

```powershell
$env:WHATSAPP_ACCESS_TOKEN = "your_access_token"
$env:WHATSAPP_PHONE_NUMBER_ID = "1311740252032810"
$env:WHATSAPP_TEST_RECIPIENT = "+15556292158"
```

### Option C: Command Prompt (Current Session)

```cmd
set WHATSAPP_ACCESS_TOKEN=your_access_token
set WHATSAPP_PHONE_NUMBER_ID=1311740252032810
set WHATSAPP_TEST_RECIPIENT=+15556292158
```

### Option D: Permanent (User Environment Variables)

1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Go to **Advanced** tab → **Environment Variables**
3. Under **User variables**, click **New** for each:
   - Variable: `WHATSAPP_ACCESS_TOKEN`, Value: your token
   - Variable: `WHATSAPP_PHONE_NUMBER_ID`, Value: `1311740252032810`
   - Variable: `WHATSAPP_TEST_RECIPIENT`, Value: `+15556292158`
4. Restart PowerShell/Command Prompt for changes to take effect

## Step 5: SSL Certificate Verification (Windows)

On Windows, Python's built-in `urllib` may fail with `[SSL: CERTIFICATE_VERIFY_FAILED]` if it cannot locate trusted CA certificates. The script now uses the `certifi` package for consistent cross-platform certificate verification.

### Recommended: Use Windows Python with certifi

1. **Install certifi** (if not already installed):
   ```powershell
   python -m pip install certifi
   ```

2. **Use the Windows Python installation** (not MSYS2/Git Bash Python):
   ```powershell
   # Check which Python you're using
   where python
   
   # Should show something like: C:\Users\<name>\AppData\Local\Programs\Python\Python311\python.exe
   # NOT: C:\msys64\mingw64\bin\python.exe
   ```

3. **Verify certifi is available**:
   ```powershell
   python -c "import certifi; print(certifi.where())"
   # Should print a path to cacert.pem
   ```

If you must use the MSYS2 Python, you may need to configure the Windows certificate store manually or install certifi via pacman (if available).

### Dry Run (No Network Request)

```powershell
python scripts/send_whatsapp_notification.py --dry-run
```

Expected output:
```
WhatsApp Cloud API Test Notification
==================================================
Recipient: +15556292158
Phone Number ID: 1311740252032810
Template:  hello_world
Mode:      DRY RUN

Payload that would be sent:
{
  "messaging_product": "whatsapp",
  "to": "+15556292158",
  "type": "template",
  "template": {
    "name": "hello_world",
    "language": {
      "code": "en_US"
    }
  }
}

SUCCESS: Dry-run completed (no message sent)
Dry-run mode: no network request made
```

### Live Test (Sends Real Message)

```powershell
python scripts/send_whatsapp_notification.py --send
```

Expected output:
```
WhatsApp Cloud API Test Notification
==================================================
Recipient: +15556292158
Phone Number ID: 1311740252032810
Template:  hello_world
Mode:      LIVE (--send)

SUCCESS: Message accepted by WhatsApp API
Message ID: wamid.xxxxxxxxxxxx
NOTE: Message accepted by API. Delivery confirmation requires webhook.
```

The recipient will receive a WhatsApp message with the `hello_world` template content.

## Step 6: Production Considerations

### Permanent Access Token

The token from the dashboard expires in 24 hours. For production:

1. Go to **WhatsApp** → **API Setup** in your app dashboard
2. Generate a **System User Token** or use the **Permanent Token** flow
3. Store it securely (not in code)

### Message Templates

For production notifications, create custom templates in the Meta dashboard:
1. Go to **WhatsApp** → **Message Templates**
2. Click **Create Template**
3. Choose category (e.g., `UTILITY` for order updates)
4. Submit for Meta approval
5. Use the approved template name in your code

### Security Best Practices

- **Never commit tokens to git** — use environment variables only
- **Rotate tokens periodically** — set calendar reminders
- **Limit token permissions** — use minimal required scopes
- **Monitor usage** — check Meta dashboard for unusual activity
- **Use HTTPS only** — the script enforces this via the API URL

### ⚠️ Token Revocation Required

The access token previously appeared in a shared transcript. **You must revoke it and generate a fresh token:**

1. Go to Meta App Dashboard → **WhatsApp** → **API Setup**
2. Click **Revoke** on the current token
3. Generate a new token
4. Update your `.env` file or environment variables

## Step 7: PAD Integration

See [docs/pad_whatsapp_integration.md](pad_whatsapp_integration.md) for Power Automate Desktop integration instructions.

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Missing required environment variables` | Env vars not set | Set all three variables (see Step 4) |
| `HTTP 400: Invalid recipient` | Recipient not in test numbers | Add phone to test numbers in Meta dashboard |
| `HTTP 401: Invalid token` | Token expired or wrong | Regenerate token in dashboard |
| `HTTP 403: Permission denied` | App not approved or WABA issue | Check app status and WABA ownership |
| `Network error` | Firewall/proxy | Check network allows `graph.facebook.com:443` |
| `[SSL: CERTIFICATE_VERIFY_FAILED]` | Missing CA certificates | Install `certifi` and use Windows Python (see Step 5) |
| `Must specify either --dry-run or --send` | No mode selected | Use `--dry-run` or `--send` flag |

## File Reference

- **Script:** `scripts/send_whatsapp_notification.py`
- **Test:** `tests/test_whatsapp_notification.py`
- **Run tests:** `python tests/test_whatsapp_notification.py`
- **PAD Guide:** `docs/pad_whatsapp_integration.md`

## Safety Notes

- The script only supports the built-in `hello_world` template for testing
- Custom templates require Meta approval before use
- The `WHATSAPP_TEST_RECIPIENT` must be pre-approved in the Meta dashboard
- Dry-run mode (`--dry-run`) makes zero network requests
- Live sending requires explicit `--send` flag
- No credentials are ever logged or printed
- API acceptance ≠ delivery confirmation (requires webhook)