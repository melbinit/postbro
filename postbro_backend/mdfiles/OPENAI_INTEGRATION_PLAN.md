# OpenAI Integration Plan

## Overview
Add OpenAI GPT-4o support alongside existing Gemini service, with environment variable to switch between models.

---

## Current Architecture

### Current Flow:
1. `analysis/tasks.py` → calls `analyze_post_with_gemini()` from `analysis/services/gemini_service.py`
2. `gemini_service.py` → loads prompt template, builds prompts, calls Gemini API
3. Returns analysis result as JSON

### What We Need:
- Similar service for OpenAI (`analysis/services/openai_service.py`)
- Environment variable to select model (`USE_MODEL=openai` or `USE_MODEL=gemini`)
- Update `tasks.py` to use selected model
- Both services use same prompt template

---

## Implementation Plan

### Phase 1: Create OpenAI Service
**File:** `postbro_backend/analysis/services/openai_service.py`

**What it does:**
- Mirrors `gemini_service.py` structure
- Uses same prompt template (`prompts/v1.txt`)
- Calls OpenAI GPT-4o API
- Enables input caching (50% discount on system prompt)
- Returns same JSON structure as Gemini

**Key Features:**
- ✅ Uses `get_system_prompt()` and `build_user_prompt()` (shared functions)
- ✅ Implements retry logic for rate limits
- ✅ Logs API calls to analytics
- ✅ Handles JSON parsing and validation
- ✅ Enables `cache_control={"type": "ephemeral"}` for input caching

**Function Signature:**
```python
def analyze_post_with_openai(
    platform: str,
    task_id: str,
    post_data: Dict,
    media_urls: List[str],
    video_length: Optional[int] = None,
    transcript: Optional[str] = None,
    frames: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict:
```

---

### Phase 2: Create Shared Prompt Utilities
**File:** `postbro_backend/analysis/services/prompt_utils.py` (NEW)

**Why:** Both Gemini and OpenAI need the same prompt building logic. Extract to shared module.

**Functions:**
- `load_prompt_template()` - Load v1.txt
- `get_system_prompt()` - Extract system prompt section
- `build_user_prompt()` - Build user prompt with post data

