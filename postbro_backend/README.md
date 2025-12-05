# PostBro Backend

PostBro is a social media analysis and post suggestion tool that helps users analyze their social media performance and get AI-powered content suggestions.

## Features

- User authentication with email verification
- Social media post analysis (Twitter, Instagram)
- AI-powered post suggestions using Claude
- Usage tracking and subscription management
- RESTful API endpoints
- Asynchronous task processing with Celery

## Tech Stack

- Django 5.x
- PostgreSQL
- Celery + Redis
- REST Framework
- Django AllAuth
- Stripe (for payments)

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
```
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:password@localhost:5432/postbro
REDIS_URL=redis://localhost:6379/0
STRIPE_PUBLIC_KEY=your-stripe-public-key
STRIPE_SECRET_KEY=your-stripe-secret-key
ANTHROPIC_API_KEY=your-anthropic-api-key
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