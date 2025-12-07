
### Key Components
1. **Authentication**: Clerk-based JWT authentication
2. **Async Processing**: Celery tasks for long-running operations
3. **Real-time Updates**: Supabase Realtime for status updates
4. **Media Storage**: Supabase Storage for images/videos
5. **Payment Processing**: Dodo Payments webhooks

---

## Apps Overview

### 1. Accounts App (`accounts/`)
**Purpose**: User management, authentication, subscriptions, usage tracking

**Key Models:**
- `User`: Custom user model (email-based, no username)
- `Plan`: Subscription plans (Free, Pro, etc.)
- `Subscription`: User subscriptions with status tracking
- `UserUsage`: Daily usage tracking per platform

**Key Features:**
- Clerk authentication integration
- Auto-creation of Free subscriptions
- Usage limit enforcement
- Plan management

### 2. Analysis App (`analysis/`)
**Purpose**: Core analysis functionality - post analysis requests, AI processing, chat

**Key Models:**
- `PostAnalysisRequest`: Main analysis request container
- `PostAnalysis`: Individual post analysis results
- `AnalysisStatusHistory`: Real-time status updates
- `ChatSession`: Chat sessions for post Q&A
- `ChatMessage`: Individual chat messages
- `AnalysisNote`: User notes on analyses

**Key Features:**
- Multi-stage processing pipeline
- Gemini AI integration
- Real-time status updates
- Chat interface for follow-up questions
- Note-taking system

### 3. Social App (`social/`)
**Purpose**: Social media scraping, post storage, media handling

**Key Models:**
- `Platform`: Supported platforms (Instagram, X, YouTube)
- `Post`: Scraped post data
- `PostMedia`: Media files (images, videos, thumbnails)
- `PostComment`: Post comments
- `UserPostActivity`: User interaction tracking

**Key Features:**
- BrightData scraping integration
- TwitterAPI.io integration
- YouTube API integration
- Media extraction and storage
- Video transcription (Whisper AI)

### 4. Billing App (`billing/`)
**Purpose**: Payment processing, subscription management, webhooks

**Key Models:**
- `PaymentMethod`: Stored payment methods
- `Payment`: Payment transactions
- `Invoice`: Invoice records
- `BillingEvent`: Webhook event tracking
- `Refund`: Refund records

**Key Features:**
- Dodo Payments integration
- Subscription upgrades/downgrades
- Webhook processing
- Prorated billing
- Payment method management

### 5. Analytics App (`analytics/`)
**Purpose**: API tracking, usage analytics, monitoring

**Key Models:**
- `APIAccessLog`: All API request logs
- `AuthenticationLog`: Auth event tracking
- `ExternalAPICallLog`: External API calls (Gemini, BrightData, etc.)

**Key Features:**
- Middleware for automatic logging
- Performance monitoring
- Cost tracking
- Error tracking

### 6. Feedback App (`feedback/`)
**Purpose**: User feedback collection (currently minimal implementation)

### 7. Logs App (`logs/`)
**Purpose**: Application-level logging

**Key Models:**
- `AppLog`: Structured application logs

---

## Detailed App Documentation

### Accounts App

#### Models

**User Model**
- UUID primary key
- Email-based authentication (no username)
- Clerk integration (`clerk_user_id`)
- Profile fields: `full_name`, `company_name`, `profile_image`
- Email verification status synced from Clerk

**Plan Model**
- Subscription tiers (Free, Pro, etc.)
- Limits: `max_handles`, `max_urls`, `max_analyses_per_day`, `max_questions_per_day`
- Payment provider product ID linking

**Subscription Model**
- Statuses: ACTIVE, PENDING, TRIAL, FAILED, CANCELING, CANCELLED, EXPIRED
- Payment providers: STRIPE, DODO
- Provider IDs for external payment systems
- Downgrade scheduling (`downgrade_to_plan`)

