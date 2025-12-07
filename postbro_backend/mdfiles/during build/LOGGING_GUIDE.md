# Logging Guide - Production Ready

## Overview

All errors are now traceable to `analysis_request_id` or `chat_session_id`. Logs are rotated automatically by Docker (10MB files, 5 backups = 50MB max per container).

## How to Check Logs

### View All Logs
```bash
docker-compose logs
```

### View Specific Service
```bash
docker-compose logs backend
docker-compose logs celery-worker
```

### Follow Logs in Real-Time
```bash
docker-compose logs -f backend
```

### Find Errors for Specific Analysis
```bash
# Find all errors for a specific analysis
docker-compose logs | grep "analysis_request_id=abc-123-def"

# Find all errors for a specific chat session
docker-compose logs | grep "chat_session_id=xyz-789-abc"
```

### Find All Errors
```bash
# All errors today
docker-compose logs --since 24h | grep "ERROR\|❌"

# All errors in Celery
docker-compose logs celery-worker | grep "ERROR\|❌"

# All errors in backend
docker-compose logs backend | grep "ERROR\|❌"
```

### Export Logs
```bash
# Export all errors to file
docker-compose logs | grep "ERROR\|❌" > errors-$(date +%Y%m%d).log

# Export specific analysis logs
docker-compose logs | grep "analysis_request_id=abc-123" > analysis-abc-123.log
```

## Log Format

All logs include:
- **Level**: INFO, WARNING, ERROR
- **Timestamp**: YYYY-MM-DD HH:MM:SS
- **Module**: Which file/component logged it
- **Process ID**: For debugging multi-process issues
- **Message**: Human-readable message
- **Context**: `analysis_request_id` or `chat_session_id` in error messages

### Example Log Output
```
ERROR 2024-01-01 10:00:00 [analysis.tasks] 12345 ❌ [Analysis] Failed to scrape Instagram post for analysis_request_id=abc-123-def: Connection timeout
```

## Error Tracing

### Scenario 1: User reports "My analysis failed"
1. Get the `analysis_request_id` from database or frontend
2. Search logs:
   ```bash
   docker-compose logs | grep "analysis_request_id=abc-123"
   ```
3. You'll see the full flow:
   - When request was created
   - When Celery task started
   - Which scraper was called
   - Where it failed
   - Any retry attempts

### Scenario 2: User reports "Chat not working"
1. Get the `chat_session_id` from database
2. Search logs:
   ```bash
   docker-compose logs | grep "chat_session_id=xyz-789"
   ```
3. You'll see:
   - When chat session was created
   - Message sending attempts
   - Streaming errors
   - Gemini API errors

### Scenario 3: Find all errors for a user
```bash
# Get user_id from database, then:
docker-compose logs | grep "user_id=user-123" | grep "ERROR\|❌"
```

## Log Rotation

Docker automatically rotates logs:
- **Max file size**: 10MB
- **Max files**: 5 (keeps 5 rotated files)
- **Total max**: 50MB per container
- **Compression**: Old logs are compressed

Logs are stored in Docker's log directory (usually `/var/lib/docker/containers/`).

## Important Notes

1. **All errors include traceable IDs**: Every error log includes `analysis_request_id` or `chat_session_id`
2. **All exceptions use `exc_info=True`**: Full stack traces are logged
3. **No file logging**: All logs go to stdout/stderr (Docker handles collection)
4. **Production-ready**: Handles 1000+ users without filling disk

## Quick Troubleshooting Commands

```bash
# See recent errors (last 100 lines)
docker-compose logs --tail=100 | grep "ERROR\|❌"

# See errors from last hour
docker-compose logs --since 1h | grep "ERROR\|❌"

# Monitor errors in real-time
docker-compose logs -f | grep "ERROR\|❌"

# Find slow operations
docker-compose logs | grep "took.*ms\|took.*s"

# Find all FastPath operations (optimized)
docker-compose logs | grep "FastPath"

# Find all failed scrapes
docker-compose logs | grep "Failed to scrape"
```




