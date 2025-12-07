# Downgrade Implementation - Standard SaaS Behavior

## Overview

This implementation follows industry-standard SaaS downgrade behavior used by major platforms (Stripe, Paddle, LemonSqueezy, etc.).

## Key Principles

1. **Downgrades NEVER take effect immediately**
2. **User keeps current plan until billing period ends**
3. **No refunds, no proration for downgrades**
4. **New plan starts only on next renewal date**

## Implementation Details

### Database Changes

- Added `downgrade_to_plan` field to `Subscription` model
- Stores the target plan for scheduled downgrades
- Only set when `status = CANCELING` for downgrades

### Downgrade Flow

When user clicks "Downgrade to [Plan]":

1. **Mark current subscription as `CANCELING`**
   - Status changes to `CANCELING`
   - `downgrade_to_plan` is set to target plan
   - `end_date` remains unchanged (user keeps access until then)

2. **User keeps current plan features**
   - `get_user_subscription()` returns `CANCELING` subscriptions
   - User retains all current plan features until `end_date`

3. **Frontend shows:**
   - Current plan: [Current Plan Name]
   - Status: "Downgrading to [New Plan] on [end_date]"
   - End date: When current period ends

4. **At period end (via Celery Beat task):**
   - Old subscription marked as `CANCELLED`
   - Dodo subscription cancelled (if exists)
   - New subscription created for downgraded plan
   - For paid plans: Checkout session created (user pays for new plan)
   - For free plans: Activated immediately

### Edge Cases Handled

1. **Multiple downgrades:** Updates `downgrade_to_plan` to latest target
2. **Upgrade during scheduled downgrade:** Cancels downgrade, processes upgrade immediately
3. **Cancel during scheduled downgrade:** Clears `downgrade_to_plan`, cancels at period end
4. **Payment failure for downgraded plan:** Subscription stays `PENDING`, can be retried

### Periodic Task

**File:** `billing/tasks.py`
**Task:** `process_scheduled_downgrades`
**Schedule:** Daily at midnight UTC (via Celery Beat)

Processes all subscriptions where:
- `status = CANCELING`
- `end_date <= now`
- `downgrade_to_plan` is set

### Example Scenario

**User on Pro ($59) plan, downgrades to Starter ($29) after 2 days:**

1. **Day 1:** User subscribes to Pro ($59)
   - Subscription: `ACTIVE`, Pro plan
   - End date: Day 31

2. **Day 3:** User downgrades to Starter
   - Subscription: `CANCELING`, Pro plan
   - `downgrade_to_plan`: Starter
   - End date: Day 31 (unchanged)
   - User keeps Pro features for 28 more days

3. **Day 31:** Celery Beat task runs
   - Old subscription: `CANCELLED`
   - New subscription: `PENDING` (Starter)
   - Checkout session created for $29 payment
   - User completes payment → Subscription becomes `ACTIVE`

## API Response for Downgrade

```json
{
  "message": "Downgrade scheduled. You will switch to Starter plan at the end of your current billing period (January 31, 2025). You will continue to have access to Pro features until then.",
  "subscription": {
    "id": "...",
    "plan": { "name": "Pro", "price": 59 },
    "status": "canceling",
    "end_date": "2025-01-31T00:00:00Z",
    "downgrade_to_plan": { "name": "Starter", "price": 29 }
  },
  "downgrade": true,
  "scheduled_at": "2025-01-31T00:00:00Z",
  "current_plan": "Pro",
  "downgrade_to_plan": "Starter"
}
```

## Frontend Display

Show current subscription with:
- **Current Plan:** Pro ($59/month)
- **Status:** "Downgrading to Starter on January 31, 2025"
- **Features:** User keeps Pro features until end date
- **End Date:** January 31, 2025

## Testing

To test the downgrade flow:

1. Create a subscription with an end_date in the past
2. Mark it as `CANCELING` with `downgrade_to_plan` set
3. Run the task manually:
   ```bash
   docker compose exec backend python manage.py shell
   >>> from billing.tasks import process_scheduled_downgrades
   >>> process_scheduled_downgrades()
   ```

## Notes

- Celery Beat must be running for automatic processing
- Checkout sessions for downgrades are created but user must complete payment
- In production, consider sending email notifications with checkout links
- Free plan downgrades activate immediately (no payment needed)

