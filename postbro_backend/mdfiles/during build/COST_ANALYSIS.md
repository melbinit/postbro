# PostBro Cost Analysis - Per Post Processing

This document provides detailed cost estimates for processing social media posts in PostBro.

## Quick Summary

### Cost Per Single Post

| LLM Provider | Instagram/X | YouTube |
|--------------|-------------|---------|
| **Gemini (Free)** | **$0.028** | **$0.04** |
| **GPT-4o** | **$0.062** | **$0.074** |
| **GPT-4 Turbo** | **$0.14** | **$0.152** |
| **GPT-3.5 Turbo** | **$0.034** | **$0.046** |

### Cost Per 10 Posts

| LLM Provider | Instagram/X | YouTube |
|--------------|-------------|---------|
| **Gemini (Free)** | **$0.28** | **$0.40** |
| **GPT-4o** | **$0.62** | **$0.74** |
| **GPT-4 Turbo** | **$1.40** | **$1.52** |
| **GPT-3.5 Turbo** | **$0.34** | **$0.46** |

**Breakdown:**
- Scraper API: $0.003-0.04 per post (depends on platform)
- LLM Analysis: $0-0.112 per post (depends on provider)
- Storage: ~$0.00002 per post (negligible)

---

## Overview

**Processing Flow:**
1. Scrape post data (Instagram/YouTube via BrightData, Twitter via TwitterAPI.io)
2. Analyze with LLM (currently Gemini, but estimates for OpenAI included)
3. Store results in Supabase (database + storage)

---

## 1. Scraper API Costs

### BrightData (Instagram & YouTube)

**Pricing Structure:**
- **Pay-as-you-go**: ~$0.01-0.05 per successful request
- **Instagram Dataset**: Typically $0.02-0.03 per post scrape
- **YouTube Dataset**: Typically $0.03-0.05 per video scrape (includes transcript extraction)

**Per Post Cost:**
- **Instagram**: ~$0.025 per post
- **YouTube**: ~$0.04 per post (includes video processing, transcript, frame extraction)

**Note:** BrightData charges per successful scrape. Failed requests may still incur costs depending on your plan.

### TwitterAPI.io (Twitter/X)

**Pricing Structure:**
- **Starter Plan**: $49/month for 10,000 requests = **$0.0049 per request**
- **Growth Plan**: $149/month for 50,000 requests = **$0.00298 per request**
- **Pro Plan**: $499/month for 200,000 requests = **$0.0025 per request**

**Per Post Cost:**
- **Conservative estimate**: $0.003-0.005 per tweet

**Note:** TwitterAPI.io pricing is based on monthly quotas. Unused requests don't roll over.

---

## 2. LLM Costs (AI Analysis)

### Current Setup: Gemini 2.0 Flash (Free Tier)
- **Cost**: $0 (free tier available)
- **Limits**: 15 requests per minute, 1,500 requests per day

### If Switching to OpenAI

#### Prompt Size Analysis

**System Prompt:**
- Template file: ~12,000 characters (~3,000 tokens) *[Actual: 11,981 bytes]*
- Static instructions and JSON schema

**User Prompt (per post):**
- Base template: ~2,000 characters (~500 tokens)
- Post data (caption, metrics, comments): ~500-2,000 characters (~125-500 tokens)
- YouTube transcript: ~500-5,000 characters (~125-1,250 tokens) *if applicable*
- Media URLs: ~100-500 characters (~25-125 tokens)
- JSON format instructions: ~500 characters (~125 tokens)

**Total Input Tokens per Post:**
- **Instagram/X**: ~3,500-4,000 tokens
- **YouTube** (with transcript): ~4,500-6,500 tokens

#### Response Size Analysis

**JSON Response Structure:**
- Quick takeaways: ~200 tokens
- Content observation: ~300 tokens
- Virality reasoning: ~200 tokens
- Analysis (hook, structure, psychology): ~600 tokens
- Replicable elements: ~200 tokens
- Strengths/weaknesses: ~150 tokens
- Improvements: ~150 tokens
- Future suggestions (5 items): ~500 tokens
- Viral formula: ~50 tokens
- Metadata: ~50 tokens

**Total Output Tokens per Post:**
- **Average**: ~2,400 tokens
- **Maximum** (detailed analysis): ~3,000 tokens

### OpenAI Pricing (as of 2025)

#### GPT-4 Turbo
- **Input**: $10.00 per 1M tokens
- **Output**: $30.00 per 1M tokens

**Cost per Post:**
- Input: 4,000 tokens × $10/1M = **$0.04**
- Output: 2,400 tokens × $30/1M = **$0.072**
- **Total: ~$0.112 per post**

#### GPT-4o (Optimized)
- **Input**: $2.50 per 1M tokens
- **Output**: $10.00 per 1M tokens