## Overview

All errors are now traceable to `analysis_request_id` or `chat_session_id`. Logs are rotated automatically by Docker (10MB files, 5 backups = 50MB max per container).

## How to Check Logs

### View All Logs
```bash
docker-compose logs
```

### View Specific Service
```bash
docker-compose logs backend
docker-compose logs celery-worker
```

### Follow Logs in Real-Time
```bash
docker-compose logs -f backend
```

### Find Errors for Specific Analysis
```bash
# Find all errors for a specific analysis
docker-compose logs | grep "analysis_request_id=abc-123-def"

# Find all errors for a specific chat session
docker-compose logs | grep "chat_session_id=xyz-789-abc"
```

### Find All Errors
```bash
# All errors today
docker-compose logs --since 24h | grep "ERROR\|❌"

# All errors in Celery
docker-compose logs celery-worker | grep "ERROR\|❌"

# All errors in backend
docker-compose logs backend | grep "ERROR\|❌"
```

### Export Logs
```bash
# Export all errors to file
docker-compose logs | grep "ERROR\|❌" > errors-$(date +%Y%m%d).log

# Export specific analysis logs
docker-compose logs | grep "analysis_request_id=abc-123" > analysis-abc-123.log
```

## Log Format

All logs include:
- **Level**: INFO, WARNING, ERROR
- **Timestamp**: YYYY-MM-DD HH:MM:SS
- **Module**: Which file/component logged it
- **Process ID**: For debugging multi-process issues
- **Message**: Human-readable message
- **Context**: `analysis_request_id` or `chat_session_id` in error messages

### Example Log Output
```
ERROR 2024-01-01 10:00:00 [analysis.tasks] 12345 ❌ [Analysis] Failed to scrape Instagram post for analysis_request_id=abc-123-def: Connection timeout
```

## Error Tracing

### Scenario 1: User reports "My analysis failed"
1. Get the `analysis_request_id` from database or frontend
2. Search logs:
   ```bash
   docker-compose logs | grep "analysis_request_id=abc-123"
   ```
3. You'll see the full flow:
   - When request was created
   - When Celery task started
   - Which scraper was called
   - Where it failed
   - Any retry attempts

### Scenario 2: User reports "Chat not working"
1. Get the `chat_session_id` from database
2. Search logs:
   ```bash
   docker-compose logs | grep "chat_session_id=xyz-789"
   ```
3. You'll see:
   - When chat session was created
   - Message sending attempts
   - Streaming errors
   - Gemini API errors

### Scenario 3: Find all errors for a user
```bash
# Get user_id from database, then:
docker-compose logs | grep "user_id=user-123" | grep "ERROR\|❌"
```

## Log Rotation

Docker automatically rotates logs:
- **Max file size**: 10MB
- **Max files**: 5 (keeps 5 rotated files)
- **Total max**: 50MB per container
- **Compression**: Old logs are compressed

Logs are stored in Docker's log directory (usually `/var/lib/docker/containers/`).

## Important Notes

1. **All errors include traceable IDs**: Every error log includes `analysis_request_id` or `chat_session_id`
2. **All exceptions use `exc_info=True`**: Full stack traces are logged
3. **No file logging**: All logs go to stdout/stderr (Docker handles collection)
4. **Production-ready**: Handles 1000+ users without filling disk

## Quick Troubleshooting Commands

```bash
# See recent errors (last 100 lines)
docker-compose logs --tail=100 | grep "ERROR\|❌"

# See errors from last hour
docker-compose logs --since 1h | grep "ERROR\|❌"

# Monitor errors in real-time
docker-compose logs -f | grep "ERROR\|❌"

# Find slow operations
docker-compose logs | grep "took.*ms\|took.*s"

# Find all FastPath operations (optimized)
docker-compose logs | grep "FastPath"

# Find all failed scrapes
docker-compose logs | grep "Failed to scrape"
```



