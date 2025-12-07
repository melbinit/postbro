# Media Processing Implementation - Complete ✅

**Date:** 2025-01-XX  
**Status:** Implementation Complete

---

## 📋 Summary

Successfully implemented professional-grade media processing functionality for PostBro, including:

- ✅ Database model updates (`PostMedia` with Supabase Storage fields)
- ✅ `MediaProcessor` service with FFmpeg, yt-dlp, and Supabase integration
- ✅ `PostSaver` integration with smart upload strategy
- ✅ Migration created and ready to apply
- ✅ Environment variables documented

---

## 🗄️ Database Changes

### `PostMedia` Model Updates

**New Fields:**
- `supabase_url` (URLField, nullable): Supabase Storage URL for uploaded media
- `uploaded_to_supabase` (BooleanField): Tracks upload status

**New Media Type:**
- `VIDEO_FRAME`: For extracted video frames

**New Indexes:**
- `uploaded_to_supabase` (for lazy upload queries)
- `post, media_type` (for efficient queries)

**Migration:** `social/migrations/0004_add_supabase_storage_fields.py`

---

## 🔧 New Service: `MediaProcessor`

**Location:** `social/services/media_processor.py`

### Key Features:

1. **YouTube Frame Extraction**
   - Uses `yt-dlp` to get working video stream URLs
   - Extracts frames at 0%, 25%, 50%, 75%, 100% of video duration
   - Uses FFmpeg for frame extraction
   - Handles expired `googlevideo.com` URLs automatically

2. **Video Frame Extraction (Instagram/Twitter)**
   - Direct FFmpeg extraction from video URLs
   - Extracts 5 frames evenly distributed across video

3. **Image Download**
   - Browser headers to avoid blocking
   - Content-type detection
   - Proper error handling

4. **Supabase Storage Upload**
   - Automatic upload with proper MIME types
   - Public URL generation
   - Error handling and logging