**UserUsage Model**
- Daily usage tracking per platform
- Tracks: `handle_analyses`, `url_lookups`, `post_suggestions`, `questions_asked`
- Unique constraint: (user, date, platform)

#### Views & Endpoints

**Authentication:**
- `POST /api/accounts/signup/` - Create account via Clerk
- `POST /api/accounts/login/` - Login (token-based)
- `POST /api/accounts/logout/` - Logout
- `POST /api/accounts/reset-password/` - Password reset request

**Profile:**
- `GET/PATCH /api/accounts/me/` - Get/update profile

**Subscriptions:**
- `GET /api/accounts/subscription/` - Get current subscription
- `GET /api/accounts/plans/` - List all plans (public)

**Usage:**
- `GET /api/accounts/usage/` - Get usage stats
- `GET /api/accounts/usage/limits/` - Get plan limits
- `GET /api/accounts/usage/history/` - Get usage history

#### Key Utilities

**`get_user_subscription()`**: Get active subscription (handles CANCELING status)
**`get_user_plan()`**: Get user's current plan
**`check_usage_limit()`**: Check if user can perform action
**`increment_usage()`**: Increment usage counters

#### Authentication Flow

1. User signs up via Clerk (frontend)
2. Clerk creates user and sends JWT token
3. Backend syncs user via `ClerkAuthentication` middleware
4. Auto-creates Free subscription if new user
5. JWT token used for all subsequent requests

---

### Analysis App

#### Models

**PostAnalysisRequest**
- Main container for analysis requests
- Fields:
  - `platform`: Instagram, X, or YouTube
  - `post_urls`: List of URLs to analyze
  - `display_name`: Extracted username (for sidebar)
  - `status`: PENDING, PROCESSING, COMPLETED, FAILED
  - `results`: AI analysis results (JSON)
  - Error tracking fields (`error_stage`, `error_category`, `error_details`)
  - Retry mechanism (`retry_count`, `max_retries`)
  - Business metrics (`duration_seconds`, `total_api_calls`, `posts_processed`)

**PostAnalysis**
- Individual post analysis results
- Stores:
  - `is_viral`: Boolean virality flag
  - `virality_reasoning`: Why it went viral
  - `quick_takeaways`: 3-5 bullet points
  - `creator_context`: Who posted this
  - `content_observation`: What AI sees (JSON)
  - `replicable_elements`: Prescriptive format
  - `viral_formula`: 1-2 line summary
  - `improvements`: Improvement suggestions
  - `suggestions_for_future_posts`: 4 future post ideas
  - `analysis_data`: Full analysis JSON
  - `metadata_used`: Metadata reference

**AnalysisStatusHistory**
- Real-time status updates for frontend
- Stages:
  - `request_created`
  - `fetching_posts`
  - `social_data_fetched`
  - `collecting_media`
  - `transcribing`
  - `displaying_content`
  - `analysing`
  - `analysis_complete`
  - `error`, `retrying`, `partial_success`
- Progress tracking (0-100%)
- Cost estimates per stage

**ChatSession & ChatMessage**
- One chat session per post analysis
- Stores user questions and AI responses
- Token tracking for cost analysis

**AnalysisNote**
- User notes on analyses
- One note per user per analysis
- Title and content fields

#### Processing Pipeline

The analysis process follows these stages (in `tasks.py`):

1. **Request Creation** (`request_created`)
   - Validate URLs
   - Group by platform

2. **Social Media Collection** (`fetching_posts`, `social_data_fetched`)
   - Check for existing posts (fast path)
   - Scrape new posts via BrightData/TwitterAPI
   - Save posts to database
   - Link posts to analysis request

3. **Media Extraction** (`collecting_media`)
   - Extract images/videos
   - Upload to Supabase Storage
   - Download media bytes for analysis

4. **Transcription** (`transcribing`)
   - Use Whisper AI for video transcripts
   - Store transcripts on PostMedia

