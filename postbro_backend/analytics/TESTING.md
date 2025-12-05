# 🧪 Testing Analytics Tracking

## Quick Test Steps

### 1. Run Migrations (if not done)
```bash
python manage.py migrate analytics
```

### 2. Start Celery Worker (for async logging)
```bash
celery -A postbro worker -l info
```

### 3. Process a Post

**Option A: Via API (if frontend is running)**
- Make a POST request to `/api/analysis/analyze/` with:
  ```json
  {
    "platform": "x",
    "post_urls": ["https://x.com/elonmusk/status/1234567890"]
  }
  ```

**Option B: Via Django Shell**
```python
python manage.py shell

from accounts.models import User
from analysis.models import PostAnalysisRequest
from analysis.tasks import process_analysis_request

# Get a user
user = User.objects.first()

# Create analysis request
request = PostAnalysisRequest.objects.create(
    user=user,
    platform='x',
    post_urls=['https://x.com/elonmusk/status/1234567890']
)

# Process it
process_analysis_request.delay(str(request.id))
```

### 4. Check Analytics Logs

**Option A: Django Admin**
- Go to `/admin/analytics/`
- Check:
  - `APIAccessLog` - Should see the `/api/analysis/analyze/` request
  - `ExternalAPICallLog` - Should see Gemini API calls

**Option B: Django Shell**
```python
python manage.py shell

from analytics.models import APIAccessLog, ExternalAPICallLog

# Check API requests
APIAccessLog.objects.count()
APIAccessLog.objects.latest('created_at')

# Check external API calls
ExternalAPICallLog.objects.count()
ExternalAPICallLog.objects.filter(service='gemini').latest('created_at')
ExternalAPICallLog.objects.filter(service='brightdata').latest('created_at')
```

### 5. What to Look For

✅ **API Request Tracking:**
- Endpoint: `/api/analysis/analyze/`
- Method: `POST`
- Status code: `200` or `400`
- Response time in milliseconds
- User ID (if authenticated)

✅ **External API Calls:**
- **Gemini**: Should see calls with:
  - `service='gemini'`
  - `endpoint` containing `gemini-2.5-flash`
  - `response_time_ms`
  - `metadata` with token usage
  
- **BrightData**: Should see calls with:
  - `service='brightdata'`
  - `endpoint` containing BrightData API URL
  - `response_time_ms`
  - `metadata` with dataset_id

### 6. Verify Flush Manager

Check if logs are being batched and flushed:
```python
from analytics.utils import get_flush_manager

manager = get_flush_manager()
queue_size = manager.get_queue_size()
print(f"Current queue size: {queue_size}")
```

## Expected Results

After processing a post, you should see:

1. **1 API Access Log** for the `/api/analysis/analyze/` request
2. **1+ External API Call Logs** for Gemini (one per post analyzed)
3. **0+ External API Call Logs** for BrightData (if scraping was needed)

## Troubleshooting

**No logs appearing?**
- Check Celery worker is running
- Check `ANALYTICS_ENABLED=True` in config
- Check logs in Django admin after a few seconds (flush delay)

**Logs appearing but incomplete?**
- Check Celery worker logs for errors
- Check database connection
- Verify middleware is in `MIDDLEWARE` list

**Cost estimates showing?**
- Should be `None` (cost tracking removed)






