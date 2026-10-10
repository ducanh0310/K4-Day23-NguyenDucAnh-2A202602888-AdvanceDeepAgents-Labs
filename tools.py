"""tools.py - STUDENT IMPLEMENTS.  Source tools for the research agents.   Guide: GUIDE.md, part 1.

Rules for every tool:
  * runs on the HOST (not in the sandbox): API keys must never enter the sandbox;
  * returns a STRING (JSON text of compact records) and NEVER raises:
        "NO RESULTS"  when the source answers with nothing,
        "ERROR: ..."  when the source keeps failing after the retries (the agent then tries another source);
  * the docstring is the tool description the LLM reads: keep it precise (what it does, what it returns, when to use it).
Try your tools without any agent:   python tools.py
"""
import json
import os
import random
import re
import time
import xml.etree.ElementTree

import httpx
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

# ---- constants (given) ----
ARXIV_URL = "https://export.arxiv.org/api/query"  # https only: http answers 301
HF_DAILY_URL = "https://huggingface.co/api/daily_papers"
HF_SEARCH_URL = "https://huggingface.co/api/papers/search"
EXA_URL = "https://mcp.exa.ai/mcp"

_LAST_ARXIV_CALL = 0.0


class RetryableError(Exception):
    """Given. Raise it inside a call to ask with_retry to wait and try again (retry_after in seconds, optional)."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


# ---- TODO 1: retry helper ----
def with_retry(fn, *, attempts=5, base=1.0, cap=30.0):
    """Call fn(); when it raises RetryableError, wait and call it again."""
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            retryable = False
            retry_after = None

            if isinstance(exc, RetryableError):
                retryable = True
                retry_after = exc.retry_after
            elif isinstance(exc, httpx.HTTPStatusError):
                if exc.response.status_code in {429, 500, 502, 503, 504}:
                    retryable = True
                    raw_after = exc.response.headers.get("Retry-After")
                    if raw_after:
                        try:
                            retry_after = float(raw_after)
                        except ValueError:
                            pass
            elif isinstance(exc, httpx.TransportError):
                retryable = True

            if not retryable:
                raise

            if attempt == attempts - 1:
                raise

            if retry_after is not None:
                delay = min(float(retry_after), cap)
            else:
                delay = min(cap, base * (2 ** attempt)) + random.uniform(0.1, 1.0) * base
                delay = min(delay, cap)

            time.sleep(delay)


def _safe_error(exc: Exception) -> str:
    key = (os.getenv("EXA_API_KEY") or "").strip()
    msg = f"ERROR: {type(exc).__name__}: {exc}"
    if key and key in msg:
        msg = msg.replace(key, "<REDACTED>")
    return msg


def _wait_arxiv():
    global _LAST_ARXIV_CALL
    now = time.monotonic()
    elapsed = now - _LAST_ARXIV_CALL
    if elapsed < 3.0:
        time.sleep(3.0 - elapsed)
    _LAST_ARXIV_CALL = time.monotonic()


# ---- TODO 2: arXiv ----
@tool
def arxiv_search(query: str, max_results: int = 10) -> str:
    """Search arXiv papers by keywords, newest first. Returns a JSON list of {id, url, published, title, summary}."""
    try:
        terms = re.findall(r"[A-Za-z0-9\-]+", query)
        if not terms:
            return "NO RESULTS"

        search_query = " AND ".join(f"all:{t}" for t in terms)
        n_results = max(1, min(int(max_results), 30))

        def _fetch():
            _wait_arxiv()
            resp = httpx.get(
                ARXIV_URL,
                params={
                    "search_query": search_query,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": n_results,
                    "start": 0,
                },
                timeout=30.0,
            )
            if resp.status_code == 429:
                raise RetryableError("arxiv HTTP 429", retry_after=resp.headers.get("Retry-After"))
            resp.raise_for_status()
            return resp.text

        xml_text = with_retry(_fetch, attempts=6, base=2.0, cap=60.0)
        root = xml.etree.ElementTree.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        records = []

        for entry in root.findall("atom:entry", ns):
            raw_id = (entry.findtext("atom:id", "", namespaces=ns) or "").strip()
            paper_id = raw_id.split("/abs/")[-1].strip()
            paper_id = re.sub(r"v\d+$", "", paper_id)
            if not paper_id:
                continue
            url = f"https://arxiv.org/abs/{paper_id}"
            published = (entry.findtext("atom:published", "", namespaces=ns) or "").strip()[:10]
            raw_title = entry.findtext("atom:title", "", namespaces=ns) or ""
            title = " ".join(raw_title.split())
            raw_summary = entry.findtext("atom:summary", "", namespaces=ns) or ""
            summary = " ".join(raw_summary.split())[:600]
            records.append({
                "id": paper_id,
                "url": url,
                "published": published,
                "title": title,
                "summary": summary,
            })

        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return _safe_error(exc)


# ---- TODO 3: Hugging Face ----
@tool
def hf_daily_papers(limit: int = 30, date: str = "", keyword: str = "") -> str:
    """Hugging Face Daily Papers = what is trending in AI research. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars} sorted by upvotes. `date` is YYYY-MM-DD (empty = latest).
    `keyword` filters title/summary; there is no topic search on this endpoint (use hf_search_papers for a topic)."""
    try:
        n_limit = max(1, min(int(limit), 100))
        params = {"limit": n_limit}
        if date and date.strip():
            params["date"] = date.strip()

        def _fetch():
            resp = httpx.get(HF_DAILY_URL, params=params, timeout=30.0)
            if resp.status_code == 429:
                raise RetryableError("HF HTTP 429", retry_after=resp.headers.get("Retry-After"))
            resp.raise_for_status()
            return resp.json()

        data = with_retry(_fetch, attempts=5, base=1.0, cap=30.0)
        records = []
        for item in data:
            p = item.get("paper") if isinstance(item, dict) and "paper" in item else item
            if not isinstance(p, dict):
                continue
            paper_id = p.get("id")
            if not paper_id:
                continue
            published = str(p.get("publishedAt") or item.get("publishedAt") or "")[:10]
            title = " ".join(str(p.get("title") or item.get("title") or "").split())
            summary = " ".join(str(p.get("summary") or item.get("summary") or "").split())[:600]
            upvotes = int(p.get("upvotes") or 0)
            github = str(p.get("githubRepo") or "")
            stars = int(p.get("githubStars") or 0)
            records.append({
                "id": str(paper_id),
                "url": f"https://huggingface.co/papers/{paper_id}",
                "published": published,
                "title": title,
                "summary": summary,
                "upvotes": upvotes,
                "github": github,
                "stars": stars,
            })

        if keyword and keyword.strip():
            kw = keyword.strip().lower()
            records = [r for r in records if kw in (r["title"] + " " + r["summary"]).lower()]

        records.sort(key=lambda r: r["upvotes"], reverse=True)
        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return _safe_error(exc)


@tool
def hf_search_papers(query: str, limit: int = 10) -> str:
    """Search Hugging Face papers by topic. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars}."""
    try:
        q = query.strip()
        if not q:
            return "NO RESULTS"
        n_limit = max(1, min(int(limit), 50))
        params = {"q": q, "limit": n_limit}

        def _fetch():
            resp = httpx.get(HF_SEARCH_URL, params=params, timeout=30.0)
            if resp.status_code == 429:
                raise RetryableError("HF HTTP 429", retry_after=resp.headers.get("Retry-After"))
            resp.raise_for_status()
            return resp.json()

        data = with_retry(_fetch, attempts=5, base=1.0, cap=30.0)
        records = []
        for item in data:
            p = item.get("paper") if isinstance(item, dict) and "paper" in item else item
            if not isinstance(p, dict):
                continue
            paper_id = p.get("id")
            if not paper_id:
                continue
            raw_summary = p.get("ai_summary") or item.get("ai_summary") or p.get("summary") or item.get("summary") or ""
            summary = " ".join(str(raw_summary).split())[:600]
            published = str(p.get("publishedAt") or item.get("publishedAt") or "")[:10]
            title = " ".join(str(p.get("title") or item.get("title") or "").split())
            upvotes = int(p.get("upvotes") or 0)
            github = str(p.get("githubRepo") or "")
            stars = int(p.get("githubStars") or 0)
            records.append({
                "id": str(paper_id),
                "url": f"https://huggingface.co/papers/{paper_id}",
                "published": published,
                "title": title,
                "summary": summary,
                "upvotes": upvotes,
                "github": github,
                "stars": stars,
            })

        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return _safe_error(exc)


# ---- TODO 4: web search / fetch through the Exa MCP endpoint ----
def _call_exa_mcp(tool_name: str, arguments: dict) -> str:
    key = (os.getenv("EXA_API_KEY") or "").strip()
    url = f"{EXA_URL}?exaApiKey={key}" if key else EXA_URL
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    def _post():
        resp = httpx.post(url, headers=headers, json=payload, timeout=45.0)
        if resp.status_code == 429:
            raise RetryableError("Exa HTTP 429", retry_after=resp.headers.get("Retry-After"))
        resp.raise_for_status()

        parsed_data = None
        for line in resp.text.splitlines():
            line_str = line.strip()
            if line_str.startswith("data:"):
                raw_json = line_str[len("data:"):].strip()
                if raw_json:
                    parsed_data = json.loads(raw_json)
                    break
        if parsed_data is None:
            try:
                parsed_data = resp.json()
            except Exception:
                raise RuntimeError(f"Unexpected response from Exa: {resp.text[:200]}")

        if "error" in parsed_data:
            err = parsed_data["error"]
            err_msg = err.get("message", str(err))
            if "rate limit" in err_msg.lower():
                raise RetryableError(f"Exa rate limit: {err_msg}")
            raise RuntimeError(f"Exa error: {err_msg}")

        result = parsed_data.get("result", {})
        meta = result.get("_meta", {})
        meta_str = json.dumps(meta).lower()
        if "rate_limit" in meta_str or "ratelimit" in meta_str or ("limit" in meta_str and "exceeded" in meta_str):
            raise RetryableError(f"Exa rate limit flag in _meta: {meta}")

        content_items = result.get("content", [])
        text_parts = []
        for c in content_items:
            if isinstance(c, dict) and c.get("type") == "text":
                text_parts.append(c.get("text", ""))

        combined_text = "\n\n".join(text_parts).strip()
        if "rate limit" in combined_text.lower() and ("exceeded" in combined_text.lower() or "too many requests" in combined_text.lower()):
            raise RetryableError(f"Exa rate limit text detected: {combined_text[:100]}")

        return combined_text

    return with_retry(_post, attempts=6, base=2.0, cap=60.0)


@tool
def web_search(query: str, objective: str = "", num_results: int = 5) -> str:
    """Search the web (Exa). Describe the ideal page in natural language. Returns clean text of the top results with URLs."""
    try:
        q = query.strip()
        if not q:
            return "NO RESULTS"
        obj = objective.strip() or f"find research papers and comprehensive articles about {q}"
        num = max(1, min(int(num_results), 10))
        text = _call_exa_mcp("web_search_exa", {"query": q, "objective": obj, "numResults": num})
        return text if text else "NO RESULTS"
    except Exception as exc:
        return _safe_error(exc)


@tool
def web_fetch(url: str) -> str:
    """Read the full content of one web page (e.g. an arXiv abstract page) as markdown. Long pages are truncated."""
    try:
        u = url.strip()
        if not u:
            return "NO RESULTS"
        text = _call_exa_mcp("web_fetch_exa", {"urls": [u]})
        if not text:
            return "NO RESULTS"
        return text[:12000]
    except Exception as exc:
        return _safe_error(exc)


# ---- TODO 5: registry (the researcher subagent gets exactly these) ----
SOURCE_TOOLS = [arxiv_search, hf_daily_papers, hf_search_papers, web_search, web_fetch]


if __name__ == "__main__":
    for name, fn, args in [
        ("arxiv_search", arxiv_search, {"query": "world model", "max_results": 3}),
        ("hf_daily_papers", hf_daily_papers, {"limit": 20}),
        ("hf_search_papers", hf_search_papers, {"query": "world model", "limit": 3}),
        ("web_search", web_search, {"query": "survey paper on world models", "num_results": 2}),
        ("web_fetch", web_fetch, {"url": "https://arxiv.org/abs/1803.10122"}),
    ]:
        try:
            print(f"== {name}\n{fn.invoke(args)[:400]}\n")
        except NotImplementedError as exc:
            print(f"== {name}: not implemented yet ({exc})\n")