**Cost per Post:**
- Input: 4,000 tokens × $2.50/1M = **$0.01**
- Output: 2,400 tokens × $10/1M = **$0.024**
- **Total: ~$0.034 per post**

#### GPT-3.5 Turbo (Cheaper Alternative)
- **Input**: $0.50 per 1M tokens
- **Output**: $1.50 per 1M tokens

**Cost per Post:**
- Input: 4,000 tokens × $0.50/1M = **$0.002**
- Output: 2,400 tokens × $1.50/1M = **$0.0036**
- **Total: ~$0.0056 per post**

**Note:** GPT-3.5 may have lower quality analysis compared to GPT-4.

### Anthropic Claude (Alternative)

#### Claude 3.5 Sonnet
- **Input**: $3.00 per 1M tokens
- **Output**: $15.00 per 1M tokens

**Cost per Post:**
- Input: 4,000 tokens × $3/1M = **$0.012**
- Output: 2,400 tokens × $15/1M = **$0.036**
- **Total: ~$0.048 per post**

---

## 3. Storage & Database Costs

### Supabase Storage

**What We Store Per Post:**

1. **Post Data** (in `social.Post`):
   - Content (caption): ~500 bytes - 5 KB
   - Metrics (JSON): ~200 bytes
   - Transcript (YouTube): ~5-50 KB (if applicable)
   - Formatted transcript (JSON): ~10-100 KB (if applicable)
   - **Total: ~1-150 KB per post**

2. **Analysis Results** (in `analysis.PostAnalysis`):
   - Quick takeaways (JSON): ~2 KB
   - Content observation (JSON): ~3 KB
   - Analysis data (JSON): ~5 KB
   - Replicable elements (JSON): ~2 KB
   - Suggestions (JSON): ~4 KB
   - Raw LLM response: ~8 KB
   - **Total: ~24 KB per analysis**

3. **Media Files** (in `social.PostMedia`):
   - Images: ~50-500 KB per image (if stored)
   - Video frames: ~100-500 KB per frame (if extracted)
   - **Total: ~0-2 MB per post** (if media is stored)

**Database Storage Per Post:**
- **Without media**: ~25-175 KB
- **With media** (if stored): ~25 KB + media size

### Supabase Pricing

**Free Tier:**
- 500 MB database storage
- 1 GB file storage
- **Cost: $0/month**

**Pro Plan ($25/month):**
- 8 GB database storage included
- 100 GB file storage included
- Additional storage: $0.125/GB database, $0.021/GB files

**Storage Cost Calculation:**

**Per 1,000 Posts (without media):**
- Database: ~175 MB (0.175 GB)
- **Cost on Pro Plan**: $0 (within 8 GB limit)
- **Cost if over limit**: 0.175 GB × $0.125 = **$0.022**

**Per 1,000 Posts (with media, assuming 1 MB avg per post):**
- Database: ~175 MB (0.175 GB)
- Files: ~1 GB
- **Cost on Pro Plan**: $0 (within limits)
- **Cost if over limit**: 
  - Database: 0.175 GB × $0.125 = $0.022
  - Files: 1 GB × $0.021 = $0.021
  - **Total: $0.043**

**Per Post Storage Cost:**
- **Without media**: ~$0.000022 per post (negligible)
- **With media**: ~$0.000043 per post (negligible)

**Note:** Storage costs are negligible for most use cases. The main costs are API calls.

---

## Total Cost Breakdown

### Per Single Post

| Component | Instagram/X | YouTube |
|-----------|-------------|---------|
| **Scraper API** | | |
| - Instagram (BrightData) | $0.025 | - |
| - YouTube (BrightData) | - | $0.04 |
| - Twitter (TwitterAPI.io) | $0.003 | - |
| **LLM Analysis** | | |
| - Gemini (Free) | $0.00 | $0.00 |
| - GPT-4 Turbo | $0.112 | $0.112 |
| - GPT-4o | $0.034 | $0.034 |
| - GPT-3.5 Turbo | $0.0056 | $0.0056 |
| - Claude 3.5 Sonnet | $0.048 | $0.048 |
| **Storage** | $0.00002 | $0.00002 |
| **TOTAL (Gemini)** | **$0.028** | **$0.04** |
| **TOTAL (GPT-4 Turbo)** | **$0.140** | **$0.152** |
| **TOTAL (GPT-4o)** | **$0.062** | **$0.074** |
| **TOTAL (GPT-3.5)** | **$0.034** | **$0.046** |

### Per 10 Posts

