# ngrok Setup for Webhook Testing

## ✅ Current Status

**ngrok is running!**

- **Public URL**: `https://58ca3475465e.ngrok-free.app`
- **Webhook Endpoint**: `https://58ca3475465e.ngrok-free.app/api/billing/webhook/dodo/`
- **ngrok Dashboard**: http://localhost:4040
- **Backend**: Running on port 8000

## 🔧 Configure Dodo Payments

1. **Go to Dodo Payments Dashboard**
   - Navigate to Webhook settings
   - Or API settings → Webhooks

2. **Add Webhook URL**:
   ```
   https://58ca3475465e.ngrok-free.app/api/billing/webhook/dodo/
   ```

3. **Select Events** (if available):
   - ✅ `payment.succeeded`
   - ✅ `payment.failed`
   - ✅ `subscription.active`
   - ✅ `subscription.renewed`
   - ✅ `subscription.failed`

4. **Save the webhook configuration**

## 🧪 Testing

### Test 1: Check Endpoint is Accessible
```bash
curl -X POST https://58ca3475465e.ngrok-free.app/api/billing/webhook/dodo/ \
  -H "Content-Type: application/json" \
  -d '{"type": "test", "data": {}}'
```

### Test 2: Make a Test Payment
1. Go to your app
2. Subscribe to a paid plan
3. Complete payment in Dodo test mode
4. Watch ngrok dashboard: http://localhost:4040
5. Check Django logs: `docker compose logs -f backend`

### Test 3: View Webhook Requests
- **ngrok Dashboard**: http://localhost:4040
  - Shows all incoming requests
  - View request/response details
  - Replay requests for testing

### Test 4: Check Django Logs
```bash
docker compose logs -f backend | grep -i webhook
```

## 📊 Monitor Webhook Processing

### Check BillingEvent Records
```bash
docker compose exec backend python manage.py shell
```

```python
from billing.models import BillingEvent
from accounts.models import Subscription

# View recent webhook events
BillingEvent.objects.all().order_by('-created_at')[:10]

# Check subscription status
Subscription.objects.filter(status='pending')
Subscription.objects.filter(status='active')
```

## ⚠️ Important Notes

1. **ngrok Free Plan**:
   - URL changes each time you restart ngrok
   - You'll need to update Dodo webhook URL if you restart
   - Consider ngrok paid plan for fixed domain

2. **Signature Verification**:
   - Currently disabled in DEBUG mode
   - Will be enabled in production
   - Make sure `DODO_WEBHOOK_SECRET` is set in production

3. **Keep ngrok Running**:
   - Don't close the terminal where ngrok is running
   - Or run it in background: `ngrok http 8000 &`

## 🛠️ Troubleshooting

### Webhook not received?
1. Check ngrok is running: Visit http://localhost:4040
2. Verify URL in Dodo matches ngrok URL exactly
3. Check Django logs for errors
4. Test endpoint manually with curl

### ngrok URL changed?
- Restart ngrok: `pkill ngrok && ngrok http 8000`
- Get new URL from http://localhost:4040
- Update Dodo webhook URL

### Backend not responding?
- Check backend is running: `docker compose ps`
- Check logs: `docker compose logs backend`
- Restart if needed: `docker compose restart backend`

## 🎯 Next Steps

1. ✅ Configure webhook URL in Dodo dashboard
2. ✅ Make a test payment
3. ✅ Monitor webhook in ngrok dashboard
4. ✅ Check subscription status changes
5. ✅ Verify payment records are created