**Benefits:**
- ✅ DRY (Don't Repeat Yourself)
- ✅ Single source of truth for prompts
- ✅ Easy to update prompts for both models

---

### Phase 3: Update Gemini Service
**File:** `postbro_backend/analysis/services/gemini_service.py`

**Changes:**
- Import shared prompt utilities from `prompt_utils.py`
- Remove duplicate `load_prompt_template()`, `get_system_prompt()`, `build_user_prompt()`
- Keep Gemini-specific logic (API calls, response parsing)

---

### Phase 4: Add Model Selection Logic
**File:** `postbro_backend/analysis/services/__init__.py` (NEW) or update existing

**Function:**
```python
def get_analysis_service():
    """
    Returns the appropriate analysis service based on USE_MODEL env var.
    
    Returns:
        Function: analyze_post_with_gemini or analyze_post_with_openai
    """
    use_model = os.getenv('USE_MODEL', 'gemini').lower()
    
    if use_model == 'openai':
        from .openai_service import analyze_post_with_openai
        return analyze_post_with_openai
    else:
        from .gemini_service import analyze_post_with_gemini
        return analyze_post_with_gemini
```

---

### Phase 5: Update Celery Task
**File:** `postbro_backend/analysis/tasks.py`

**Changes:**
- Replace direct import: `from analysis.services.gemini_service import analyze_post_with_gemini`
- Use dynamic import: `from analysis.services import get_analysis_service`
- Call: `analyze_post = get_analysis_service()` then `analyze_post(...)`

**Location:** Around line 652-704 where Gemini is called

---

### Phase 6: Environment Variables
**File:** `.env`

**Add:**
```bash
# Model Selection: 'openai' or 'gemini' (default: gemini)
USE_MODEL=openai

# OpenAI API Key
OPENAI_API_KEY=sk-proj-...

# Gemini API Key (keep existing)
GEMINI_API_KEY_1=...
```

---

### Phase 7: Dependencies
**File:** `postbro_backend/requirements.txt`

**Add:**
```
openai>=1.0.0
```

---

## File Structure After Implementation

```
postbro_backend/
├── analysis/
│   ├── services/
│   │   ├── __init__.py          # get_analysis_service() function
│   │   ├── prompt_utils.py      # Shared prompt building (NEW)
│   │   ├── gemini_service.py    # Updated (uses prompt_utils)
│   │   └── openai_service.py    # NEW - OpenAI service
│   ├── prompts/
│   │   └── v1.txt                # Same prompt template (unchanged)
│   └── tasks.py                  # Updated (uses get_analysis_service)
```

---

## Implementation Details

### OpenAI Service Structure

```python
# analysis/services/openai_service.py

from openai import OpenAI
from .prompt_utils import get_system_prompt, build_user_prompt
from analytics.tasks import log_external_api_call

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def analyze_post_with_openai(...):
    # 1. Build prompts (using shared functions)
    system_prompt = get_system_prompt()
    user_prompt = build_user_prompt(...)
    
    # 2. Call OpenAI API with caching
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},  # Gets cached!
            {"role": "user", "content": user_prompt}
        ],
        cache_control={"type": "ephemeral"},  # Enable input caching
        response_format={"type": "json_object"},  # Force JSON
        temperature=0.4,
    )
    
    # 3. Parse response (same JSON structure as Gemini)
    # 4. Log to analytics
    # 5. Return analysis result
```

### Key Differences: Gemini vs OpenAI

| Feature | Gemini | OpenAI |
|---------|--------|--------|
| **Client** | `genai.GenerativeModel()` | `OpenAI().chat.completions.create()` |
| **System Prompt** | `system_instruction` parameter | `messages[0]` with `role: "system"` |
| **JSON Format** | `response_mime_type="application/json"` | `response_format={"type": "json_object"}` |
| **Caching** | Not available | `cache_control={"type": "ephemeral"}` |
| **Response** | `response.text` | `response.choices[0].message.content` |
| **Usage Info** | `response.usage_metadata` | `response.usage` |

---

## Testing Plan

### 1. Unit Tests
- Test prompt building (shared utilities)
- Test OpenAI service with mock responses
- Test model selection logic

### 2. Integration Tests
- Test full analysis flow with OpenAI
- Test fallback to Gemini if OpenAI fails
- Test environment variable switching

### 3. Manual Testing
- ✅ Set `USE_MODEL=openai` → Process a post → Verify OpenAI is used
- ✅ Set `USE_MODEL=gemini` → Process a post → Verify Gemini is used
- ✅ Check analytics logs show correct service
- ✅ Verify JSON response structure matches Gemini

---

## Error Handling

### OpenAI-Specific Errors:
- **401 Unauthorized** → Invalid API key
- **429 Rate Limit** → Retry with exponential backoff
- **500 Server Error** → Retry (up to 3 times)
- **Invalid JSON** → Log error, provide defaults

### Fallback Strategy:
- If OpenAI fails and `USE_MODEL=openai`, log error and raise
- Consider adding fallback to Gemini if OpenAI fails (optional)

---

## Cost Considerations

### With Input Caching Enabled:
- **System prompt** (3,000 tokens) → $1.25/1M = $0.00375 (cached)
- **User prompt** (1,500 tokens) → $2.50/1M = $0.00375 (not cached)
- **Output** (2,400 tokens) → $10/1M = $0.024
- **Total per post: ~$0.0315** (with caching)

### Without Caching:
- **Total per post: ~$0.054**

**Savings with caching: ~42% on input costs**

---

## Migration Steps

1. ✅ Create `prompt_utils.py` with shared functions
2. ✅ Update `gemini_service.py` to use shared utilities
3. ✅ Create `openai_service.py` using shared utilities
4. ✅ Create `services/__init__.py` with `get_analysis_service()`
5. ✅ Update `tasks.py` to use `get_analysis_service()`
6. ✅ Add `openai` to `requirements.txt`
7. ✅ Add environment variables to `.env`
8. ✅ Test with both models
9. ✅ Update documentation

---

## Environment Variable Options

### Option 1: Simple String
```bash
USE_MODEL=openai  # or 'gemini'
```

### Option 2: With Default
```python
USE_MODEL = os.getenv('USE_MODEL', 'gemini').lower()
```

**Recommendation:** Option 2 (defaults to Gemini for backward compatibility)

---

## Backward Compatibility

- ✅ Default to Gemini if `USE_MODEL` not set
- ✅ Keep all existing Gemini code working
- ✅ No breaking changes to API or database
- ✅ Existing analyses continue to work

---

## Next Steps After Implementation

1. **Monitor Costs:**
   - Track OpenAI usage in analytics
   - Compare costs vs Gemini
   - Optimize prompt size if needed

2. **A/B Testing (Optional):**
   - Test quality differences between models
   - Compare response times
   - User feedback on analysis quality

3. **Advanced Features:**
   - Per-user model selection (premium feature?)
   - Automatic fallback if one model fails
   - Model performance metrics

---

## Estimated Time

- **Phase 1 (OpenAI Service):** 2-3 hours
- **Phase 2 (Shared Utils):** 30 minutes
- **Phase 3 (Update Gemini):** 30 minutes
- **Phase 4 (Model Selection):** 30 minutes
- **Phase 5 (Update Tasks):** 30 minutes
- **Phase 6-7 (Config):** 15 minutes
- **Testing:** 1-2 hours

**Total: ~5-7 hours**

---

## Approval Checklist

- [ ] Review plan and architecture
- [ ] Confirm environment variable name (`USE_MODEL`)
- [ ] Confirm OpenAI model (`gpt-4o`)
- [ ] Confirm caching strategy (ephemeral)
- [ ] Approve to proceed with implementation

---

*Ready to implement once approved!* 🚀






