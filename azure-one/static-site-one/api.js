async function fetchRSSFeed(forceReload = false) {
    const authHeaders = getAuthHeaders();
    if (!authHeaders) {
        throw new Error('Authentication required');
    }
    
    let url;
    let options;
    
    if (CONFIG.isLocalDev) {
        url = `${CONFIG.apiBaseUrl}/rss-feed`;
        if (forceReload) {
            url += '?force_reload=true';
        }
        options = {
            headers: authHeaders
        };
    } else {
        url = `${CONFIG.apiBaseUrl}/rss-feed-parser`;
        if (forceReload) {
            url += '?force_reload=true';
        }
        options = {
            headers: authHeaders
        };
    }
    
    const response = await fetch(url, options);
    
    if (!response.ok) {
        if (response.status === 401) {
            window.location.href = 'index.html';
            return null;
        }
        throw new Error(`Failed to load RSS feed: ${response.statusText}`);
    }
    
    return await response.json();
}

async function fetchArticle(shortcode, lang = 'fi') {
    const authHeaders = getAuthHeaders();
    if (!authHeaders) {
        throw new Error('Authentication required');
    }
    
    let url;
    let options;
    
    if (CONFIG.isLocalDev) {
        url = `${CONFIG.apiBaseUrl}/article/${shortcode}/${lang}`;
        options = {
            headers: authHeaders
        };
    } else {
        url = `${CONFIG.apiBaseUrl}/article-scraper`;
        options = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders
            },
            body: JSON.stringify({
                urls: [`https://yle.fi/a/${shortcode}`],
                language_code: lang
            })
        };
    }
    
    const response = await fetch(url, options);
    
    if (!response.ok) {
        if (response.status === 401) {
            window.location.href = 'index.html';
            return null;
        }
        if (response.status === 404) {
            return null;
        }
        throw new Error(`Failed to load article: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // For Azure API, extract the first result from results array
    if (!CONFIG.isLocalDev) {
        if (data.results && Array.isArray(data.results) && data.results.length > 0) {
            const result = data.results[0];
            if (result && result.success) {
                return result;
            }
        }
        // If we're in Azure mode but don't have results array, return null
        return null;
    }
    
    // For local dev, return data as-is
    return data;
}

async function checkArticleExists(shortcode, lang = 'fi') {
    const authHeaders = getAuthHeaders();
    if (!authHeaders) {
        return false;
    }
    
    if (CONFIG.isLocalDev) {
        const response = await fetch(`${CONFIG.apiBaseUrl}/article/${shortcode}/${lang}`, {
            method: 'HEAD',
            headers: authHeaders
        });
        return response.ok;
    } else {
        try {
            const article = await fetchArticle(shortcode, lang);
            return article !== null;
        } catch (error) {
            return false;
        }
    }
}

async function translateArticle(articleId, sourceLang, targetLang, paragraphs) {
    const authHeaders = getAuthHeaders();
    if (!authHeaders) {
        throw new Error('Authentication required');
    }
    
    const url = `${CONFIG.translatorApiUrl}/translate-article`;
    const options = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...authHeaders
        },
        body: JSON.stringify({
            article_id: articleId,
            source_lang: sourceLang,
            target_lang: targetLang,
            paragraphs: paragraphs
        })
    };
    
    const response = await fetch(url, options);
    
    if (!response.ok) {
        if (response.status === 401) {
            window.location.href = 'index.html';
            return null;
        }
        if (response.status === 429) {
            throw new Error('Rate limit exceeded. Please try again later.');
        }
        throw new Error(`Failed to translate article: ${response.statusText}`);
    }
    
    return await response.json();
}

let quotaCache = null;
let quotaCacheTimestamp = null;

async function fetchTranslatorQuota(forceRefresh = false) {
    const cacheHours = CONFIG.quotaCacheHours || 2;
    const cacheMs = cacheHours * 60 * 60 * 1000;
    const now = Date.now();
    
    if (!forceRefresh && quotaCache && quotaCacheTimestamp && (now - quotaCacheTimestamp) < cacheMs) {
        return quotaCache;
    }
    
    const authHeaders = getAuthHeaders();
    if (!authHeaders) {
        throw new Error('Authentication required');
    }
    
    const url = `${CONFIG.translatorApiUrl}/translator-quota`;
    const options = {
        headers: authHeaders
    };
    
    const response = await fetch(url, options);
    
    if (!response.ok) {
        if (response.status === 401) {
            window.location.href = 'index.html';
            return null;
        }
        throw new Error(`Failed to load quota: ${response.statusText}`);
    }
    
    const quotaData = await response.json();
    quotaCache = quotaData;
    quotaCacheTimestamp = now;
    
    return quotaData;
}
