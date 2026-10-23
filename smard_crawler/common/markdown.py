"""HTML to Markdown conversion for browser-driven engines."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from markdownify import markdownify

_DROP_TAGS = ["script", "style", "noscript", "svg", "template", "iframe", "canvas"]


def html_to_markdown(html: str, base_url: str = "") -> dict:
    """Return {"markdown", "title", "links"} extracted from rendered HTML."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(_DROP_TAGS):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href and not href.startswith(("javascript:", "mailto:", "#")):
            links.append(urljoin(base_url, href))

    body = soup.body or soup
    md = markdownify(str(body), heading_style="ATX", bullets="-")
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return {"markdown": md, "title": title, "links": list(dict.fromkeys(links))}
