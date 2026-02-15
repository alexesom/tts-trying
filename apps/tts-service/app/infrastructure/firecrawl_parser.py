from __future__ import annotations

from firecrawl import Firecrawl

from app.domain.ports import ParsedArticle


class FirecrawlArticleParser:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY is required")
        self._client = Firecrawl(api_key=api_key)

    def parse(self, url: str) -> ParsedArticle:
        document = self._client.scrape(
            url,
            formats=["markdown"],
            only_main_content=True,
            timeout=30_000,
        )

        markdown = (document.markdown or "").strip()
        title = document.metadata.title if document.metadata else None

        if not markdown:
            raise ValueError(f"No markdown content extracted for URL: {url}")

        return ParsedArticle(url=url, markdown=markdown, title=title)
