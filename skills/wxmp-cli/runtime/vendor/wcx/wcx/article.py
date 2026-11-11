"""Fetch & parse article HTML from mp.weixin.qq.com public article URLs."""
from __future__ import annotations

import ast
import base64
import binascii
import html as html_lib
import re

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from markdownify import markdownify


def fetch_article_html(url: str, *, impersonate: str = "chrome120") -> str:
    """Fetch the public article page HTML (no auth needed for public articles).

    WeChat returns a 301 on http:// that curl_cffi's default impersonated session
    mishandles as 501. Normalize to https:// and enable redirect following.
    """
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    resp = cffi_requests.get(url, impersonate=impersonate, timeout=30, allow_redirects=True)
    resp.raise_for_status()
    return resp.text


def extract_content(html: str) -> tuple[str, str]:
    """Extract the article content div. Returns (inner_html, markdown)."""
    soup = BeautifulSoup(html, "lxml")
    content = soup.find("div", id="js_content") or soup.find("div", class_="rich_media_content")
    if content:
        # WeChat hides content via CSS visibility:hidden until JS runs — strip that
        if content.has_attr("style"):
            del content["style"]
        inner_html = str(content)
        md = markdownify(inner_html, heading_style="ATX", strip=["script", "style"])
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        return inner_html, md

    return extract_text_content(html)


def extract_text_content(html: str) -> tuple[str, str]:
    """Extract text-only share pages rendered from cgiDataNew.content_noencode."""
    match = re.search(r"content_noencode\s*[:=]\s*([\"'])(.*?)\1", html, re.S)
    if not match:
        return "", ""

    try:
        text = ast.literal_eval(f"{match.group(1)}{match.group(2)}{match.group(1)}")
    except (SyntaxError, ValueError):
        text = match.group(2)

    text = html_lib.unescape(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return "", ""

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    inner_html = (
        '<div id="js_content">'
        + "".join(f"<p>{html_lib.escape(part).replace(chr(10), '<br/>')}</p>" for part in paragraphs)
        + "</div>"
    )
    md = re.sub(r"\n{3,}", "\n\n", text).strip()
    return inner_html, md


def extract_meta(html: str) -> dict:
    """Extract title/author/publish_time from article page."""
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.find("h1", class_="rich_media_title") or soup.find("h2", class_="rich_media_title")
    title = title_el.get_text(strip=True) if title_el else ""
    author_el = soup.find("a", id="js_name") or soup.find("span", class_="rich_media_meta_text")
    author = author_el.get_text(strip=True) if author_el else ""
    return {"title": title, "author": author}


def extract_identity(html: str) -> dict[str, str]:
    """Extract stable publisher/article identifiers embedded in a public page."""

    source = html_lib.unescape(html)

    def stable_fakeid_literal(candidate: str) -> bool:
        """Accept only fakeid literals whose decoded bizuin is numeric."""

        try:
            padded = candidate + "=" * (-len(candidate) % 4)
            decoded = base64.b64decode(padded, validate=True).decode("ascii")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            return False
        return decoded.isdigit()

    def value(*names: str, validator=None) -> str:
        for name in names:
            escaped = re.escape(name)
            patterns = (
                # JavaScript assignments and object properties, including
                # ``var biz = ...`` and ``{"__biz": ...}``.
                rf"(?<![\w$])[\"']?{escaped}[\"']?\s*[:=]\s*([\"'])(.*?)\1",
                # WeChat also embeds identifiers without quotes in some data
                # blobs. Keep this deliberately limited to identifier-safe
                # characters so arbitrary JavaScript is never consumed.
                rf"(?<![\w$])[\"']?{escaped}[\"']?\s*[:=]\s*([A-Za-z0-9_+/=-]+)",
            )
            for pattern in patterns:
                for match in re.finditer(pattern, source, re.S):
                    captured = (
                        match.group(2) if match.lastindex == 2 else match.group(1)
                    )
                    captured = captured.strip()
                    if captured and (validator is None or validator(captured)):
                        return captured
        return ""

    return {
        # ``fakeid`` is exposed as ``biz`` on older article pages and as
        # ``__biz`` (or occasionally ``bizuin``) on newer page data. These
        # aliases all describe the same stable publisher identity.
        "biz": value(
            "biz",
            "__biz",
            "bizuin",
            validator=stable_fakeid_literal,
        ),
        "mid": value("mid"),
        "idx": value("idx"),
        "user_name": value("user_name"),
    }


def extract_classification(html: str) -> dict[str, int | None]:
    """Extract WeChat's own content/copyright flags from an article page."""

    def integer(*names: str) -> int | None:
        for name in names:
            escaped = re.escape(name)
            patterns = (
                rf"(?:\bvar\s+)?{escaped}\s*=\s*['\"]?([0-9]+)['\"]?",
                rf"['\"]{escaped}['\"]\s*:\s*['\"]?([0-9]+)['\"]?",
            )
            for pattern in patterns:
                match = re.search(pattern, html, re.S)
                if match:
                    return int(match.group(1))
        return None

    copyright_type = integer("copyright_type")
    if copyright_type is None:
        copyright_type = {
            100: 0,
            11: 1,
            201: 2,
        }.get(integer("copyright_stat"))

    return {
        "article_type": integer("appmsg_type"),
        "copyright_type": copyright_type,
    }
