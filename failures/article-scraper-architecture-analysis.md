# Article Scraper Architecture Analysis

## Current Architecture (Synchronous)

**Flow:**
1. Frontend calls `/api/article-scraper`
2. Function checks cache
3. If cached: Return immediately ✓
4. If not cached: Scrape article → Save to cache → Return (WAIT)

**Cost Analysis:**
- **Cached requests**: ~100-500ms execution = Very cheap ✓
- **Uncached requests**: 2-10 seconds execution = More expensive ✗
- Azure Functions Consumption Plan charges: **GB-seconds** (memory × execution time)

## Problems with Current Approach

1. **User waits** for scraping to complete (poor UX)
2. **Function timeout risk** (default 5-10 min, but still risky)
3. **Higher cost** for long-running executions
4. **No retry mechanism** if scraping fails mid-execution
5. **Blocks other requests** if function is busy scraping

## Cheaper Alternatives

### Option 1: Async with Azure Queue Storage (RECOMMENDED)

**Architecture:**
```
Frontend → Function (immediate response) → Queue → Background Function → Cache
```

**Flow:**
1. Frontend calls `/api/article-scraper`
2. Function checks cache
3. If cached: Return immediately ✓
4. If not cached:
   - Return `{"status": "processing", "job_id": "..."}` immediately
   - Queue scraping job
   - Background function processes queue
   - Frontend polls `/api/article-status/{job_id}` or uses webhooks

**Cost:**
- Main function: ~200ms (just queues job) = **Much cheaper** ✓
- Queue storage: ~$0.000001 per message = **Negligible** ✓
- Background function: Same cost as current, but doesn't block user ✓

**Pros:**
- ✅ Faster user response
- ✅ Cheaper (shorter main function execution)
- ✅ Better UX (user doesn't wait)
- ✅ Retry mechanism built into queues
- ✅ Scales better

**Cons:**
- ❌ More complex (requires polling/webhooks)
- ❌ Frontend needs to handle async flow

### Option 2: Pre-scraping on RSS Feed Parse

**Architecture:**
```
RSS Feed Parse → Scrape all articles → Cache → User requests → Return cached
```

**Flow:**
1. When RSS feed is parsed, scrape all articles in background
2. Store in cache
3. User requests article → Always cached → Instant response

**Cost:**
- Same total scraping cost
- But spread over time (not blocking user requests)
- User gets instant responses ✓

**Pros:**
- ✅ Instant article responses
- ✅ No user waiting
- ✅ Simpler frontend code

**Cons:**
- ❌ Scrapes articles users might never view (waste)
- ❌ RSS feed parsing takes longer
- ❌ More complex RSS parser function

### Option 3: Hybrid Approach

**Architecture:**
```
Request → Check cache → If cached: return
         → If not cached: return "not available" + trigger async scrape
         → User can refresh later
```

**Flow:**
1. Frontend requests article
2. If cached: Return immediately ✓
3. If not cached:
   - Return `{"available": false, "scraping": true}`
   - Trigger async scrape (queue or direct async call)
   - Frontend shows "Loading..." or allows refresh

**Cost:**
- Similar to Option 1
- Main function stays fast ✓

**Pros:**
- ✅ Fast response
- ✅ User knows status
- ✅ Can refresh when ready

**Cons:**
- ❌ Still requires async handling
- ❌ User might need to refresh

## Recommendation

**For your use case (Finnish news reader):**

**Option 1 (Async Queue)** is best because:
1. **Cost**: Main function execution time drops from 2-10s to ~200ms = **90% cost reduction** for uncached requests
2. **UX**: User gets immediate feedback
3. **Scalability**: Can handle many concurrent requests
4. **Reliability**: Queue provides retry mechanism

**Implementation:**
- Use Azure Queue Storage (very cheap)
- Create background function `article-scraper-worker`
- Main function just queues jobs
- Frontend polls status endpoint or uses Server-Sent Events

**Cost Comparison:**
- Current: 10s execution × 1GB = 10 GB-seconds per uncached request
- Async: 0.2s execution × 1GB = 0.2 GB-seconds per request
- **Savings: 98% reduction** in main function cost

**When to use current approach:**
- If scraping is very fast (< 1 second)
- If you want simplicity over cost
- If articles are almost always cached

## Azure Functions Pricing Context

- **Consumption Plan**: Pay per execution (GB-seconds)
- **1M requests/month free** (first 1M)
- **After free tier**: ~$0.000016 per GB-second
- **Example**: 10s × 1GB = $0.00016 per uncached request
- **With async**: 0.2s × 1GB = $0.0000032 per request

**For 1000 uncached requests/month:**
- Current: $0.16/month
- Async: $0.0032/month
- **Savings: $0.16/month** (not huge, but scales with traffic)

## Conclusion

**Current approach is fine IF:**
- Most articles are cached (80%+ cache hit rate)
- Scraping is fast (< 2 seconds)
- You want simplicity

**Switch to async IF:**
- High uncached request rate
- Scraping takes > 3 seconds
- You want better UX
- You're hitting cost concerns

For a news reader where users browse articles, **high cache hit rate is expected**, so current approach might be fine. But async is better for scalability and UX.

