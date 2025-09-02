from typing import Optional, List, Dict, Any

import trafilatura

from urllib.parse import urlparse

import aiohttp


class WebSearch:
    def __init__(self, brave_api_key: str, proxy: Optional[str] = None, timeout: int = 20, logger=None):
        self.brave_api_key = brave_api_key
        self.proxy = proxy
        self.timeout = timeout
        self.logger = logger


    async def brave_search(
        self,
        keywords: str,
        max_results: int = 10,
        country: Optional[str] = "us",      # e.g., "us", "fr", "sg" (2-letter)
        safesearch: str = "moderate",       # "off", "moderate", "strict"
        freshness: Optional[str] = None,    # "pd" (past day), "pw" (past week), "pm" (past month) | None
        search_lang: Optional[str] = None,  # e.g., "en", "fr"; None = auto
        mode: str = "web",                  # "web" (default) or "news"
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search Brave (official API) for results.

        Args:
            keywords: Search query
            max_results: Maximum number of results (API caps at 20)
            country: 2-letter country code (e.g., "us", "fr", "sg")
            safesearch: "off" | "moderate" | "strict"
            freshness: "pd" (past day) | "pw" (past week) | "pm" (past month) | None
            search_lang: 2-letter language code (e.g., "en", "fr") or None for auto
            mode: "web" or "news"
            offset: results offset for pagination (0-based)

        Returns:
            List of dicts with {title, url, snippet, source}
        """
        # Brave caps per call
        count = min(max_results, 20)

        # Endpoint selection
        base = "https://api.search.brave.com/res/v1"
        if mode == "news":
            url = f"{base}/news/search"
        else:
            url = f"{base}/web/search"

        params = {
            "q": keywords,
            "count": count,
            "offset": max(0, offset),
            "safesearch": safesearch,
        }
        if country:
            params["country"] = country
        if freshness:
            params["freshness"] = freshness
        if search_lang:
            params["search_lang"] = search_lang

        headers = {
            "X-Subscription-Token": self.brave_api_key,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": "ServerMCP/1.0",
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, params=params, proxy=self.proxy) as resp:
                    text = await resp.text()
                    if resp.status != 200:
                        # surface the body for debugging
                        raise RuntimeError(f"Brave API error {resp.status}: {text}")

                    data = await resp.json()

            # Normalize
            results: List[Dict[str, Any]] = []
            seen = set()

            if mode == "news":
                items = (data.get("results") or [])  # news top-level is "results"
                for it in items:
                    link = it.get("url") or ""
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    results.append({
                        "title": it.get("title", "").strip(),
                        "url": link,
                        "snippet": (it.get("description") or "").strip(),
                        "source": "brave_news"
                    })
            else:
                items = (data.get("web", {}) or {}).get("results", [])
                for it in items:
                    link = it.get("url") or ""
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    results.append({
                        "title": it.get("title", "").strip(),
                        "url": link,
                        "snippet": (it.get("description") or "").strip(),
                        "source": "brave"
                    })

            if callable(getattr(self.logger, "info", None)):
                self.logger.info(f"Brave search returned {len(results)} unique results for: {keywords}")

            return results

        except Exception as e:
            if callable(getattr(self.logger, "error", None)):
                self.logger.error(f"Brave search failed: {str(e)}")
            return [{
                "title": "Search Error",
                "url": "",
                "snippet": f"Search failed: {str(e)}",
                "source": "error"
            }]


    async def fetch_url_content(
        self,
        url: str,
        max_length: int = 5000,
        mode: str = "readable",  # "readable" (default) or "raw"
        include_links: bool = False,
        include_images: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch and extract content from a URL.
        Readable mode only returns textual content.
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {
                    'url': url,
                    'status': 'error',
                    'content': 'Invalid URL format',
                    'length': 0,
                    'error': 'Invalid URL format'
                }

            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True, ssl=False, proxy=self.proxy) as response:
                    response.raise_for_status()
                    html = await response.text()
                    final_url = str(response.url)
                    content_type = response.headers.get('content-type', '')

            if mode == "readable":
                extracted = trafilatura.extract(
                    html,
                    include_comments=False,
                    include_links=include_links,
                    include_images=include_images,
                    url=final_url,
                    favor_precision=True,
                )
                if not extracted:
                    extracted = "Content extraction failed - the page may not contain readable text"
            else:
                extracted = html

            if extracted and len(extracted) > max_length:
                extracted = extracted[:max_length] + "... [truncated]"

            return {
                'url': url,
                'final_url': final_url,
                'status': 'success',
                'content': extracted or "No content extracted",
                'length': len(extracted) if extracted else 0,
                'content_type': content_type,
                'mode': mode
            }

        except aiohttp.ClientError as e:
            error_msg = f"HTTP error: {str(e)}"
            if callable(getattr(self.logger, "error", None)):
                self.logger.error(f"Failed to fetch {url}: {error_msg}")
            return {
                'url': url,
                'status': 'error',
                'content': error_msg,
                'length': 0,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            if callable(getattr(self.logger, "error", None)):
                self.logger.error(f"Failed to fetch {url}: {error_msg}")