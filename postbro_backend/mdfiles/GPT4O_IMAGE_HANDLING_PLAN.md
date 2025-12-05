# GPT-4o Image Handling Plan

## Current State

### Image Download Status:

1. **Instagram Images**: ✅ **Downloaded & Uploaded to Supabase**
   - Location: `post_saver.py` line 252
   - Process: Images downloaded immediately and uploaded to Supabase
   - Result: Both `source_url` (original) and `supabase_url` (uploaded) available

2. **Twitter/X Images**: ❌ **NOT Downloaded**
   - Location: `post_saver.py` line 612
   - Process: "Lazy upload" - only URL stored (`uploaded_to_supabase: False`)
   - Result: Only `source_url` available, no local file

3. **YouTube Thumbnails**: ✅ **Downloaded & Uploaded to Supabase**
   - Location: `post_saver.py` line 427
   - Process: Thumbnails downloaded and uploaded immediately
   - Result: Both `source_url` and `supabase_url` available

### GPT-4o Limitation:
- **Cannot read images from URLs directly**
- **Needs base64-encoded image data**
- Must download image → convert to base64 → include in API call

---

## Solution: Download Images Right Before OpenAI API Call

### Best Location: `openai_service.py` - Right Before API Call

**Why here?**
1. ✅ Only needed when using OpenAI (not Gemini)
2. ✅ Images already available as URLs (from scraping)
3. ✅ Can download on-demand without affecting other flows
4. ✅ Keeps image processing logic isolated to OpenAI service

### Implementation Plan

#### Step 1: Create Image Download Helper
**File**: `analysis/services/openai_service.py`

**Function**:
```python
def download_and_encode_image(image_url: str) -> Optional[Dict]:
    """
    Download image from URL and convert to base64 for GPT-4o.
    
    Returns:
        Dict with 'type': 'image_url' or 'type': 'base64' format
        None if download fails
    """
    # Download image
    # Convert to base64
    # Detect MIME type
    # Return OpenAI format
```

#### Step 2: Update `analyze_post_with_openai()`
**Location**: `openai_service.py` - before API call

**Process**:
1. Get media URLs from `media_urls` parameter
2. For each image URL:
   - Download image (use existing `MediaProcessor.download_image()`)
   - Convert to base64
   - Detect MIME type (image/jpeg, image/png, etc.)
   - Create OpenAI image message format
3. Include images in `messages` array alongside text

#### Step 3: OpenAI Message Format
**Format**:
```python
messages = [
    {
        "role": "system",
        "content": system_prompt,
        "cache_control": {"type": "ephemeral"}
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": user_prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_data}"
                }
            }
            # ... more images
        ]
    }
]
```

---

## Where Images Are Available

### Current Flow:
1. **Scraping** → Images stored as URLs in `PostMedia` model
2. **Post Saving** → URLs saved to database
3. **Analysis** → URLs passed to `analyze_post_with_openai()` as `media_urls` list

### Image Sources:
- **Instagram**: `supabase_url` (preferred) or `source_url` (fallback)
- **Twitter**: `source_url` only (not uploaded to Supabase)
- **YouTube**: `supabase_url` (thumbnail) or frames

---

## Implementation Details

### Option 1: Download Right Before API Call (Recommended)
**Location**: `openai_service.py` - in `analyze_post_with_openai()`

**Pros**:
- ✅ Only downloads when using OpenAI
- ✅ Doesn't affect Gemini flow
- ✅ Keeps image processing isolated
- ✅ Can use existing `MediaProcessor.download_image()`

**Cons**:
- ⚠️ Adds latency to OpenAI API call
- ⚠️ Downloads same image multiple times if analyzing same post

### Option 2: Download After Supabase Upload
**Location**: `post_saver.py` - after uploading to Supabase

**Pros**:
- ✅ Images already downloaded (no extra download)
- ✅ Can cache base64 in database

**Cons**:
- ❌ Downloads for all models (even Gemini)
- ❌ Stores base64 in database (large size)
- ❌ Not needed for Gemini

**Recommendation**: **Option 1** - Download right before OpenAI API call

---

## Code Changes Needed

### 1. Add Image Download Function to `openai_service.py`
```python
import base64
import requests
from typing import Optional, Dict, List
from social.services.media_processor import MediaProcessor

def download_and_encode_image(image_url: str) -> Optional[Dict]:
    """Download image and convert to base64 for GPT-4o"""
    media_processor = MediaProcessor()
    image_data = media_processor.download_image(image_url)
    
    if not image_data:
        return None
    
    # Detect MIME type
    import mimetypes
    mime_type, _ = mimetypes.guess_type(image_url)
    if not mime_type or not mime_type.startswith('image/'):
        mime_type = 'image/jpeg'  # Default
    
    # Convert to base64
    base64_data = base64.b64encode(image_data).decode('utf-8')
    
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime_type};base64,{base64_data}"
        }
    }
```

### 2. Update `analyze_post_with_openai()` to Include Images
```python
# Before API call, process images
image_messages = []
for image_url in media_urls:
    if image_url:  # Skip empty URLs
        image_msg = download_and_encode_image(image_url)
        if image_msg:
            image_messages.append(image_msg)

# Build content array
content = [
    {"type": "text", "text": enhanced_user_prompt}
]
content.extend(image_messages)  # Add images

# Update messages
messages = [
    {
        "role": "system",
        "content": enhanced_system_prompt,
        "cache_control": {"type": "ephemeral"}
    },
    {
        "role": "user",
        "content": content  # Now includes text + images
    }
]
```

---

## Answer to Your Questions

### Q1: Where to download images?
**Answer**: **Right before OpenAI API call** in `openai_service.py`

**Why**:
- Only needed for OpenAI (not Gemini)
- Images already available as URLs
- Keeps processing isolated
- Can reuse existing download logic

### Q2: After Supabase upload or right after download?
**Answer**: **Neither - download on-demand right before OpenAI call**

**Why**:
- Instagram images: Already uploaded to Supabase, but we still need to download for base64
- Twitter images: Not uploaded, need to download from source URL
- Best approach: Download on-demand (don't store base64 in DB)

### Q3: Are we downloading Twitter images?
**Answer**: **NO - Currently Twitter images are NOT downloaded**

**Current State**:
- Twitter images: Only URL stored (`source_url`)
- `uploaded_to_supabase: False` (lazy upload)
- No local file or Supabase upload

**For GPT-4o**:
- Need to download Twitter images from `source_url`
- Convert to base64
- Include in API call

---

## Implementation Steps

1. ✅ Add `download_and_encode_image()` function to `openai_service.py`
2. ✅ Update `analyze_post_with_openai()` to process images
3. ✅ Include images in OpenAI messages array
4. ✅ Handle errors gracefully (if image download fails, continue with text only)
5. ✅ Log image processing for debugging

---

## Error Handling

- If image download fails → Continue with text-only analysis
- If image is too large → Skip or resize (OpenAI has size limits)
- If invalid image format → Skip that image, continue with others
- Log all failures for debugging

---

## Performance Considerations

- **Download time**: Adds ~1-3 seconds per image
- **API call size**: Base64 increases payload size
- **Caching**: Could cache base64 in memory for same request (optional)

---

*Ready to implement when approved!*