5. **AI Analysis** (`analysing`, `analysis_complete`)
   - For each post:
     - Build context (post data, media, transcript)
     - Call Gemini API with structured prompt
     - Parse JSON response
     - Save to PostAnalysis model

6. **Error Handling**
   - Partial success support
   - Retry mechanism (max 3 retries)
   - Error categorization (rate_limit, api_error, etc.)
   - Smart retry (resume from last successful stage)

#### Processors

**`social_collector.py`**
- Orchestrates scraping across platforms
- Fast path: Reuse existing posts
- Slow path: Scrape new posts
- Returns: posts, failed_urls, api_calls, fast_path_ids

**`post_linker.py`**
- Links posts to analysis requests
- Verifies post relationships
- Handles ManyToMany relationships

**`media_extractor.py`**
- Extracts media from posts
- Uploads to Supabase Storage
- Downloads media bytes for AI analysis
- Checks transcription status

**`gemini_analyzer.py`**
- Calls Gemini API per post
- Uses structured prompts from `prompts/` directory
- Parses JSON responses
- Handles rate limits and retries

**`duplicate_checker.py`**
- Checks for existing posts by URL
- Optimizes scraping costs

#### Services

**`gemini_service.py`**
- Gemini API client
- Key rotation support (multiple API keys)
- Rate limit handling
- Cost estimation

**`chat_service.py`**
- Chat message handling (non-streaming)
- Builds context from post analysis
- Calls Gemini for responses

**`chat_streaming_service.py`**
- Streaming chat responses
- Server-sent events (SSE)
- Real-time token delivery

**`chat_context_builder.py`**
- Builds chat context from post analysis
- Includes: post data, analysis results, previous messages

#### Views & Endpoints

- `POST /api/analysis/analyze/` - Create analysis request
- `GET /api/analysis/requests/` - List user's requests
- `GET /api/analysis/requests/<id>/` - Get specific request
- `POST /api/analysis/requests/<id>/retry/` - Retry failed request
- `POST /api/analysis/chat/sessions/` - Create chat session
- `GET /api/analysis/chat/sessions/list/` - List chat sessions
- `POST /api/analysis/chat/sessions/<id>/messages/` - Send message (non-streaming)
- `POST /api/analysis/chat/sessions/<id>/messages/stream/` - Send message (streaming)
- `GET /api/analysis/chat/sessions/<id>/` - Get chat session
- `GET /api/analysis/notes/` - List all notes
- `GET /api/analysis/notes/<post_analysis_id>/` - Get note for analysis
- `POST /api/analysis/notes/save/` - Create/update note
- `DELETE /api/analysis/notes/<note_id>/delete/` - Delete note

#### AI Provider Factory

Supports:
- Gemini (default) - via `gemini_service`
- Self-hosted LLM - via `self_hosted.py`

---

### Social App

#### Models

**Platform**
- Instagram, X (Twitter), YouTube
- Active/inactive status

**Post**
- Core post data
- Fields:
  - `platform_post_id`: Original platform ID
  - `username`: Post author
  - `content`: Post text/caption
  - `engagement_score`: Calculated score
  - `metrics`: JSON (likes, shares, comments, etc.)
  - `url`: Post URL
  - `transcript`: Video transcript (full text)
  - `formatted_transcript`: Timestamped segments (YouTube)

**PostMedia**
- Media files (images, videos, thumbnails)
- Fields:
  - `file`: Local file (if stored locally)
  - `source_url`: Original API URL
  - `supabase_url`: Supabase Storage URL
  - `uploaded_to_supabase`: Upload status
  - `transcript`: Audio transcript for videos

**PostComment**
- Stores comment data as JSON

**UserPostActivity**
- Tracks user interactions with posts

#### Scrapers

**BrightDataScraper** (`social/scrapers/`)
- Instagram scraping
- BrightData API integration

**TwitterAPIScraper** (`social/scrapers/`)
- X/Twitter scraping
- TwitterAPI.io integration

**YouTube Scraper** (via `yt-dlp`)
- Video metadata extraction
- Transcript fetching (via YouTube API)