5. **Smart Upload Strategy**
   - **Immediate upload:** Video frames, Instagram/YouTube media (URLs expire)
   - **Lazy upload:** Twitter images (URLs don't expire)

### Methods:

```python
# YouTube
extract_youtube_frames(video_id, num_frames=5) -> List[bytes]
process_youtube_video(video_id, post_id, num_frames=5) -> List[str]

# Generic video
extract_video_frames(video_url, num_frames=5) -> List[bytes]
process_video_frames(video_url, post_id, num_frames=5) -> List[str]

# Images
download_image(image_url) -> Optional[bytes]
process_image(image_url, post_id, media_index=0) -> Optional[str]

# Upload
upload_to_supabase(file_data, filename, content_type) -> Optional[str]

# Strategy
should_upload_immediately(platform, media_type, source_url) -> bool
```

---

## 🔄 PostSaver Integration

**Location:** `social/services/post_saver.py`

### Changes:

1. **Initialization**
   - Added `MediaProcessor` instance to `PostSaver`

2. **Instagram Posts** (`save_instagram_post`)
   - Processes images with lazy upload strategy
   - Saves `uploaded_to_supabase=False` initially
   - Calls `_process_media()` for each image

3. **YouTube Videos** (`save_youtube_video`)
   - Extracts 5 frames immediately using `process_youtube_video()`
   - Uploads frames to Supabase Storage
   - Saves frames as `PostMedia` with `media_type='video_frame'`
   - Processes thumbnail with lazy upload

4. **Twitter Tweets** (`save_twitter_tweet`)
   - **Videos:** Extracts frames immediately, uploads to Supabase
   - **Images:** Lazy upload (saves URL, marks `uploaded_to_supabase=False`)

5. **New Method: `_process_media()`**
   - Implements smart upload strategy
   - Handles immediate vs lazy uploads
   - Updates `PostMedia` with Supabase URLs

---

## 📦 Dependencies

**Added to `requirements.txt`:**
- `requests>=2.31.0` (for image downloads)
- `python-dateutil>=2.8.2` (for date parsing)

**System Requirements:**
- `ffmpeg` (for video frame extraction)
- `ffprobe` (for video duration)
- `yt-dlp` (for YouTube video stream URLs)

**Installation:**
```bash
# macOS
brew install ffmpeg yt-dlp

# Ubuntu/Debian
sudo apt-get install ffmpeg
pip install yt-dlp
```

---

## 🔐 Environment Variables

**Added to `env.example`:**

```bash
# Supabase Storage (for media uploads)
# Get SERVICE_ROLE_KEY from: Settings → API → service_role key
# Create bucket in: Storage → Buckets → Create bucket (name: post-media, public: true)
SUPABASE_STORAGE_BUCKET=post-media
```

**Required:**
- `SUPABASE_URL` (already configured)
- `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_SECRET_KEY` (already configured)
- `SUPABASE_STORAGE_BUCKET` (new)

---

## 🚀 Usage Flow

### 1. User Submits URL
```
POST /api/analysis/analyze/
{
  "platform": "youtube",
  "post_urls": ["https://youtube.com/watch?v=..."]
}
```

### 2. Celery Task Processes
```
process_analysis_request()
  → Scrape YouTube video
  → PostSaver.save_youtube_video()
    → Save Post to database
    → MediaProcessor.process_youtube_video()
      → Extract 5 frames using yt-dlp + FFmpeg
      → Upload frames to Supabase Storage
    → Save PostMedia entries with supabase_url
```

### 3. Media Available
- Original video URL: `PostMedia.source_url`
- Frame URLs: `PostMedia.supabase_url` (for frames)
- Upload status: `PostMedia.uploaded_to_supabase`

---

## 📊 Upload Strategy

| Platform | Media Type | Strategy | Reason |
|----------|-----------|----------|--------|
| YouTube | Video frames | Immediate | Needed for Gemini, small files |
| YouTube | Thumbnail | Immediate | URLs expire |
| Instagram | Images | **Lazy** | URLs stay active for hours (save 1-2 secs) |
| Instagram | Videos | Immediate | Extract frames for Gemini |
| Twitter | Images | Lazy | URLs don't expire |
| Twitter | Video frames | Immediate | Needed for Gemini |

---

## 🎯 Next Steps

1. **Apply Migration:**
   ```bash
   python manage.py migrate social
   ```

2. **Set Up Supabase Storage:**
   - Create bucket: `post-media`
   - Set as public
   - Add `SUPABASE_STORAGE_BUCKET` to `.env`

3. **Install System Dependencies:**
   ```bash
   brew install ffmpeg yt-dlp  # macOS
   ```

4. **Test Media Processing:**
   - Test YouTube frame extraction
   - Test Instagram image upload
   - Test Twitter lazy upload

5. **Future: Celery Beat Task for Lazy Uploads**
   - Create periodic task to upload `uploaded_to_supabase=False` media
   - Run every 30 minutes
   - Process Twitter images in background

---

## 🐛 Error Handling

All methods include comprehensive error handling:

- **YouTube frame extraction:** Falls back gracefully if yt-dlp/FFmpeg fails
- **Image downloads:** Returns `None` if download fails, doesn't crash
- **Supabase uploads:** Logs errors, continues processing
- **PostSaver:** Media processing errors don't prevent post saving

---

## 📝 Code Quality

✅ **Professional Python practices:**
- Type hints throughout
- Comprehensive docstrings
- Proper logging
- Error handling
- Clean separation of concerns
- Modular design

✅ **Django best practices:**
- Transaction management
- Model field choices
- Database indexes
- Proper migrations

---

## ✅ Implementation Checklist

- [x] Add `supabase_url` and `uploaded_to_supabase` to `PostMedia`
- [x] Add `VIDEO_FRAME` media type
- [x] Create `MediaProcessor` service
- [x] Implement YouTube frame extraction (yt-dlp + FFmpeg)
- [x] Implement video frame extraction (FFmpeg)
- [x] Implement image download with headers
- [x] Implement Supabase Storage upload
- [x] Implement smart upload strategy
- [x] Integrate into `PostSaver`
- [x] Update Instagram post saving
- [x] Update YouTube video saving
- [x] Update Twitter tweet saving
- [x] Create migration
- [x] Update `env.example`
- [x] Update `requirements.txt`
- [x] Update `__init__.py` exports

---

**Status:** ✅ Ready for testing and deployment

