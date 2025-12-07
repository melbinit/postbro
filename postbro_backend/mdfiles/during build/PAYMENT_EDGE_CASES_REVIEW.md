# Payment Edge Cases Review

## Current Implementation Status

### ✅ **Already Handled**

1. **Small → Big Upgrade (before month ends)**
   - ✅ Immediate activation with prorated credit
   - ✅ Old subscription cancelled after new payment succeeds
   - ✅ Refund processed for remaining days

2. **Big → Small Downgrade (paid to paid)**
   - ✅ Scheduled at period end
   - ✅ User keeps current plan until period ends
   - ✅ New subscription created at period end

3. **Multiple Downgrades**
   - ✅ Updates `downgrade_to_plan` to latest target

4. **Upgrade During Scheduled Downgrade**
   - ✅ Cancels scheduled downgrade
   - ✅ Processes upgrade immediately

5. **Cancel During Scheduled Downgrade**
   - ✅ Clears `downgrade_to_plan`
   - ✅ Cancels at period end (no new plan)

---

## ⚠️ **Issues Found**

### 1. **Downgrade to Free Plan** ❌

**Current Behavior:**
- Line 96-127: Treated like any downgrade (scheduled at period end)
- Task (line 121-131): Activates free plan immediately if target is free

**Problem:**
- Free plans don't need payment, so scheduling is unnecessary
- User should get free plan immediately (or at least not wait until period end)
- This is different from paid downgrades

**Recommended Fix:**
- **Option A (Industry Standard):** Downgrade to free should be **immediate**
  - User keeps paid plan features until period ends
  - But account shows "Free plan" immediately
  - Actually activates free plan at period end
  
- **Option B (More Generous):** Downgrade to free is **scheduled** but user gets free plan features immediately
  - User loses paid features but gets free plan access immediately
  - Paid subscription ends at period end
  
- **Option C (Current behavior but better UX):** Keep scheduled but handle differently
  - Still schedule at period end
  - But make it clear it's free (no payment needed)
  - Frontend should show "Downgrading to Free on [date]"

**Recommendation: Option A** (Industry standard - Stripe, Paddle do this)

---

### 2. **Cancelled Subscription → Free Plan Assignment** ⚠️

**Current Behavior:**
- Line 348-353: Can't cancel free plan
- Line 376-380: Marks as CANCELING (no `downgrade_to_plan`)
- Line 384-385: Comment says "Free plan will be assigned when subscription expires (can be done via scheduled task later)"
- **BUT:** No task actually assigns free plan after cancellation!

**Problem:**
- When user cancels paid subscription, they stay on paid plan until period ends
- After period ends, subscription becomes EXPIRED but no free plan is assigned
- User has no active subscription after cancellation period ends

**Recommended Fix:**
- Create a task to process expired cancellations
- When `CANCELING` subscription expires with no `downgrade_to_plan`, assign free plan
- Or: Handle in `process_scheduled_downgrades` task

---

### 3. **Free Plan Subscription Handling** ⚠️

**Current Behavior:**
- Line 140-148: Free plan activates immediately when subscribing
- But what if user is on paid plan and subscribes to free?
  - Line 79: This would be detected as downgrade
  - Line 96: Would schedule downgrade
  - But free plan doesn't need scheduling!

**Problem:**
- Subscribe to free plan while on paid plan = treated as downgrade
- This is correct, but should we handle free plan downgrades differently?

