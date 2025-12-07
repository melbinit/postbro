# Local Webhook Testing Guide

## Overview
Dodo Payments needs to send webhooks to your server, but localhost isn't accessible from the internet. Use a tunneling service to expose your local server.

## Option 1: ngrok (Recommended - Easiest)

### Setup
1. **Install ngrok**:
   ```bash
   # macOS
   brew install ngrok
   
   # Or download from https://ngrok.com/download
   ```

2. **Start your Django server**:
   ```bash
   cd postbro_backend
   docker compose up backend
   # Or if running directly:
   python manage.py runserver 0.0.0.0:8000
   ```

3. **Start ngrok tunnel**:
   ```bash
   ngrok http 8000
   ```

4. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

5. **Configure Dodo Webhook URL**:
   - Go to Dodo Payments dashboard
   - Webhook settings
   - Add webhook URL: `https://abc123.ngrok.io/api/billing/webhook/dodo/`
   - Save

### Testing
- Make a test payment
- Check ngrok dashboard: http://localhost:4040 (shows all requests)
- Check Django logs for webhook processing

### Pro Tips
- **Free ngrok**: URLs change on restart (get new URL each time)
- **Paid ngrok**: Can set custom domain (e.g., `postbro.ngrok.io`)
- **ngrok authtoken**: Sign up at ngrok.com for persistent URLs

---

## Option 2: localtunnel (Free, No Signup)

### Setup
1. **Install localtunnel**:
   ```bash
   npm install -g localtunnel
   ```

2. **Start tunnel**:
   ```bash
   lt --port 8000 --subdomain postbro-test
   ```
   (Note: subdomain may not be available, will assign random one)

3. **Use the provided URL** (e.g., `https://postbro-test.loca.lt`)

4. **Configure Dodo**: `https://postbro-test.loca.lt/api/billing/webhook/dodo/`

### Testing
- Make test payment
- Check terminal for incoming requests
- Check Django logs

---

## Option 3: Cloudflare Tunnel (cloudflared)

### Setup
1. **Install cloudflared**:
   ```bash
   brew install cloudflared
   ```

2. **Start tunnel**:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. **Use the provided URL**

---

## Option 4: webhook.site (Quick Testing)

### For Quick Tests Only
1. Go to https://webhook.site
2. Copy the unique URL
3. Configure Dodo to send to that URL
4. View webhook payloads in browser
5. **Manually trigger** your webhook handler with the payload

### Manual Testing Script
Create `test_webhook.py`:
```python
import requests
import json

# Get webhook payload from webhook.site
payload = {
    "business_id": "bus_...",
    "data": {
        "payment_id": "pay_test123",
        "subscription_id": "sub_test123",
        "status": "succeeded",
        "total_amount": 5900,
        "currency": "USD",
        "metadata": {
            "subscription_id": "YOUR_SUBSCRIPTION_UUID",
            "user_id": "YOUR_USER_UUID",
            "plan_id": "YOUR_PLAN_UUID",
            "plan_name": "Pro"
        }
    },
    "timestamp": "2025-12-05T10:59:30.550128Z",
    "type": "payment.succeeded"
}

# Send to local server
response = requests.post(
    "http://localhost:8000/api/billing/webhook/dodo/",
    json=payload,
    headers={
        "Content-Type": "application/json",
        "X-Dodo-Signature": "test_signature"  # Will fail verification, disable in dev
    }
)

print(response.status_code)
print(response.text)
```

---

## Recommended Setup for Development

### 1. Use ngrok with Fixed Domain (Best for Development)

```bash
# Install ngrok
brew install ngrok

# Sign up at ngrok.com and get authtoken
ngrok config add-authtoken YOUR_AUTH_TOKEN

# Create config file: ~/.ngrok2/ngrok.yml
tunnels:
  postbro:
    addr: 8000
    proto: http
    subdomain: postbro-dev  # Requires paid plan, or use random

# Start tunnel
ngrok start postbro
```

### 2. Disable Webhook Signature Verification in Development

**File: `billing/services/dodo_service.py`**

