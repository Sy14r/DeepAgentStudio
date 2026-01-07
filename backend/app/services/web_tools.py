"""
Web Tools for Agent Research
Provides web search and content fetching capabilities.
"""
import json
import re
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import StructuredTool, BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Constants
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DEFAULT_TIMEOUT = 30
MAX_CONTENT_LENGTH = 50000  # Max characters to return


# ============= Input Schemas =============

class WebSearchInput(BaseModel):
    """Input schema for web search"""
    query: str = Field(description="The search query")
    max_results: int = Field(default=5, description="Maximum number of results (1-10)")


class WebFetchInput(BaseModel):
    """Input schema for web fetch"""
    url: str = Field(description="URL to fetch content from")
    extract_text: bool = Field(default=True, description="Extract text content (strip HTML)")
    include_links: bool = Field(default=False, description="Include links in output")
    max_length: int = Field(default=10000, description="Maximum content length to return")


# ============= Search Implementations =============

def _search_duckduckgo(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search using DuckDuckGo HTML (no API key required).

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        List of search results with title, url, snippet
    """
    try:
        # Use DuckDuckGo HTML search
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            response = client.post(url, data={"q": query}, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # Parse search results
        for result in soup.select(".result")[:max_results]:
            title_elem = result.select_one(".result__title a")
            snippet_elem = result.select_one(".result__snippet")

            if title_elem:
                result_url = title_elem.get("href", "")
                # DuckDuckGo uses redirect URLs, extract actual URL
                if "uddg=" in result_url:
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(result_url).query)
                    result_url = parsed.get("uddg", [result_url])[0]

                results.append({
                    "title": title_elem.get_text(strip=True),
                    "url": result_url,
                    "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                })

        return results

    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []


def _search_tavily(query: str, max_results: int = 5, api_key: str = None) -> List[Dict[str, str]]:
    """
    Search using Tavily API (requires API key).

    Args:
        query: Search query
        max_results: Maximum number of results
        api_key: Tavily API key

    Returns:
        List of search results with title, url, snippet
    """
    if not api_key:
        raise ValueError("Tavily API key required")

    try:
        url = "https://api.tavily.com/search"
        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }

        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:500]  # Limit snippet length
            })

        return results

    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        raise


# ============= Web Search Tool =============

def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for information.

    Uses DuckDuckGo by default (free, no API key required).
    Can optionally use Tavily for better quality if API key is configured.

    Args:
        query: Search query string
        max_results: Maximum number of results (1-10)

    Returns:
        JSON formatted search results
    """
    import os

    # Validate max_results
    max_results = max(1, min(10, max_results))

    results = []
    source = "duckduckgo"

    # Try Tavily first if API key is available
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key:
        try:
            results = _search_tavily(query, max_results, tavily_key)
            source = "tavily"
        except Exception as e:
            logger.warning(f"Tavily failed, falling back to DuckDuckGo: {e}")

    # Fall back to DuckDuckGo
    if not results:
        results = _search_duckduckgo(query, max_results)
        source = "duckduckgo"

    if not results:
        return json.dumps({
            "success": False,
            "error": "No search results found",
            "query": query
        }, indent=2)

    return json.dumps({
        "success": True,
        "source": source,
        "query": query,
        "count": len(results),
        "results": results
    }, indent=2)


# ============= Web Fetch Tool =============

def _clean_html_to_text(html: str, include_links: bool = False) -> str:
    """
    Clean HTML and extract readable text.

    Args:
        html: HTML content
        include_links: Whether to preserve links as markdown

    Returns:
        Cleaned text content
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, and other non-content elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
        element.decompose()

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith("<!--")):
        comment.extract()

    if include_links:
        # Convert links to markdown format
        for a in soup.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            href = a["href"]
            if link_text and href and not href.startswith(("#", "javascript:")):
                a.replace_with(f"[{link_text}]({href})")

    # Get text content
    text = soup.get_text(separator="\n", strip=True)

    # Clean up whitespace
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)

    # Remove excessive blank lines
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned


def web_fetch(url: str, extract_text: bool = True, include_links: bool = False, max_length: int = 10000) -> str:
    """
    Fetch content from a URL.

    Args:
        url: URL to fetch
        extract_text: Whether to extract text from HTML (default True)
        include_links: Whether to include links as markdown (default False)
        max_length: Maximum content length to return (default 10000)

    Returns:
        JSON formatted response with content
    """
    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        if not parsed.netloc:
            return json.dumps({
                "success": False,
                "error": "Invalid URL format",
                "url": url
            }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"URL parsing error: {str(e)}",
            "url": url
        }, indent=2)

    # Validate max_length
    max_length = max(100, min(MAX_CONTENT_LENGTH, max_length))

    try:
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }

        with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()

        # Handle different content types
        if "application/json" in content_type:
            try:
                json_content = response.json()
                content = json.dumps(json_content, indent=2)
            except:
                content = response.text
            content_format = "json"
        elif "text/html" in content_type and extract_text:
            content = _clean_html_to_text(response.text, include_links)
            content_format = "text"
        else:
            content = response.text
            content_format = "raw"

        # Truncate if needed
        truncated = False
        if len(content) > max_length:
            content = content[:max_length] + "\n\n... [Content truncated]"
            truncated = True

        return json.dumps({
            "success": True,
            "url": str(response.url),  # Final URL after redirects
            "status_code": response.status_code,
            "content_type": content_type,
            "content_format": content_format,
            "content_length": len(content),
            "truncated": truncated,
            "content": content
        }, indent=2)

    except httpx.TimeoutException:
        return json.dumps({
            "success": False,
            "error": "Request timed out",
            "url": url
        }, indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({
            "success": False,
            "error": f"HTTP error: {e.response.status_code}",
            "url": url
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "url": url
        }, indent=2)


# ============= Tool Factory =============

def create_web_search_tool() -> BaseTool:
    """Create the web search tool."""
    return StructuredTool.from_function(
        func=web_search,
        name="web_search",
        description=(
            "Search the web for information. Returns a list of search results "
            "with titles, URLs, and snippets. Use this to find current information, "
            "research topics, or discover relevant web pages."
        ),
        args_schema=WebSearchInput,
        return_direct=False
    )


def create_web_fetch_tool() -> BaseTool:
    """Create the web fetch tool."""
    return StructuredTool.from_function(
        func=web_fetch,
        name="web_fetch",
        description=(
            "Fetch and read content from a web page URL. Extracts readable text "
            "from HTML pages. Use this to read articles, documentation, or any "
            "web page content after finding URLs via web_search."
        ),
        args_schema=WebFetchInput,
        return_direct=False
    )


def create_web_tools() -> List[BaseTool]:
    """Create all web tools."""
    return [
        create_web_search_tool(),
        create_web_fetch_tool()
    ]


# Web tool class names for identification
WEB_TOOL_CLASSES = {
    "WebSearch": "web_search",
    "WebFetch": "web_fetch"
}

WEB_TOOL_NAMES = list(WEB_TOOL_CLASSES.values())


def is_web_tool_class(langchain_class: str) -> bool:
    """Check if a langchain_class is a web tool."""
    return langchain_class in WEB_TOOL_CLASSES