**Recommendation:**
- Keep current behavior (treat as downgrade)
- But handle it specially (immediate free plan, see Issue #1)

---

### 4. **Upgrade from Free to Paid** ✅

**Current Behavior:**
- Line 140-148: Free plan activates immediately (no checkout)
- If user has free plan and subscribes to paid:
  - Line 79: Detected as upgrade (paid > free)
  - Line 195-200: Creates checkout session
  - ✅ This is correct

**Status:** ✅ No issues

---

### 5. **Payment Failure for Downgraded Plan** ⚠️

**Current Behavior:**
- Task creates PENDING subscription for downgraded paid plan
- Creates checkout session
- If payment fails:
  - Webhook will mark subscription as FAILED
  - User has no active subscription
  - ❌ User loses access completely!

**Problem:**
- If downgrade payment fails, user should:
  - Keep old plan? No, period ended
  - Get free plan? Probably
  - Or retry payment? Yes, with fallback to free

**Recommended Fix:**
- If downgrade payment fails after period end:
  - Mark subscription as FAILED
  - Assign free plan as fallback
  - Notify user about payment failure
  - Allow retry with checkout link

---

## 📋 **Edge Cases Summary**

| Scenario | Current Status | Issue | Recommendation |
|----------|---------------|-------|----------------|
| Small → Big Upgrade | ✅ Working | None | Keep as is |
| Big → Small Downgrade (paid→paid) | ✅ Working | None | Keep as is |
| Paid → Free Downgrade | ⚠️ Partial | Scheduled unnecessarily | Make immediate OR schedule but clarify |
| Free → Paid Upgrade | ✅ Working | None | Keep as is |
| Upgrade during downgrade | ✅ Working | None | Keep as is |
| Multiple downgrades | ✅ Working | None | Keep as is |
| Cancel subscription | ⚠️ Partial | No free plan assignment | Add task to assign free plan |
| Payment failure (downgrade) | ❌ Missing | User loses access | Assign free plan as fallback |
| Cancel free plan | ✅ Blocked | None | Keep as is |

---

## 🔧 **Recommended Fixes**

### Fix 1: Handle Downgrade to Free Plan Specially

```python
# In subscribe_to_plan, around line 96
if is_downgrade:
    # Special case: Downgrade to free plan = immediate (no payment needed)
    if plan.price == 0:
        # Mark current subscription as CANCELING
        current_subscription.status = Subscription.Status.CANCELING
        current_subscription.downgrade_to_plan = plan
        
        # BUT: Also create free subscription immediately (user gets free plan now)
        # Paid subscription ends at period end
        free_subscription = Subscription.objects.create(
            user=request.user,
            plan=plan,
            status=Subscription.Status.ACTIVE,  # Activate immediately
            start_date=timezone.now(),
            end_date=None,  # Free plans don't expire
            payment_provider=Subscription.PaymentProvider.DODO
        )
        
        return Response({
            'message': f'Downgraded to {plan.name} plan. Your {current_subscription.plan.name} plan will end on {current_subscription.end_date.strftime("%B %d, %Y")}, but you can use {plan.name} features now.',
            'subscription': SubscriptionSerializer(free_subscription).data,
            'downgrade': True,
            'immediate': True  # Flag for frontend
        })
    
    # Regular paid downgrade (scheduled at period end)
    # ... existing code ...
```

### Fix 2: Process Expired Cancellations

```python
# In billing/tasks.py, add to process_scheduled_downgrades or create new task
@shared_task
def process_expired_cancellations():
    """Assign free plan to users whose cancellations have expired"""
    now = timezone.now()
    
    # Find CANCELING subscriptions with no downgrade_to_plan that have expired
    expired_cancellations = Subscription.objects.filter(
        status=Subscription.Status.CANCELING,
        end_date__lte=now,
        downgrade_to_plan__isnull=True
    ).select_related('user')
    
    for subscription in expired_cancellations:
        # Get or create free plan
        free_plan = Plan.objects.filter(price=0, is_active=True).first()
        if not free_plan:
            logger.error("No free plan found - cannot assign to expired cancellations")
            continue
        
        # Check if user already has free plan
        existing_free = Subscription.objects.filter(
            user=subscription.user,
            plan=free_plan,
            status=Subscription.Status.ACTIVE
        ).first()
        
        if existing_free:
            # User already has free plan, just mark old as CANCELLED
            subscription.status = Subscription.Status.CANCELLED
            subscription.save()
            continue
        
        # Mark old subscription as CANCELLED
        subscription.status = Subscription.Status.CANCELLED
        subscription.save()
        
        # Create free plan subscription
        free_subscription = Subscription.objects.create(
            user=subscription.user,
            plan=free_plan,
            status=Subscription.Status.ACTIVE,
            start_date=now,
            payment_provider=Subscription.PaymentProvider.DODO
        )
        
        logger.info(f"✅ Assigned free plan to {subscription.user.email} after cancellation expired")
```

### Fix 3: Handle Payment Failure for Downgrades

```python
# In billing/webhook_handlers.py, in handle_payment_failed
# Check if this is a downgrade payment failure
if subscription_id:
    subscription = Subscription.objects.get(id=subscription_id, user=user)
    
    # Check if this is a downgrade (has is_downgrade flag or no old_subscription_id)
    metadata = payment_data.get('metadata', {})
    is_downgrade_payment = metadata.get('is_downgrade') == 'true'
    
    if is_downgrade_payment and subscription.status == Subscription.Status.PENDING:
        # Downgrade payment failed - assign free plan as fallback
        from accounts.models import Plan
        free_plan = Plan.objects.filter(price=0, is_active=True).first()
        
        if free_plan:
            subscription.plan = free_plan
            subscription.status = Subscription.Status.ACTIVE
            subscription.save()
            
            logger.warning(f"⚠️ Downgrade payment failed for {user.email}, assigned free plan as fallback")
            # TODO: Send notification email
```

---

## 🎯 **Priority**

1. **HIGH:** Fix expired cancellations (users lose access after cancellation period)
2. **MEDIUM:** Handle downgrade to free plan (better UX)
3. **MEDIUM:** Handle payment failure for downgrades (fallback to free)

---

## ❓ **Questions for Product Decision**

1. **Downgrade to Free:** Immediate or scheduled?
   - Immediate: User gets free plan now, paid ends at period end (recommended)
   - Scheduled: User keeps paid plan until period ends, then gets free

2. **Payment Failure After Downgrade:** What happens?
   - Assign free plan immediately (recommended)
   - Keep old plan? (confusing)
   - Retry payment? (with free fallback)

3. **Cancelled Subscription:** After period ends, automatically assign free?
   - Yes (recommended - standard SaaS behavior)
   - No (user needs to manually subscribe to free)

