# Enterprise-Level Analytics & Tracking Implementation Plan

## 📋 Overview

This document outlines the implementation plan for enterprise-level request tracking, authentication logging, and API call monitoring in PostBro. The system is designed to be **non-blocking**, **scalable**, and **performance-optimized**.

---

## 🎯 Goals

1. **Track all API requests** - Every endpoint hit, with metadata
2. **Track authentication events** - Signups, logins, logouts, failures
3. **Track external API calls** - Gemini, BrightData, Supabase usage
4. **Zero performance impact** - Async logging via Celery
5. **Analytics-ready** - Structured data for business intelligence
6. **Configurable** - Easy to adjust flush strategies, sampling rates, etc.

---

## 📊 Data Models

### 1. `APIAccessLog` Model

**Purpose**: Track every API request to our backend

**Fields**:
```python
- id: UUID (primary key)
- user: ForeignKey(User, null=True)  # null for unauthenticated requests
- endpoint: CharField(max_length=255)  # e.g., '/api/analysis/analyze/'
- method: CharField(max_length=10)  # GET, POST, PUT, DELETE, etc.
- status_code: IntegerField  # 200, 404, 500, etc.
- response_time_ms: IntegerField  # Latency in milliseconds
- ip_address: GenericIPAddressField  # Client IP
- user_agent: TextField  # Browser/client info
- request_size_bytes: IntegerField(null=True)  # Request body size
- response_size_bytes: IntegerField(null=True)  # Response body size
- query_params: JSONField(default=dict)  # URL query parameters
- error_message: TextField(null=True, blank=True)  # If error occurred
- created_at: DateTimeField(auto_now_add=True)
```

**Indexes**:
- `user_id` + `created_at` (for user activity queries)
- `endpoint` + `created_at` (for endpoint analytics)
- `status_code` + `created_at` (for error tracking)
- `created_at` (for time-based queries)

---

### 2. `AuthenticationLog` Model

**Purpose**: Track all authentication events

**Fields**:
```python
- id: UUID (primary key)
- user: ForeignKey(User, null=True)  # null for failed attempts
- event_type: CharField(choices=[
    ('signup', 'Sign Up'),
    ('login', 'Login'),
    ('logout', 'Logout'),
    ('login_failed', 'Login Failed'),
    ('token_refresh', 'Token Refresh'),
    ('password_reset', 'Password Reset'),
])
- ip_address: GenericIPAddressField
- user_agent: TextField
- success: BooleanField  # True if successful
- error_message: TextField(null=True, blank=True)  # Error details if failed
- metadata: JSONField(default=dict)  # Additional context
- created_at: DateTimeField(auto_now_add=True)
```

**Indexes**:
- `user_id` + `created_at`
- `event_type` + `created_at`
- `success` + `created_at` (for security monitoring)
- `ip_address` + `created_at` (for abuse detection)

---

### 3. `ExternalAPICallLog` Model

**Purpose**: Track calls to external APIs (Gemini, BrightData, Supabase)

**Fields**:
```python
- id: UUID (primary key)
- user: ForeignKey(User, null=True)  # User who triggered the call
- service: CharField(choices=[
    ('gemini', 'Google Gemini'),
    ('brightdata', 'BrightData'),
    ('supabase', 'Supabase'),
])
- endpoint: CharField(max_length=500)  # External API endpoint
- method: CharField(max_length=10)  # GET, POST, etc.
- status_code: IntegerField  # HTTP status from external API
- response_time_ms: IntegerField  # Latency
- cost_estimate: DecimalField(max_digits=10, decimal_places=6, null=True)  # Estimated cost in USD
- request_size_bytes: IntegerField(null=True)
- response_size_bytes: IntegerField(null=True)
- error_message: TextField(null=True, blank=True)
- metadata: JSONField(default=dict)  # Additional context (model used, tokens, etc.)
- created_at: DateTimeField(auto_now_add=True)
```

**Indexes**:
- `user_id` + `service` + `created_at`
- `service` + `created_at` (for service-level analytics)
- `created_at` (for time-based queries)

---

## 🏗️ Architecture

### Component Structure

```
postbro_backend/
├── analytics/
│   ├── __init__.py
│   ├── models.py              # APIAccessLog, AuthenticationLog, ExternalAPICallLog
│   ├── middleware.py          # APITrackingMiddleware
│   ├── tasks.py               # Celery tasks for async logging
│   ├── decorators.py          # @track_external_api decorator
│   ├── utils.py               # Helper functions, flush logic
│   ├── config.py              # Configuration settings
│   └── serializers.py         # For analytics API (optional)
```

