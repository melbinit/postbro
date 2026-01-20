# PostBro Backend

PostBro is a social media analysis and post suggestion tool that helps users analyze their social media performance and get AI-powered content suggestions.

## Features

- User authentication with Clerk
- Social media post analysis (Instagram, X/Twitter, YouTube)
- AI-powered post analysis using Gemini 2.5 Flash
- Video transcription (YouTube API + Whisper AI)
- Usage tracking and subscription management
- Payment processing with Dodo Payments
- RESTful API endpoints
- Asynchronous task processing with Celery
- Media storage with Supabase

## Tech Stack

- Django 5.x
- PostgreSQL (via Supabase)
- Celery + Redis
- Django REST Framework
- Clerk (authentication)
- Dodo Payments (subscriptions)
- BrightData (social media scraping)
- Gemini 2.5 Flash (AI analysis)
- Supabase (media storage)
- Whisper AI (video transcription)

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with:
```bash
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgres://user:password@localhost:5432/postbro

# Redis
REDIS_URL=redis://localhost:6379/0

# BrightData API (for Instagram & YouTube scraping)
BRIGHTDATA_API_TOKEN=your-brightdata-api-token
BRIGHTDATA_INSTAGRAM_DATASET_ID=gd_lk5ns7kz21pck8jpis  # Instagram Posts API
BRIGHTDATA_INSTAGRAM_REELS_DATASET_ID=gd_lyclm20il4r5helnj  # Instagram Reels API
BRIGHTDATA_YOUTUBE_DATASET_ID=your-youtube-dataset-id

# AI Services
GEMINI_API_KEY_1=your-gemini-api-key

# Payment Processing (Dodo Payments)
DODO_API_KEY=your-dodo-api-key
DODO_WEBHOOK_SECRET=your-dodo-webhook-secret

# Authentication (Clerk)
CLERK_SECRET_KEY=your-clerk-secret-key

# Storage (Supabase)
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
SUPABASE_BUCKET_NAME=post-media
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

7. Start Celery worker (in a separate terminal):
```bash
celery -A postbro worker -l info
```

## Project Structure

- `accounts/` - User management and subscription
- `social/` - Social media post handling
- `analysis/` - Post analysis and suggestions
- `feedback/` - User feedback system
- `billing/` - Payment processing
- `logs/` - Application logging

## API Documentation

API documentation is available at `/api/docs/` when running the server.

## Development

- Use `black` for code formatting
- Follow PEP 8 guidelines
- Write tests for new features
- Update documentation as needed

## License

Proprietary - All rights reserved 