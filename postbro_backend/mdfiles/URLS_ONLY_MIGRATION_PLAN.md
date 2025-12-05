# URLs-Only Migration Plan

## Current Daily Limit Setup

### Database Models

**Plan Model** (`accounts/models.py`):
- `max_handles` - Daily limit for username/handle analyses
- `max_urls` - Daily limit for URL lookups
- `max_analyses_per_day` - Daily limit for post suggestions

**UserUsage Model** (`accounts/models.py`):
- `handle_analyses` - Tracks username-based analyses
- `url_lookups` - Tracks URL-based analyses
- `post_suggestions` - Tracks post suggestions generated

### Backend Logic

**Usage Checking** (`accounts/utils.py`):
- `check_usage_limit()` checks different limits based on `usage_type`:
  - `'handle_analyses'` → checks `plan.max_handles` vs `usage.handle_analyses`
  - `'url_lookups'` → checks `plan.max_urls` vs `usage.url_lookups`
  - `'post_suggestions'` → checks `plan.max_analyses_per_day` vs `usage.post_suggestions`

**Analysis View** (`analysis/views.py`):
- Determines usage type based on input:
  ```python
  if username:
      usage_type = 'handle_analyses'
  elif post_urls:
      usage_type = 'url_lookups'
  ```

**Serializers** (`analysis/serializers.py`):
- `PostAnalysisRequestCreateSerializer` validates: "Either username or post_urls must be provided"
- `PostAnalysisRequest` model has both `username` and `post_urls` fields

### Frontend

**Analysis Form** (`components/app/analysis-form.tsx`):
- Toggle between `'username'` and `'url'` analysis types
- Shows date range selector for username type
- Different input fields based on type (Input for username, Textarea for URLs)

---

## Required Changes for URLs-Only Mode

### 1. Database Changes

#### A. Plan Model Updates
**File**: `postbro_backend/accounts/models.py`

**Changes**:
- ✅ Keep `max_urls` (this becomes the primary limit)
- ❌ Remove or deprecate `max_handles` (no longer needed)
- ❓ Consider renaming `max_urls` to `max_urls_per_day` for clarity (optional)
- Update default plan limits to match new pricing:
  - Free: `max_urls = 3`
  - Basic: `max_urls = 10`
  - Pro: `max_urls = 30`

**Migration needed**: Yes - update Plan records and optionally remove `max_handles` field

#### B. UserUsage Model Updates
**File**: `postbro_backend/accounts/models.py`

**Options**:
1. **Keep `handle_analyses` for historical data** (recommended)
   - Don't increment it anymore
   - Keep for analytics/reporting on old data
   
2. **Remove `handle_analyses` field** (cleaner, but loses historical data)
   - Requires migration to drop column
   - Historical usage data will be lost

**Recommendation**: Keep the field but stop using it. This preserves historical data.

#### C. PostAnalysisRequest Model Updates
**File**: `postbro_backend/analysis/models.py`

**Changes**:
- ❌ Remove `username` field (or make it nullable and never set it)
- ❌ Remove `date_range_type` field (only used with username)
- ❌ Remove `start_date` and `end_date` fields (only used with username)
- ✅ Keep `post_urls` (now required)
- ✅ Keep `display_name` (still needed for sidebar display)

**Migration needed**: Yes - make `post_urls` required, remove username-related fields

---

### 2. Backend Code Changes

#### A. Serializers
**File**: `postbro_backend/analysis/serializers.py`

**Changes**:
1. **`PostAnalysisRequestCreateSerializer`**:
   ```python
   # OLD:
   fields = ['platform', 'username', 'post_urls', 'date_range_type']
   
   # NEW:
   fields = ['platform', 'post_urls']  # Remove username, date_range_type
   
   # OLD validation:
   if not data.get('username') and not data.get('post_urls'):
       raise ValidationError("Either username or post_urls must be provided")
   
   # NEW validation:
   if not data.get('post_urls') or len(data.get('post_urls', [])) == 0:
       raise ValidationError("At least one post_url must be provided")
   ```