#### Services

**`url_parser.py`**
- Detects platform from URL
- Validates URL format
- Extracts post IDs

**`post_saver.py`**
- Saves scraped posts to database
- Handles media uploads
- Creates PostMedia records

**`media_processor.py`**
- Processes media files
- Uploads to Supabase Storage
- Handles video frames/thumbnails

**`whisper_service.py`**
- Video transcription via Whisper AI
- Handles audio extraction
- Returns formatted transcripts

#### Views & Endpoints

- `GET /api/social/posts/analysis/<analysis_request_id>/` - Get posts for analysis

---

### Billing App

#### Models

**PaymentMethod**
- Stored payment methods
- Card details (last4, brand, exp)
- Default payment method tracking

**Payment**
- Payment transactions
- Statuses: PENDING, PROCESSING, SUCCEEDED, FAILED, CANCELED, REFUNDED
- Links to subscription
- Provider IDs (Dodo/Stripe)

**Invoice**
- Invoice records
- PDF URLs
- Payment tracking

**BillingEvent**
- Webhook event tracking
- Event types: subscription.created, payment.succeeded, etc.
- Processing status tracking

**Refund**
- Refund records
- Links to payments
- Status tracking

#### Services

**`dodo_service.py`**
- Dodo Payments API client
- Subscription management
- Payment processing
- Refund handling

#### Webhook Handlers

**`webhook_handlers.py`**
- Processes Dodo webhook events:
  - `payment.succeeded`: Create payment record, handle upgrades/downgrades
  - `subscription.active`: Activate subscription
  - `subscription.plan_changed`: Handle plan changes
  - `subscription.canceled`: Cancel subscription
  - `refund.succeeded`: Process refunds

**Key Features:**
- Prorated billing for upgrades
- Automatic downgrade scheduling
- Credit calculation
- Payment method updates

#### Views & Endpoints

- `POST /api/billing/subscribe/` - Subscribe to plan
- `POST /api/billing/upgrade/` - Upgrade plan
- `POST /api/billing/cancel/` - Cancel subscription
- `GET /api/billing/subscription/history/` - Get subscription history
- `POST /api/billing/webhook/dodo/` - Dodo webhook endpoint
- `GET /api/billing/subscription/success/` - Success page
- `GET /api/billing/subscription/cancel/` - Cancel page

#### Tasks

**`process_scheduled_downgrades`** (Celery Beat)
- Runs daily at midnight UTC
- Processes scheduled downgrades
- Updates subscription statuses

---

### Analytics App

#### Models

**APIAccessLog**
- Every API request logged
- Fields: endpoint, method, status_code, response_time_ms, ip_address, user_agent
- Performance tracking
- Error tracking

**AuthenticationLog**
- Auth events: signup, login, logout, password_reset
- Success/failure tracking
- IP address logging
- Security monitoring

**ExternalAPICallLog**
- External API calls: Gemini, BrightData, Supabase, TwitterAPI
- Cost estimation
- Response time tracking
- Error logging

#### Middleware

**`APITrackingMiddleware`**
- Automatically logs all API requests
- Tracks response times
- Logs errors
- Captures user info

#### Views & Endpoints

Currently no public endpoints (admin-only)

#### Tasks

**`tasks.py`**
- `log_auth_event`: Async auth event logging
- Background processing for analytics

---

### Feedback App

**Status**: Minimal implementation
- Basic model structure
- No active endpoints

---

### Logs App

#### Models

**AppLog**
- Structured logging
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Categories: AUTH, SCRAPE, API, ANALYSIS, BILLING, SYSTEM
- Metadata JSON field

---

## Key Integrations

### Clerk Authentication

**Setup:**
- Uses Clerk for user authentication
- JWT tokens for API access
- Email verification handled by Clerk
- Password reset via Clerk

**Implementation:**
- `ClerkAuthentication` class in `accounts.authentication`
- `ClerkClient` in `accounts.clerk_client`
- Syncs Clerk users with Django User model
- Auto-creates Free subscriptions