```python
def verify_webhook_signature(
    self,
    payload: bytes,
    signature: str
) -> bool:
    """
    Verify webhook signature from Dodo Payments
    """
    # Skip verification in development
    if settings.DEBUG:
        logger.warning("⚠️ [Dodo] Skipping webhook signature verification in DEBUG mode")
        return True
    
    if not self.webhook_secret:
        logger.warning("⚠️ [Dodo] Webhook secret not configured, skipping signature verification")
        return True
    
    # ... rest of verification code
```

### 3. Test Webhook Endpoint Directly

```bash
# Test webhook endpoint is accessible
curl -X POST http://localhost:8000/api/billing/webhook/dodo/ \
  -H "Content-Type: application/json" \
  -d '{"type": "test", "data": {}}'
```

### 4. Use Django Management Command for Testing

Create `billing/management/commands/test_webhook.py`:

```python
from django.core.management.base import BaseCommand
from billing.webhook_handlers import handle_payment_succeeded
from billing.models import BillingEvent
import json

class Command(BaseCommand):
    help = 'Test webhook handlers locally'

    def add_arguments(self, parser):
        parser.add_argument('event_type', type=str, choices=['payment.succeeded', 'payment.failed', 'subscription.active', 'subscription.failed'])
        parser.add_argument('--subscription-id', type=str, required=True)
        parser.add_argument('--user-id', type=str, required=True)

    def handle(self, *args, **options):
        # Create test event data based on Dodo format
        event_data = {
            "payment_id": "pay_test123",
            "subscription_id": "sub_test123",
            "status": "succeeded" if "succeeded" in options['event_type'] else "failed",
            "total_amount": 5900,
            "currency": "USD",
            "metadata": {
                "subscription_id": options['subscription_id'],
                "user_id": options['user_id'],
                "plan_id": "test-plan-id",
                "plan_name": "Pro"
            }
        }
        
        billing_event = BillingEvent.objects.create(
            payment_provider=BillingEvent.PaymentProvider.DODO,
            provider_event_id="test_event_123",
            event_type=options['event_type'],
            event_data={"type": options['event_type'], "data": event_data},
            processed=False
        )
        
        if options['event_type'] == 'payment.succeeded':
            handle_payment_succeeded(event_data, billing_event)
        # ... handle other event types
        
        self.stdout.write(self.style.SUCCESS(f'Webhook test completed: {options["event_type"]}'))
```

Usage:
```bash
python manage.py test_webhook payment.succeeded --subscription-id=YOUR_SUB_UUID --user-id=YOUR_USER_UUID
```

---

## Testing Checklist

- [ ] ngrok/localtunnel is running and accessible
- [ ] Webhook URL configured in Dodo dashboard
- [ ] Django server is running on port 8000
- [ ] Webhook endpoint is accessible: `https://your-tunnel-url/api/billing/webhook/dodo/`
- [ ] Signature verification disabled or configured for testing
- [ ] Test successful payment webhook
- [ ] Test failed payment webhook
- [ ] Check `BillingEvent` records in Django admin
- [ ] Verify subscription status changes
- [ ] Check logs for any errors

---

## Quick Start (Recommended)

```bash
# Terminal 1: Start Django
cd postbro_backend
docker compose up backend

# Terminal 2: Start ngrok
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Configure in Dodo: https://abc123.ngrok.io/api/billing/webhook/dodo/

# Terminal 3: Watch logs
docker compose logs -f backend
```

---

## Troubleshooting

### Webhook not received?
1. Check ngrok is running: Visit http://localhost:4040
2. Check Django logs: `docker compose logs backend`
3. Verify URL in Dodo dashboard matches ngrok URL
4. Test endpoint manually with curl

### Signature verification failing?
- Disable in development (see above)
- Or get webhook secret from Dodo dashboard

### Subscription not activating?
- Check webhook handler logs
- Verify subscription_id in metadata matches your subscription UUID
- Check BillingEvent records for errors

### Port already in use?
- Change Django port: `python manage.py runserver 8001`
- Update ngrok: `ngrok http 8001`