2. **`PostAnalysisRequestSerializer`**:
   - Remove `username` from `get_username()` method (or simplify to only use `display_name`)
   - Remove `date_range_type` from fields
   - Remove date range logic from `validate()`

#### B. Views
**File**: `postbro_backend/analysis/views.py`

**Changes**:
1. **`analyze_posts` view**:
   ```python
   # OLD:
   username = serializer.validated_data.get('username')
   post_urls = serializer.validated_data.get('post_urls', [])
   
   if username:
       usage_type = 'handle_analyses'
   elif post_urls:
       usage_type = 'url_lookups'
   else:
       return Response({'error': 'Either username or post_urls must be provided'})
   
   # NEW:
   post_urls = serializer.validated_data.get('post_urls', [])
   
   if not post_urls:
       return Response({'error': 'At least one post_url must be provided'})
   
   usage_type = 'url_lookups'  # Always URL lookups now
   
   # Remove date range calculation logic (lines 92-107)
   ```

2. **Usage limit checking**:
   - Always use `'url_lookups'` as `usage_type`
   - Check `plan.max_urls` limit

#### C. Utils
**File**: `postbro_backend/accounts/utils.py`

**Changes**:
1. **`check_usage_limit()`**:
   - Remove `'handle_analyses'` case (or keep for backward compatibility but never call it)
   - Simplify to only check `'url_lookups'` and `'post_suggestions'`

2. **`get_usage_summary()`**:
   - Remove `handle_analyses` from response (or keep for historical data display)
   - Focus on `url_lookups` and `post_suggestions`

#### D. Celery Tasks
**File**: `postbro_backend/analysis/tasks.py`

**Changes**:
- Remove username scraping logic
- Remove date range filtering logic
- Simplify to only process `post_urls` from the request

---

### 3. Frontend Changes

#### A. Analysis Form
**File**: `postbro_frontend/components/app/analysis-form.tsx`

**Changes**:
1. **Remove analysis type toggle**:
   ```typescript
   // REMOVE:
   const [analysisType, setAnalysisType] = useState<'username' | 'url'>('url')
   
   // REMOVE the toggle buttons (lines 250-278)
   ```

2. **Remove username input**:
   ```typescript
   // REMOVE:
   const [username, setUsername] = useState('')
   
   // REMOVE username Input field (lines 304-311)
   ```

3. **Remove date range selector**:
   ```typescript
   // REMOVE:
   const [dateRange, setDateRange] = useState<'last_7_days' | 'last_14_days' | 'last_30_days'>('last_7_days')
   
   // REMOVE date range Select (lines 280-299)
   ```

4. **Simplify form submission**:
   ```typescript
   // OLD:
   if (analysisType === 'username' && platform !== 'youtube' && !username.trim()) {
       toast.error('Please enter a username')
       return
   }
   if ((analysisType === 'url' || platform === 'youtube') && !urls.trim()) {
       toast.error('Please enter at least one URL')
       return
   }
   
   const data: any = { platform }
   if (analysisType === 'username' && platform !== 'youtube') {
       data.username = username.trim()
       data.date_range_type = dateRange
   } else {
       data.post_urls = urlList
   }
   
   // NEW:
   if (!urls.trim()) {
       toast.error('Please enter at least one URL')
       return
   }
   
   const urlList = urls
       .split(/[\n,]/)
       .map(url => url.trim())
       .filter(url => url.length > 0)
   
   const data = {
       platform,
       post_urls: urlList
   }
   ```

5. **Update placeholder text**:
   - Make URL textarea always visible
   - Update placeholder to show all supported platforms

#### B. API Types
**File**: `postbro_frontend/lib/api.ts`

**Changes**:
```typescript
// OLD:
interface AnalysisRequest {
    platform: 'instagram' | 'x' | 'youtube'
    username?: string
    post_urls?: string[]
    date_range_type?: 'last_7_days' | 'last_14_days' | 'last_30_days'
}

// NEW:
interface AnalysisRequest {
    platform: 'instagram' | 'x' | 'youtube'
    post_urls: string[]  // Required now
}
```