**Endpoints:**
- Signup creates Clerk user
- Login verifies JWT token
- All API endpoints use Clerk auth

### Supabase

**Database:**
- PostgreSQL database via Supabase
- Connection via `SUPABASE_DB_URL`
- All models use UUID primary keys

**Storage:**
- Media files uploaded to Supabase Storage
- Public URLs for frontend access
- Handles images, videos, thumbnails

**Realtime:**
- Used for real-time status updates
- AnalysisStatusHistory broadcasts
- Frontend subscribes to updates

### Google Gemini API

**Usage:**
- Post analysis via structured prompts
- Chat responses for Q&A
- Multiple API key rotation support
- Rate limit handling

**Configuration:**
- `GEMINI_API_KEY` (single key)
- `GEMINI_API_KEY_1` through `GEMINI_API_KEY_5` (rotation)
- Model: `gemini-2.0-flash-exp` (default)

**Cost Tracking:**
- Estimates tokens used
- Logs to ExternalAPICallLog
- Cost per analysis tracked

### BrightData

**Usage:**
- Instagram scraping
- Web scraping service
- API integration in `social/scrapers/`

### TwitterAPI.io

**Usage:**
- X/Twitter scraping
- Alternative to BrightData
- API integration in `social/scrapers/`

### Dodo Payments

**Usage:**
- Subscription payments
- Webhook processing
- Payment method storage
- Refund handling

**Webhook Events:**
- `payment.succeeded`
- `subscription.active`
- `subscription.plan_changed`
- `subscription.canceled`
- `refund.succeeded`

---

## Task Processing

### Celery Configuration

**Broker**: Redis (`CELERY_BROKER_URL`)
**Result Backend**: Django database (`django-db`)
**Task Time Limit**: 30 minutes
**Beat Schedule**: Daily at midnight UTC (downgrade processing)

### Main Tasks

**`analysis.tasks.process_analysis_request`**
- Main analysis orchestration
- Stages:
  1. Social media collection
  2. Media extraction
  3. Transcription
  4. AI analysis
- Error handling with retries
- Status history updates
- Cost tracking

**`billing.tasks.process_scheduled_downgrades`**
- Daily scheduled task
- Processes scheduled downgrades
- Updates subscription statuses

### Task Flow

1. User creates analysis request via API
2. View creates `PostAnalysisRequest` and queues Celery task
3. Task processes in background:
   - Updates status via `AnalysisStatusHistory`
   - Frontend receives real-time updates via Supabase Realtime
4. Task completes, updates request status
5. Frontend polls or receives completion notification

---

## Database Schema

### Key Relationships

**User → Subscription → Plan**
- One user can have multiple subscriptions (history)
- One subscription belongs to one plan
- Active subscription determines user limits

**User → PostAnalysisRequest → PostAnalysis → Post**
- One user creates many analysis requests
- One request analyzes many posts
- One post can be in multiple requests (caching)

**PostAnalysisRequest → AnalysisStatusHistory**
- One request has many status updates
- Used for real-time progress

**PostAnalysis → ChatSession → ChatMessage**
- One analysis has one chat session
- One session has many messages

**Post → PostMedia**
- One post has many media items
- Media can be images, videos, thumbnails

### Indexes

Most models have indexes on:
- Foreign keys
- Status fields
- Created/updated timestamps
- User + date combinations (for usage queries)

---

## API Endpoints

### Authentication Required
All endpoints except:
- `GET /api/accounts/plans/` (public)
- Health check endpoints

### Rate Limiting
- Analysis: 20/hour per user
- Chat: 100/hour per user
- Applied via `analysis.throttles`

### Response Format
- JSON responses
- Pagination: 20 items per page
- Error responses: `{"error": "message"}`

### Health Checks
- `GET /health/` - Full health check (database + Redis)
- `GET /health/live/` - Liveness probe
- `GET /health/ready/` - Readiness probe

