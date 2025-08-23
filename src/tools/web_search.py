import json
from typing import Optional, List, Dict, Any
from duckduckgo_search import DDGS
import aiohttp
import trafilatura  # for "readable" mode extraction

class WebTools:
    """Exactly two tools: duckduckgo_search and fetch_url_content."""

    async def duckduckgo_search(
        self,
        keywords: str,
        max_results: Optional[int] = 10,
        region: Optional[str] = "wt-wt",
    ) -> List[Dict[str, Any]]:
        max_results = 1 if max_results is None else max(1, min(int(max_results), 20))
        out: List[Dict[str, Any]] = []
        
        # Use DDGS synchronously in an async context
        with DDGS() as ddgs:
            results = ddgs.text(keywords, region=region, max_results=max_results)
            for r in results:
                # DDGS uses 'href' for url, 'body' for snippet
                out.append({
                    "title": r.get("title") or "",
                    "url": r.get("href") or r.get("url") or "",
                    "snippet": r.get("body") or "",
                    "source": "duckduckgo"
                })
        
        # de-dup by URL
        seen = set(); uniq = []
        for x in out:
            u = x["url"]
            if u and u not in seen:
                seen.add(u); uniq.append(x)
        return uniq

    async def fetch_url_content(
        self,
        url: str,
        max_length: int = 5000,
        mode: str = "raw",  # "raw" returns HTML text; "readable" returns extracted article text
    ) -> str:
        timeout = aiohttp.ClientTimeout(total=20)
        headers = {"User-Agent": "Mozilla/5.0 (compatible; MCPWebTools/1.0)"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as sess:
            async with sess.get(url, allow_redirects=True) as resp:
                resp.raise_for_status()
                html = await resp.text()

        if mode == "readable":
            # robust readability extraction (plain text)
            extracted = trafilatura.extract(html, include_comments=False, include_links=False, url=url)
        # default: raw HTML
        else:
            extracted = html

        # Truncate content if it's too long
        if len(extracted) > max_length:
            extracted = extracted[:max_length] + "..."

        return {
            'url': url,
            'status': 'success',
            'content': extracted,
            'length': len(extracted)
        }