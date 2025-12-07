# ✅ Webhook Testing Ready!

## Current Status

- ✅ **Backend**: Running and healthy
- ✅ **ngrok**: Running at `https://58ca3475465e.ngrok-free.app`
- ✅ **Webhook URL**: `https://58ca3475465e.ngrok-free.app/api/billing/webhook/dodo/`
- ✅ **ALLOWED_HOSTS**: Fixed to allow ngrok domains
- ✅ **Endpoint**: Responding correctly

## 🧪 Ready to Test!

### Step 1: Make a Test Payment
1. Go to your app (frontend)
2. Navigate to subscription/plans
3. Click "Subscribe" on a paid plan (e.g., Starter or Pro)
4. Complete payment in Dodo test mode

### Step 2: Monitor Webhooks

**Watch ngrok Dashboard:**
- Open: http://localhost:4040
- You'll see the webhook request appear when Dodo sends it

**Watch Django Logs:**
```bash
docker compose logs -f backend | grep -i webhook
```

**Or watch all logs:**
```bash
docker compose logs -f backend
```

### Step 3: Verify Results

**Check Subscription Status:**
```bash
docker compose exec backend python manage.py shell
```

```python
from accounts.models import Subscription
from billing.models import BillingEvent, Payment

# Check recent subscriptions
Subscription.objects.all().order_by('-created_at')[:5]

# Check webhook events
BillingEvent.objects.all().order_by('-created_at')[:5]

# Check payments
Payment.objects.all().order_by('-created_at')[:5]
```

## 📊 What to Look For

### Successful Payment Flow:
1. ✅ Subscription created with `PENDING` status
2. ✅ Webhook `payment.succeeded` received
3. ✅ Payment record created
4. ✅ Subscription status changed to `ACTIVE`
5. ✅ User gets access to paid plan features

### Failed Payment Flow:
1. ✅ Subscription created with `PENDING` status
2. ✅ Webhook `payment.failed` received
3. ✅ Failed payment record created
4. ✅ Subscription status changed to `CANCELLED`
5. ✅ User stays on free plan

## 🔍 Debugging

### If webhook not received:
1. Check ngrok dashboard: http://localhost:4040
2. Verify URL in Dodo matches exactly
3. Check Django logs for errors
4. Test endpoint manually:
   ```bash
   curl -X POST https://58ca3475465e.ngrok-free.app/api/billing/webhook/dodo/ \
     -H "Content-Type: application/json" \
     -d '{"type": "test", "data": {}}'
   ```

### If subscription not activating:
1. Check BillingEvent records for errors
2. Verify subscription_id in webhook metadata matches your subscription UUID
3. Check webhook handler logs
4. Verify user_id is correct

## 🎯 Test Checklist

- [ ] Make test payment
- [ ] See webhook in ngrok dashboard
- [ ] Check Django logs show webhook processing
- [ ] Verify subscription becomes ACTIVE
- [ ] Check Payment record created
- [ ] Verify user has access to paid plan
- [ ] Test failed payment scenario
- [ ] Verify subscription gets cancelled on failure

## 📝 Notes

- **ngrok URL changes** when you restart ngrok - update Dodo webhook URL if needed
- **Signature verification** is disabled in DEBUG mode for easier testing
- **Idempotency** is handled - duplicate webhooks are ignored
- **Access control** - users only get access when subscription is ACTIVE