---

## 🔄 Flush Strategy (Configurable)

### Strategy Options

**1. Time-Based Flush**
- Flush logs every N seconds (default: 5-10 seconds)
- Ensures logs are written even during low traffic
- Prevents data loss

**2. Count-Based Flush**
- Flush when queue reaches N logs (default: 50-100)
- Efficient for high traffic (bulk inserts)
- Reduces database writes

**3. Hybrid (Recommended)**
- Flush when **EITHER**:
  - Timer expires (5-10 seconds) **OR**
  - Queue reaches threshold (50-100 logs)
- Best of both worlds

### Configuration

```python
# analytics/config.py
ANALYTICS_CONFIG = {
    'FLUSH_STRATEGY': 'hybrid',  # 'time', 'count', or 'hybrid'
    'FLUSH_INTERVAL_SECONDS': 10,  # For time-based
    'FLUSH_COUNT_THRESHOLD': 100,  # For count-based
    'ENABLE_SAMPLING': False,  # Enable sampling for high-traffic endpoints
    'SAMPLING_RATE': 0.1,  # 10% of requests (if enabled)
    'SKIP_ENDPOINTS': [  # Endpoints to skip tracking
        '/health/',
        '/health/live/',
        '/health/ready/',
        '/static/',
        '/media/',
    ],
    'TRACK_AUTHENTICATED_ONLY': False,  # Only track authenticated requests
}
```

---

## 🔧 Implementation Components

### 1. Middleware: `APITrackingMiddleware`

**Location**: `analytics/middleware.py`

**Purpose**: Capture all API requests automatically

**Flow**:
1. Request comes in → Middleware captures metadata
2. Start timer for response time
3. Request processed by view
4. Response generated
5. Middleware calculates response time
6. Queue log entry to Celery task (non-blocking)
7. Return response immediately

**What to Capture**:
- User (from `request.user`)
- Endpoint (from `request.path`)
- Method (from `request.method`)
- IP address (from `request.META.get('REMOTE_ADDR')`)
- User agent (from `request.META.get('HTTP_USER_AGENT')`)
- Query params (from `request.GET`)
- Request size (from `request.META.get('CONTENT_LENGTH')`)
- Response status code
- Response time (calculated)
- Response size (from `len(response.content)`)
- Error message (if exception occurred)

**Position in Middleware Stack**:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # ← After auth
    'analytics.middleware.APITrackingMiddleware',  # ← Our middleware here
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]
```

---

### 2. Celery Tasks: Async Logging

**Location**: `analytics/tasks.py`

#### Task 1: `queue_api_log`

**Purpose**: Queue API log entry (non-blocking)

```python
@shared_task
def queue_api_log(log_data: dict):
    """
    Queue API log entry for batch processing.
    Adds to in-memory queue, triggers flush if threshold reached.
    """
    # Add to queue
    # Check if flush needed (count or time)
    # Trigger flush_task if needed
```

#### Task 2: `flush_api_logs`

**Purpose**: Bulk insert API logs to database

```python
@shared_task
def flush_api_logs(log_entries: list):
    """
    Bulk insert API logs to database.
    Uses bulk_create for efficiency.
    """
    # Bulk create APIAccessLog objects
    # Handle errors gracefully
```

#### Task 3: `log_auth_event`

**Purpose**: Log authentication events immediately (critical)

```python
@shared_task
def log_auth_event(event_data: dict):
    """
    Log authentication event immediately.
    These are critical and should not be batched.
    """
    # Create AuthenticationLog immediately
    # No batching for security events
```

#### Task 4: `log_external_api_call`

**Purpose**: Log external API calls

```python
@shared_task
def log_external_api_call(call_data: dict):
    """
    Log external API call (Gemini, BrightData, etc.)
    Can be batched or immediate based on config.
    """
    # Create ExternalAPICallLog
    # Batch if configured, otherwise immediate
