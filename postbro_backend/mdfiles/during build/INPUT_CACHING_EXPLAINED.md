# Input Caching Explained - GPT-4o

## What is Input Caching?

**Input caching** is a feature from OpenAI that allows you to cache frequently used input tokens and pay a **50% discount** when those tokens are reused.

### How It Works

1. **First Request**: You send a prompt with tokens
   - OpenAI processes it and stores the input tokens in cache
   - You pay full price: **$2.50 per 1M tokens**

2. **Subsequent Requests**: You send the same (or similar) input tokens
   - OpenAI recognizes the cached tokens
   - You pay discounted price: **$1.25 per 1M tokens** (50% off!)

3. **Cache Duration**: Cached tokens stay valid for a period (typically hours/days)

---

## Why It's Perfect for PostBro

### Your Current Prompt Structure

Every analysis request in PostBro has:

1. **System Prompt** (~3,000 tokens) - **ALWAYS THE SAME**
   - Instructions on how to analyze posts
   - JSON schema definitions
   - Analysis guidelines
   - This is **identical for every request** ✅

2. **User Prompt** (~1,000-2,000 tokens) - **CHANGES PER POST**
   - Actual post data (caption, metrics, comments)
   - Platform-specific information
   - This is **different for each post** ❌

### Caching Impact

**Without Caching:**
- System prompt: 3,000 tokens × $2.50/1M = $0.0075 per request
- User prompt: 1,500 tokens × $2.50/1M = $0.00375 per request
- **Total input: $0.01125 per request**

**With Caching (after first request):**
- System prompt: 3,000 tokens × $1.25/1M = $0.00375 per request (cached)
- User prompt: 1,500 tokens × $2.50/1M = $0.00375 per request (not cached)
- **Total input: $0.0075 per request** (33% savings!)

**For 1,000 requests:**
- Without caching: $11.25
- With caching: $7.50
- **Savings: $3.75 (33% reduction)**

---

## Real-World Example

### Scenario: 100 Users Analyzing Posts Daily

**Daily Usage:**
- 100 users × 3 posts/day (average) = 300 requests/day

**Monthly Usage:**
- 300 requests/day × 30 days = 9,000 requests/month

**Cost Comparison:**

| Component | Without Caching | With Caching | Savings |
|-----------|----------------|--------------|---------|
| System prompt (3K tokens) | $67.50 | $33.75 | $33.75 |
| User prompt (1.5K tokens) | $33.75 | $33.75 | $0 |
| **Total Input Cost** | **$101.25** | **$67.50** | **$33.75** |
| Output cost (same) | $216.00 | $216.00 | $0 |
| **Total LLM Cost** | **$317.25** | **$283.50** | **$33.75/month** |

**Annual Savings: $405/year** just from input caching!

---

## How to Enable Input Caching

### OpenAI API Implementation

When using OpenAI's API, you need to:

1. **Use the `cache_control` parameter** in your API calls
2. **Set `cache_control.type = "ephemeral"`** for short-term caching
3. **Use the same system prompt** across requests

### Example Code (Python)

```python
from openai import OpenAI

client = OpenAI(api_key="your-key")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": system_prompt  # This gets cached
        },
        {
            "role": "user",
            "content": user_prompt  # This changes per request
        }
    ],
    cache_control={
        "type": "ephemeral"  # Enable caching
    }
)
```

### Important Notes

1. **Cache Key**: OpenAI uses the **exact content** of the system message as the cache key
   - If you change even one word, it's a new cache entry
   - Keep your system prompt **static** and **consistent**

2. **Cache Duration**: 
   - "ephemeral" = short-term (hours/days)
   - Cache expires automatically
   - No manual cache management needed

3. **Cache Hit Rate**:
   - System prompt: ~100% cache hit (same for all requests)
   - User prompt: ~0% cache hit (different per post)
   - **Overall: ~50-70% of input tokens cached** (depending on prompt structure)

---

## Cost Savings Breakdown for PostBro

### Per Post Analysis

**Input Tokens:**
- System prompt: 3,000 tokens (cached after first use)
- User prompt: 1,500 tokens (varies per post)
- Total: 4,500 tokens

**Cost Per Post:**
- **Without caching**: 4,500 × $2.50/1M = **$0.01125**
- **With caching**: (3,000 × $1.25 + 1,500 × $2.50) / 1M = **$0.0075**
- **Savings: $0.00375 per post (33%)**

### Monthly Impact (Based on Plans)

**Free Plan (90 posts/month):**
- Without caching: $1.01
- With caching: $0.68
- **Savings: $0.33/month**

**Basic Plan (300 posts/month):**
- Without caching: $3.38
- With caching: $2.25
- **Savings: $1.13/month**

**Pro Plan (900 posts/month):**
- Without caching: $10.13
- With caching: $6.75
- **Savings: $3.38/month**

---

## Implementation Checklist

### ✅ What You Need to Do

1. **Keep System Prompt Static**
   - Don't modify the system prompt between requests
   - Store it in a constant/variable
   - Use the same exact string every time

2. **Update Your OpenAI Client**
   - Add `cache_control` parameter to API calls
   - Use `cache_control={"type": "ephemeral"}`

3. **Monitor Cache Usage**
   - Check OpenAI dashboard for cache hit rates
   - Verify you're getting the discounted rate

4. **Test It**
   - Make 2-3 requests with same system prompt
   - Check billing to see cached vs non-cached costs

### 📝 Code Changes Needed

**Current (Gemini):**
```python
# No caching available in Gemini
model.generate_content(prompt)
```

**Future (GPT-4o with caching):**
```python
from openai import OpenAI

client = OpenAI(api_key=api_key)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},  # Cached
        {"role": "user", "content": user_prompt}      # Not cached
    ],
    cache_control={"type": "ephemeral"}  # Enable caching
)
```

---

## Bottom Line

**Input caching is like a "bulk discount" for repeated content.**

- ✅ **System prompts** (same for every request) → **50% discount**
- ❌ **User prompts** (different per post) → **Full price**
- 💰 **Overall savings: 30-50% on input costs**

**For PostBro:**
- Your system prompt is ~3,000 tokens (67% of input)
- With caching, you save ~33% on total input costs
- **This makes your pricing profitable even at 100% usage!**

---

*Last Updated: Based on GPT-4o pricing and PostBro prompt structure*