#### C. Other Frontend Components
- **`app-content.tsx`**: Remove username-related display logic
- **`app-sidebar.tsx`**: Simplify to only show `display_name` or URL
- **Landing pages**: Update copy to remove "username" mentions

---

### 4. Plan Limits Update

**File**: `postbro_backend/accounts/migrations/` (create new migration)

**Changes**:
Update existing Plan records to match new pricing:
- **Free Plan**: `max_urls = 3`
- **Basic Plan**: `max_urls = 10`
- **Pro Plan**: `max_urls = 30`

**Migration code**:
```python
from django.db import migrations

def update_plan_limits(apps, schema_editor):
    Plan = apps.get_model('accounts', 'Plan')
    
    # Update Free plan
    free_plan = Plan.objects.filter(name__icontains='free').first()
    if free_plan:
        free_plan.max_urls = 3
        free_plan.save()
    
    # Update Basic plan
    basic_plan = Plan.objects.filter(name__icontains='basic').first()
    if basic_plan:
        basic_plan.max_urls = 10
        basic_plan.save()
    
    # Update Pro plan
    pro_plan = Plan.objects.filter(name__icontains='pro').first()
    if pro_plan:
        pro_plan.max_urls = 30
        pro_plan.save()

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_create_default_plans'),  # Adjust to your latest migration
    ]
    
    operations = [
        migrations.RunPython(update_plan_limits),
    ]
```

---

## Implementation Checklist

### Phase 1: Database & Models
- [ ] Create migration to update Plan limits (3, 10, 30)
- [ ] Create migration to make `post_urls` required in `PostAnalysisRequest`
- [ ] Create migration to remove `username`, `date_range_type`, `start_date`, `end_date` from `PostAnalysisRequest`
- [ ] Decide on `handle_analyses` field (keep for history or remove)
- [ ] Update Plan model documentation

### Phase 2: Backend Logic
- [ ] Update `PostAnalysisRequestCreateSerializer` to require `post_urls`
- [ ] Update `PostAnalysisRequestSerializer` to remove username fields
- [ ] Update `analyze_posts` view to remove username logic
- [ ] Simplify `check_usage_limit()` to only handle URLs
- [ ] Update `get_usage_summary()` to focus on URL usage
- [ ] Update Celery task to remove username scraping
- [ ] Test API endpoints

### Phase 3: Frontend
- [ ] Remove analysis type toggle from form
- [ ] Remove username input field
- [ ] Remove date range selector
- [ ] Simplify form submission logic
- [ ] Update API types
- [ ] Update landing page copy
- [ ] Test form submission

### Phase 4: Testing & Cleanup
- [ ] Test with all three platforms (Instagram, X, YouTube)
- [ ] Test daily limit enforcement
- [ ] Verify usage tracking works correctly
- [ ] Check analytics still work
- [ ] Update documentation

---

## Breaking Changes

⚠️ **This is a breaking change** - existing integrations/clients that use username input will break.

**Mitigation**:
1. Add API versioning (`/api/v1/`, `/api/v2/`)
2. Or: Deprecate username endpoint first, then remove after grace period
3. Or: Accept both for a transition period, but only process URLs

---

## Rollback Plan

If issues arise:
1. Keep username fields in database (just don't use them)
2. Add feature flag: `ENABLE_USERNAME_INPUT = False`
3. Can quickly re-enable username support if needed
4. Frontend can conditionally show/hide username input based on flag

---

## Notes

- **Historical Data**: Consider keeping `username` field in `PostAnalysisRequest` as nullable for historical records
- **Display Name**: `display_name` field is still needed for sidebar display (extracted from posts)
- **Migration Order**: Update limits first, then remove fields, then update code
- **Testing**: Test with real URLs from all platforms before deploying