```

---

### 3. Flush Manager: `LogFlushManager`

**Location**: `analytics/utils.py`

**Purpose**: Manage flush strategy logic

**Features**:
- In-memory queue for API logs
- Timer-based flush (thread-safe)
- Count-based flush trigger
- Bulk insert optimization
- Error handling and retry logic

**Implementation**:
```python
class LogFlushManager:
    """
    Manages flushing of API logs with configurable strategy.
    Thread-safe, handles both time and count-based flushing.
    """
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()
        self.last_flush = time.time()
        self.config = get_analytics_config()
    
    def add_log(self, log_data: dict):
        """Add log to queue, trigger flush if needed"""
        with self.lock:
            self.queue.append(log_data)
            if len(self.queue) >= self.config['FLUSH_COUNT_THRESHOLD']:
                self._trigger_flush()
    
    def _trigger_flush(self):
        """Flush queue to database via Celery"""
        if not self.queue:
            return
        logs_to_flush = self.queue.copy()
        self.queue.clear()
        self.last_flush = time.time()
        flush_api_logs.delay(logs_to_flush)
    
    def start_timer(self):
        """Start timer-based flush (runs in background thread)"""
        # Timer thread that checks every N seconds
```

---

### 4. Decorator: `@track_external_api`

**Location**: `analytics/decorators.py`

**Purpose**: Easy tracking of external API calls

**Usage**:
```python
from analytics.decorators import track_external_api

@track_external_api(service='gemini')
def call_gemini_api(prompt):
    # API call code
    response = gemini_client.generate_content(...)
    return response
```

**What it does**:
- Wraps function execution
- Captures start/end time
- Captures request/response size
- Calculates cost (if applicable)
- Queues log entry

---

## 📍 Integration Points

### Authentication Tracking

**Files to Modify**:
1. `accounts/views.py`
   - `signup()` - Track signup event
   - `login()` - Track login event (success/failure)
   - `logout()` - Track logout event
   - `reset_password()` - Track password reset

2. `accounts/authentication.py`
   - `SupabaseAuthentication.authenticate()` - Track token validation

**Implementation**:
```python
from analytics.tasks import log_auth_event

# In login view
log_auth_event.delay({
    'user_id': str(user.id) if user else None,
    'event_type': 'login',
    'ip_address': get_client_ip(request),
    'user_agent': request.META.get('HTTP_USER_AGENT'),
    'success': True,
    'error_message': None,
})
```

---

### External API Tracking

**Files to Modify**:
1. `analysis/services/gemini_service.py`
   - Wrap `generate_content()` calls
   - Track: model used, tokens, cost, latency

2. `social/scrapers/brightdata.py`
   - Wrap scraping calls
   - Track: endpoint, response time, cost

3. `accounts/supabase_client.py` (if needed)
   - Track Supabase API calls

**Implementation**:
```python
from analytics.decorators import track_external_api

@track_external_api(service='gemini', calculate_cost=True)
def call_gemini(prompt):
    # Existing code
    response = client.generate_content(...)
    return response