---

## Configuration

### Environment Variables

**Required:**
- `SECRET_KEY` - Django secret key
- `SUPABASE_DB_URL` - Database connection
- `CLERK_SECRET_KEY` - Clerk authentication
- `CLERK_PUBLISHABLE_KEY` - Clerk public key
- `GEMINI_API_KEY` - Google Gemini API key
- `REDIS_URL` - Redis connection for Celery

**Optional:**
- `DEBUG` - Debug mode (default: True)
- `ALLOWED_HOSTS` - Comma-separated hosts
- `CORS_ALLOWED_ORIGINS` - Frontend origins
- `AI_PROVIDER` - AI provider (gemini/self_hosted)
- `SELF_HOSTED_LLM_URL` - Self-hosted LLM endpoint
- `BRIGHTDATA_API_KEY` - BrightData API key
- `TWITTERAPI_KEY` - TwitterAPI.io key
- `DODO_API_KEY` - Dodo Payments API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SECRET_KEY` - Supabase service role key

### Settings File

**Key Settings:**
- `AUTH_USER_MODEL = 'accounts.User'`
- `REST_FRAMEWORK`: Clerk auth, pagination, throttling
- `CELERY`: Redis broker, database results
- `LOGGING`: Console logging for Docker
- `CORS`: Frontend origin configuration

### Middleware Stack

1. `AllowNgrokHostsMiddleware` - Development ngrok support
2. `WhiteNoiseMiddleware` - Static file serving
3. `CorsMiddleware` - CORS handling
4. `APITrackingMiddleware` - API logging
5. Standard Django middleware

---

## Development Notes

### Key Design Decisions

1. **UUID Primary Keys**: All models use UUIDs for better distribution
2. **Status History**: Real-time updates via Supabase Realtime
3. **Fast Path Optimization**: Reuses existing posts to reduce scraping costs
4. **Partial Success**: Handles partial failures gracefully
5. **Error Categorization**: Detailed error tracking for debugging
6. **Retry Mechanism**: Smart retries with resume capability
7. **Usage Tracking**: Per-platform, per-day usage limits
8. **Cost Tracking**: Tracks API costs per operation

### Best Practices

1. All errors include `analysis_request_id` or `chat_session_id` for tracing
2. Logging uses structured format with context
3. Database queries use `select_related` and `prefetch_related` for optimization
4. Media files stored in Supabase, not local filesystem
5. Tasks are idempotent where possible
6. Webhook handlers are idempotent (check for existing records)

### Future Improvements

1. Username-based analysis (currently URL-only)
2. Batch processing optimizations
3. More AI providers (OpenAI, Anthropic)
4. Enhanced analytics dashboard
5. Webhook retry mechanism
6. Rate limit queuing
7. Media CDN integration

---

## Testing

### Test Files
- Each app has `tests.py`
- Currently basic test structure
- Expand with integration tests

### Manual Testing
- Use `test_webhook_local.sh` for webhook testing
- Health check endpoints for monitoring
- Admin panel for data inspection

---

## Deployment

### Docker
- `Dockerfile` for containerization
- `docker-compose.yml` for local development
- Health checks configured for Kubernetes

### Production Considerations
1. Set `DEBUG=False`
2. Configure `ALLOWED_HOSTS`
3. Use production Redis
4. Configure Celery workers
5. Set up Supabase production database
6. Configure webhook endpoints
7. Set up monitoring/alerting
8. Configure log aggregation

---

## Support & Maintenance

### Logging
- All logs go to stdout/stderr (Docker-friendly)
- Structured logging with context
- Error tracking via `AnalysisStatusHistory`

### Monitoring
- Health check endpoints
- Analytics app tracks performance
- External API call logging

### Debugging
- `error_details` JSON field for exceptions
- `error_stage` and `error_category` for quick diagnosis
- Status history shows full timeline
- Admin panel for data inspection

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0
**Maintainer**: Backend Team