| Component | Instagram/X | YouTube |
|-----------|-------------|---------|
| **Scraper API** | | |
| - Instagram (BrightData) | $0.25 | - |
| - YouTube (BrightData) | - | $0.40 |
| - Twitter (TwitterAPI.io) | $0.03 | - |
| **LLM Analysis** | | |
| - Gemini (Free) | $0.00 | $0.00 |
| - GPT-4 Turbo | $1.12 | $1.12 |
| - GPT-4o | $0.34 | $0.34 |
| - GPT-3.5 Turbo | $0.056 | $0.056 |
| - Claude 3.5 Sonnet | $0.48 | $0.48 |
| **Storage** | $0.0002 | $0.0002 |
| **TOTAL (Gemini)** | **$0.28** | **$0.40** |
| **TOTAL (GPT-4 Turbo)** | **$1.40** | **$1.52** |
| **TOTAL (GPT-4o)** | **$0.62** | **$0.74** |
| **TOTAL (GPT-3.5)** | **$0.34** | **$0.46** |

---

## Cost Optimization Strategies

### 1. Scraper API Costs

**BrightData:**
- Use batch requests when possible
- Cache scraped data (avoid re-scraping same posts)
- Monitor success rates to minimize failed request costs

**TwitterAPI.io:**
- Choose plan based on volume (Growth plan at $0.003/request is better for 10+ posts/day)
- Consider annual plans for discounts

### 2. LLM Costs

**Current (Gemini Free):**
- ✅ **Best option** for MVP/testing
- Rotate API keys if hitting rate limits
- Monitor usage to stay within free tier

**If Switching to Paid LLM:**
- **GPT-3.5 Turbo**: 80% cost savings vs GPT-4, acceptable quality for most use cases
- **GPT-4o**: Best balance of cost and quality (60% cheaper than GPT-4 Turbo)
- **Batch processing**: Process multiple posts in single request if API supports
- **Caching**: Cache analysis results for identical posts

### 3. Storage Costs

- **Media storage is optional**: Only store if needed for analysis
- **Cleanup old data**: Archive or delete old analyses after retention period
- **Compression**: Compress JSON data if storing large amounts

---

## Monthly Cost Estimates

### Scenario 1: 100 Posts/Month (Mix of Platforms)

**Using Gemini (Free):**
- Scraper: ~$2.50 (mix of Instagram/YouTube/Twitter)
- LLM: $0
- Storage: $0.002
- **Total: ~$2.50/month**

**Using GPT-4o:**
- Scraper: ~$2.50
- LLM: ~$6.20 (100 posts × $0.062 avg)
- Storage: $0.002
- **Total: ~$8.70/month**

**Using GPT-4 Turbo:**
- Scraper: ~$2.50
- LLM: ~$14.00 (100 posts × $0.14 avg)
- Storage: $0.002
- **Total: ~$16.50/month**

### Scenario 2: 1,000 Posts/Month

**Using Gemini (Free):**
- Scraper: ~$25
- LLM: $0
- Storage: $0.02
- **Total: ~$25/month**

**Using GPT-4o:**
- Scraper: ~$25
- LLM: ~$62
- Storage: $0.02
- **Total: ~$87/month**

**Using GPT-4 Turbo:**
- Scraper: ~$25
- LLM: ~$140
- Storage: $0.02
- **Total: ~$165/month**

### Scenario 3: 10,000 Posts/Month (High Volume)

**Using Gemini (Free):**
- Scraper: ~$250
- LLM: $0
- Storage: $0.20
- **Total: ~$250/month**

**Using GPT-4o:**
- Scraper: ~$250
- LLM: ~$620
- Storage: $0.20
- **Total: ~$870/month**

**Using GPT-4 Turbo:**
- Scraper: ~$250
- LLM: ~$1,400
- Storage: $0.20
- **Total: ~$1,650/month**

---

## Recommendations

### For MVP/Testing Phase
✅ **Use Gemini Free Tier**
- Cost: ~$0.03 per post (scraper only)
- No LLM costs
- Perfect for validation

### For Production (Low-Medium Volume)
✅ **Use GPT-4o**
- Best cost/quality balance
- ~$0.062 per post total
- Professional quality analysis

### For Production (High Volume)
✅ **Use GPT-3.5 Turbo or Claude 3.5 Sonnet**
- Lower cost per post (~$0.005-0.045)
- Still good quality
- Consider caching strategies

### Cost-Saving Tips

1. **Cache Analysis Results**: Don't re-analyze identical posts
2. **Batch Processing**: Process multiple posts in single LLM call if possible
3. **Smart Scraping**: Only scrape what you need (avoid unnecessary data)
4. **Storage Optimization**: Don't store media unless necessary
5. **Monitor Usage**: Track costs with analytics to optimize

---

## Notes

- **Scraper costs are fixed** - you pay per post scraped regardless of analysis
- **LLM costs scale with usage** - more posts = more costs
- **Storage costs are negligible** - only matters at very high volumes
- **Pricing may vary** - check current API pricing before production
- **Volume discounts** - negotiate with API providers for high-volume usage

---

*Last Updated: November 2025*
*Based on current API pricing and codebase analysis*

