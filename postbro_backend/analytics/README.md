# Analytics App - Phase 1 Complete ✅

## What Was Built

### 1. Database Models

#### `APIAccessLog`
- Tracks every API request
- Fields: user, endpoint, method, status_code, response_time_ms, ip_address, user_agent, request/response sizes, query_params, error_message
- 4 strategic indexes for fast queries

#### `AuthenticationLog`
- Tracks all auth events (signup, login, logout, failures)
- Fields: user, event_type, ip_address, user_agent, success, error_message, metadata
- 4 indexes for security monitoring

#### `ExternalAPICallLog`
- Tracks external API calls (Gemini, BrightData, Supabase)
- Fields: user, service, endpoint, method, status_code, response_time_ms, cost_estimate, request/response sizes, metadata
- 3 indexes for cost tracking

### 2. Configuration System

**File**: `analytics/config.py`

- Centralized configuration
- Environment variable support
- Configurable flush strategy (time/count/hybrid)
- Endpoint filtering
- Sampling support
- Performance thresholds

### 3. Django Admin

- Full admin interface for all 3 models
- Optimized querysets (select_related)
- Search and filtering
- Date hierarchy
- Read-only fields protection

### 4. App Integration

- Added to `INSTALLED_APPS`
- Custom `AnalyticsConfig` app config
- Ready for migrations

## Phase 2 Complete ✅

### Celery Tasks (`analytics/tasks.py`)

1. **`flush_api_logs`** - Bulk insert API logs (batched)
2. **`log_auth_event`** - Immediate auth event logging
3. **`log_external_api_call`** - External API call logging
4. **`queue_api_log`** - Lightweight queue task

### Flush Manager (`analytics/utils.py`)

- **`LogFlushManager`** - Thread-safe batch processing
  - Time-based flush (every N seconds)
  - Count-based flush (when queue reaches N)
  - Hybrid strategy (both)
  - Automatic background timer
  - Graceful shutdown handling

### Utility Functions

- `get_client_ip()` - Extract IP from request (handles proxies)
- `get_request_size()` - Get request body size
- `get_response_size()` - Get response body size
- `sanitize_query_params()` - Remove sensitive data

## Phase 3 Complete ✅

### Middleware (`analytics/middleware.py`)

**`APITrackingMiddleware`** - Non-blocking API request tracking
- Positioned after `AuthenticationMiddleware` to access `request.user`
- Tracks all API requests asynchronously via Celery
- Configurable endpoint exclusions
- Request/response size tracking
- Error tracking (including exceptions)
- Sampling support for high-traffic endpoints
- IP address extraction (handles proxies/load balancers)
- Query parameter sanitization

### Auth Tracking Integration (`accounts/views.py`)

**Integrated tracking for:**
- ✅ `signup` - Success and failure
- ✅ `login` - Success and failure (login_failed event type)
- ✅ `logout` - Success
- ✅ `reset_password` - Password reset requests

**Features:**
- Tracks user ID, IP address, user agent
- Success/failure status
- Error messages for failures
- Metadata (email, full_name, etc.)
- Non-blocking (doesn't affect auth flow)

### External API Tracking

#### Gemini Service (`analysis/services/gemini_service.py`)
- ✅ Tracks all Gemini API calls
- ✅ Records response time, status code, cost estimate
- ✅ Tracks token usage and request/response sizes
- ✅ Logs errors (rate limits, API failures)
- ✅ Metadata includes task_id, platform, model, usage info

#### BrightData Scraper (`social/scrapers/brightdata.py`)
- ✅ Tracks all BrightData API calls
- ✅ Records response time, status code
- ✅ Tracks request/response sizes
- ✅ Logs errors (timeouts, HTTP errors)
- ✅ Metadata includes dataset_id, operation type
- ✅ Supports user_id context (when available)

### Settings Integration (`postbro/settings.py`)

- ✅ Added `APITrackingMiddleware` to `MIDDLEWARE`
- ✅ Positioned correctly (after AuthenticationMiddleware)
- ✅ Analytics app already in `INSTALLED_APPS`

## 🎯 What's Now Being Tracked

1. **Every API Request:**
   - Endpoint, method, status code
   - Response time (milliseconds)
   - User (if authenticated)
   - IP address, user agent
   - Request/response sizes
   - Query parameters (sanitized)
   - Error messages

2. **Every Authentication Event:**
   - Signup (success/failure)
   - Login (success/failure)
   - Logout
   - Password reset requests

3. **Every External API Call:**
   - Gemini API calls (with cost estimates)
   - BrightData API calls
   - Response times, status codes, errors

## 🚀 Performance

- **Non-blocking**: All logging is async via Celery
- **Batched**: API logs are batched for efficiency
- **Configurable**: Can be disabled/enabled via config
- **Sampling**: Supports sampling for high-traffic endpoints
- **Error-tolerant**: Logging failures don't affect main functionality

## 📊 Next Steps

1. Run migrations: `python manage.py migrate analytics`
2. Start Celery worker: `celery -A postbro worker -l info`
3. Monitor logs in Django admin: `/admin/analytics/`
4. Query analytics data for insights

## 🔧 Configuration

All settings in `analytics/config.py` can be overridden via environment variables:

```bash
ANALYTICS_ENABLED=True
ANALYTICS_FLUSH_STRATEGY=hybrid
ANALYTICS_FLUSH_INTERVAL_SECONDS=10
ANALYTICS_FLUSH_COUNT_THRESHOLD=100
```

## Usage

```python
from analytics.models import APIAccessLog, AuthenticationLog, ExternalAPICallLog
from analytics.config import get_analytics_config, should_track_endpoint

# Get configuration
config = get_analytics_config()

# Check if endpoint should be tracked
if should_track_endpoint('/api/analysis/analyze/'):
    # Track it
    pass
```

## Environment Variables

```bash
ANALYTICS_ENABLED=True
ANALYTICS_FLUSH_STRATEGY=hybrid  # time, count, or hybrid
ANALYTICS_FLUSH_INTERVAL_SECONDS=10
ANALYTICS_FLUSH_COUNT_THRESHOLD=100
ANALYTICS_ENABLE_SAMPLING=False
ANALYTICS_SAMPLING_RATE=0.1
```

## Database Migration

Run migrations:
```bash
python manage.py migrate analytics
```