```

---

## ⚡ Performance Optimizations

### 1. Async Processing
- **All logs go to Celery queue** (non-blocking)
- Request returns immediately
- Background worker processes logs

### 2. Bulk Inserts
- Batch API logs (50-100 at a time)
- Single database transaction
- Reduces DB overhead by 90%+

### 3. Selective Tracking
- Skip health checks (`/health/`)
- Skip static files (`/static/`, `/media/`)
- Configurable per endpoint

### 4. Sampling (Optional)
- For high-traffic endpoints, sample 10-50%
- Always log errors (100% error logging)
- Configurable per endpoint

### 5. Database Indexes
- Strategic indexes for common queries
- Partition by date (future optimization)

### 6. Memory Management
- Queue size limits (prevent memory leaks)
- Automatic flush on queue full

---

## 📈 Analytics Queries Enabled

### User Activity
- Requests per user per day
- Most used endpoints per user
- Peak usage times
- User journey analysis

### API Performance
- Average response time per endpoint
- Error rates per endpoint
- Slowest endpoints
- Throughput metrics

### Business Metrics
- Daily active users (DAU)
- Signups per day
- Login frequency
- Feature adoption rates

### Cost Tracking
- External API costs per user
- Cost per analysis
- Service-level cost breakdown

### Security
- Failed login attempts
- Suspicious IP addresses
- Rate limiting effectiveness

---

## 🔄 Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create `analytics` app
- [ ] Create database models (`APIAccessLog`, `AuthenticationLog`, `ExternalAPICallLog`)
- [ ] Run migrations
- [ ] Create configuration system (`analytics/config.py`)

### Phase 2: Core Infrastructure (Week 1)
- [ ] Create `LogFlushManager` with configurable flush strategy
- [ ] Create Celery tasks (`queue_api_log`, `flush_api_logs`, `log_auth_event`)
- [ ] Test flush strategies (time-based, count-based, hybrid)
- [ ] Add error handling and retry logic

### Phase 3: Middleware (Week 2)
- [ ] Create `APITrackingMiddleware`
- [ ] Integrate into middleware stack
- [ ] Test performance impact (<5ms overhead)
- [ ] Add endpoint filtering (skip health checks)

### Phase 4: Authentication Tracking (Week 2)
- [ ] Integrate into `accounts/views.py` (signup, login, logout)
- [ ] Integrate into `accounts/authentication.py`
- [ ] Test authentication event logging
- [ ] Verify security events are captured

### Phase 5: External API Tracking (Week 2)
- [ ] Create `@track_external_api` decorator
- [ ] Integrate into Gemini service
- [ ] Integrate into BrightData scraper
- [ ] Test external API call logging

### Phase 6: Testing & Optimization (Week 3)
- [ ] Load testing (verify no performance degradation)
- [ ] Test flush strategies under different traffic patterns
- [ ] Verify data accuracy
- [ ] Optimize database queries
- [ ] Add monitoring/alerting

### Phase 7: Analytics API (Optional - Week 3)
- [ ] Create analytics endpoints (if needed)
- [ ] Add admin interface for viewing logs
- [ ] Create dashboards/queries

---

## 🧪 Testing Strategy

### Unit Tests
- Test flush manager logic
- Test middleware capture
- Test decorator functionality
- Test error handling

### Integration Tests
- Test end-to-end logging flow
- Test bulk insert performance
- Test under load (1000+ requests/sec)

### Performance Tests
- Measure overhead per request (<5ms target)
- Measure database write performance
- Test memory usage under load

---

## 📊 Configuration Reference

### Environment Variables

```bash
# Analytics Configuration
ANALYTICS_ENABLED=True
ANALYTICS_FLUSH_STRATEGY=hybrid  # time, count, or hybrid
ANALYTICS_FLUSH_INTERVAL_SECONDS=10
ANALYTICS_FLUSH_COUNT_THRESHOLD=100
ANALYTICS_ENABLE_SAMPLING=False
ANALYTICS_SAMPLING_RATE=0.1  # 10%
ANALYTICS_TRACK_AUTHENTICATED_ONLY=False
```

### Code Configuration

```python
# analytics/config.py
ANALYTICS_CONFIG = {
    'ENABLED': os.getenv('ANALYTICS_ENABLED', 'True') == 'True',
    'FLUSH_STRATEGY': os.getenv('ANALYTICS_FLUSH_STRATEGY', 'hybrid'),
    'FLUSH_INTERVAL_SECONDS': int(os.getenv('ANALYTICS_FLUSH_INTERVAL_SECONDS', '10')),
    'FLUSH_COUNT_THRESHOLD': int(os.getenv('ANALYTICS_FLUSH_COUNT_THRESHOLD', '100')),
    'ENABLE_SAMPLING': os.getenv('ANALYTICS_ENABLE_SAMPLING', 'False') == 'True',
    'SAMPLING_RATE': float(os.getenv('ANALYTICS_SAMPLING_RATE', '0.1')),
    'SKIP_ENDPOINTS': [
        '/health/',
        '/health/live/',
        '/health/ready/',
        '/static/',
        '/media/',
        '/admin/',
    ],
    'TRACK_AUTHENTICATED_ONLY': os.getenv('ANALYTICS_TRACK_AUTHENTICATED_ONLY', 'False') == 'True',
}
```

---

## 🚀 Deployment Considerations

### Database
- Ensure indexes are created
- Monitor table growth
- Plan for partitioning (if needed later)

### Celery
- Ensure Celery worker is running
- Monitor queue size
- Set up alerts for queue backlog

### Monitoring
- Track flush frequency
- Monitor database write performance
- Alert on errors

---

## 📝 Notes

- **All logging is async** - Zero blocking
- **Configurable flush strategy** - Easy to adjust
- **Bulk inserts** - Efficient database usage
- **Error handling** - Graceful degradation
- **Scalable** - Handles high traffic
- **Analytics-ready** - Structured for BI tools

---

## ✅ Success Criteria

1. ✅ All API requests logged
2. ✅ All authentication events logged
3. ✅ All external API calls logged
4. ✅ <5ms overhead per request
5. ✅ Configurable flush strategy working
6. ✅ No performance degradation under load
7. ✅ Data accurate and queryable

---

**Status**: 📋 Planning Complete - Ready for Implementation

**Next Step**: Begin Phase 1 - Create analytics app and models

