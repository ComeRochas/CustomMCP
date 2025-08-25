import json
import asyncio
from typing import Optional, List, Dict, Any
from duckduckgo_search import DDGS
import aiohttp
import trafilatura
import logging
from urllib.parse import urlparse

class WebTools:
    """Exactly two tools: duckduckgo_search and fetch_url_content."""

    def __init__(self, proxy: Optional[str] = None, timeout: int = 20):
        """
        Initialize WebTools with optional proxy and timeout settings.
        
        Args:
            proxy: Optional proxy string (e.g., "http://user:pass@example.com:3128")
            timeout: Request timeout in seconds
        """
        self.proxy = proxy
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    async def duckduckgo_search(
        self,
        keywords: str,
        max_results: int = 10,
        region: Optional[str] = "wt-wt",  # wt-wt = worldwide, more reliable than fr-fr
        safesearch: str = "moderate",     # off, moderate, strict
        timelimit: Optional[str] = None,  # d, w, m, y (day, week, month, year)
    ) -> List[Dict[str, Any]]:
        """
        Search DuckDuckGo for text results.
        
        Args:
            keywords: Search query
            max_results: Maximum number of results (capped at 20)
            region: Search region (wt-wt for worldwide, us-en for US English, etc.)
            safesearch: Safe search setting (off, moderate, strict)
            timelimit: Time limit for results (d, w, m, y)
            
        Returns:
            List of search results with title, url, snippet, and source
        """
        max_results = min(max_results, 20)  # API limitation
        results = []
        
        try:
            # Run DDGS in thread pool to avoid blocking async event loop
            loop = asyncio.get_event_loop()
            ddgs_results = await loop.run_in_executor(
                None, 
                self._search_sync,
                keywords,
                max_results,
                region,
                safesearch,
                timelimit
            )
            
            # Process and deduplicate results
            seen_urls = set()
            for result in ddgs_results:
                url = result.get("href") or result.get("url") or ""
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    results.append({
                        "title": result.get("title", "").strip(),
                        "url": url,
                        "snippet": result.get("body", "").strip(),
                        "source": "duckduckgo"
                    })
            
            self.logger.info(f"DuckDuckGo search returned {len(results)} unique results for: {keywords}")
            return results
            
        except Exception as e:
            self.logger.error(f"DuckDuckGo search failed: {str(e)}")
            return [{
                "title": "Search Error",
                "url": "",
                "snippet": f"Search failed: {str(e)}",
                "source": "error"
            }]

    def _search_sync(self, keywords: str, max_results: int, region: str, safesearch: str, timelimit: Optional[str]) -> List[Dict]:
        """Synchronous search helper to run in thread pool."""
        try:
            with DDGS(proxy=self.proxy) as ddgs:
                return list(ddgs.text(
                    keywords=keywords,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=max_results
                ))
        except Exception as e:
            self.logger.error(f"DDGS sync search error: {str(e)}")
            return []

    async def fetch_url_content(
        self,
        url: str,
        max_length: int = 5000,
        mode: str = "readable",  # "readable" (default) or "raw"
        include_links: bool = False,
        include_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetch and extract content from a URL.
        
        Args:
            url: Target URL to fetch
            max_length: Maximum content length
            mode: "readable" for clean text extraction, "raw" for HTML
            include_links: Whether to preserve links in readable mode
            include_images: Whether to preserve image info in readable mode
            
        Returns:
            Dictionary with url, status, content, length, and metadata
        """
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {
                    'url': url,
                    'status': 'error',
                    'content': 'Invalid URL format',
                    'length': 0,
                    'error': 'Invalid URL format'
                }

            # Fetch content
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True, ssl=False) as response:
                    response.raise_for_status()
                    html = await response.text()
                    final_url = str(response.url)
                    content_type = response.headers.get('content-type', '')

            # Extract content based on mode
            if mode == "readable":
                extracted = trafilatura.extract(
                    html,
                    include_comments=False,
                    include_links=include_links,
                    include_images=include_images,
                    url=final_url,
                    favor_precision=True,  # Better quality extraction
                )
                if not extracted:
                    # Fallback if trafilatura fails
                    extracted = "Content extraction failed - the page may not contain readable text"
            else:
                extracted = html

            # Truncate if too long
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
            self.logger.error(f"Failed to fetch {url}: {error_msg}")
            return {
                'url': url,
                'status': 'error', 
                'content': error_msg,
                'length': 0,
                'error': error_msg
            }

    # Convenience methods for specific search types
    async def search_recent(self, keywords: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for recent results (past week)."""
        return await self.duckduckgo_search(keywords, max_results, timelimit="w")

    async def search_images_info(self, keywords: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for images (returns metadata, not actual images).
        Note: This would require extending DDGS to use .images() method.
        """
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                self._search_images_sync,
                keywords,
                max_results
            )
            
            return [{
                "title": result.get("title", ""),
                "url": result.get("image", ""),
                "source_url": result.get("source", ""),
                "thumbnail": result.get("thumbnail", ""),
                "width": result.get("width"),
                "height": result.get("height"),
                "source": "duckduckgo_images"
            } for result in results]
            
        except Exception as e:
            self.logger.error(f"Image search failed: {str(e)}")
            return []

    def _search_images_sync(self, keywords: str, max_results: int) -> List[Dict]:
        """Synchronous image search helper."""
        try:
            with DDGS(proxy=self.proxy) as ddgs:
                return list(ddgs.images(
                    keywords=keywords,
                    max_results=max_results
                ))
        except Exception as e:
            self.logger.error(f"DDGS image search error: {str(e)}")
            return []