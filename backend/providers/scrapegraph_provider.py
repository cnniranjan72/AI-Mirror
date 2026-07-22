"""
ScrapeGraph Content Provider — Real Integration
Uses ScrapeGraphAI SmartScraperGraph for LLM-powered web content extraction.
"""
from typing import Optional, Dict, Any, List
import logging
import os
from datetime import datetime
import uuid

from backend.shared.contracts import NormalizedContent
from .base_provider import ContentProvider

logger = logging.getLogger(__name__)

try:
    from scrapegraphai.graphs import SmartScraperGraph
    SCRAPEGRAPH_AVAILABLE = True
except ImportError:
    SCRAPEGRAPH_AVAILABLE = False
    # Try local path (refs/Scrapegraph-ai/)
    import sys
    import os as _os
    _local_path = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
        "refs", "Scrapegraph-ai"
    )
    if _os.path.isdir(_os.path.join(_local_path, "scrapegraphai")):
        sys.path.insert(0, _local_path)
        try:
            from scrapegraphai.graphs import SmartScraperGraph
            SCRAPEGRAPH_AVAILABLE = True
            logger.info("Loaded scrapegraphai from local refs/Scrapegraph-ai/")
        except ImportError:
            logger.warning(
                "scrapegraphai not installed. Run: pip install scrapegraphai, "
                f"or check refs/Scrapegraph-ai/ at {_local_path}"
            )
    else:
        logger.warning(
            "scrapegraphai not installed. Run: pip install scrapegraphai, "
            f"or check refs/Scrapegraph-ai/ at {_local_path}"
        )


class ScrapeGraphProvider(ContentProvider):
    """
    ScrapeGraphAI-based content extraction provider.

    Uses SmartScraperGraph to extract structured information from URLs
    using LLM-powered scraping pipelines.
    """
    _extraction_prompt = (
        "Extract the following information from this page content:\n"
        "1. title: The main title or headline\n"
        "2. caption: The main body text or description\n"
        "3. creator: The content creator/author name\n"
        "4. hashtags: Any hashtags or tags found\n"
        "5. topics: 3-5 key topics this content is about\n"
        "6. intent: The primary intent (educate/entertain/inspire/promote/inform)\n"
        "7. sentiment: Overall sentiment (positive/negative/neutral)\n"
        "8. language: Content language code (e.g., 'en', 'hi')"
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.llm_config = self.config.get("llm", {
            "model": os.getenv("SCRAPEGRAPH_LLM_MODEL", "openai/gpt-4o-mini"),
            "api_key": os.getenv("OPENAI_API_KEY"),
        })
        self.headless = self.config.get("headless", True)
        self.timeout = self.config.get("timeout", 60000)
        if not SCRAPEGRAPH_AVAILABLE:
            logger.warning(
                "ScrapeGraphAI library not installed. "
                "Content extraction will fail at runtime. "
                "Install: pip install scrapegraphai"
            )
        logger.info(
            f"ScrapeGraphProvider initialized (model={self.llm_config.get('model')}, "
            f"available={SCRAPEGRAPH_AVAILABLE})"
        )

    async def extract_content(
        self,
        url: str,
        prompt: Optional[str] = None,
        **kwargs
    ) -> NormalizedContent:
        if not SCRAPEGRAPH_AVAILABLE:
            raise RuntimeError(
                "ScrapeGraphAI is not installed. "
                "Run: pip install scrapegraphai"
            )

        logger.info(f"Extracting content from {url}")

        extraction_prompt = prompt or self._extraction_prompt

        try:
            smart_scraper = SmartScraperGraph(
                prompt=extraction_prompt,
                source=url,
                config={
                    "llm": self.llm_config,
                    "headless": self.headless,
                    "verbose": self.config.get("verbose", False),
                },
            )

            result = smart_scraper.run()

            if not result:
                raise ValueError(f"SmartScraper returned empty result for {url}")

            content_id = f"content_{uuid.uuid4().hex[:12]}"

            extracted = result if isinstance(result, dict) else {"raw": str(result)}

            title = self._safe_get(extracted, ["title", "headline", "heading"], "")
            caption = self._safe_get(extracted, ["caption", "description", "body", "content", "raw"], "")
            creator = self._safe_get(extracted, ["creator", "author", "username"], "")
            raw_tags = self._safe_get(extracted, ["hashtags", "tags"], [])
            hashtags = self._ensure_list(raw_tags)

            topics = self._ensure_list(
                self._safe_get(extracted, ["topics", "categories"], [])
            )
            intent = self._safe_get(extracted, ["intent"], "entertainment")
            sentiment = self._safe_get(extracted, ["sentiment"], "neutral")
            language = self._safe_get(extracted, ["language"], "en")

            confidence = 0.7 if caption else 0.3
            completeness = 0.5 if title or caption else 0.1

            content = NormalizedContent(
                content_id=content_id,
                source_url=url,
                provider="scrapegraph",
                title=title or None,
                caption=caption or None,
                hashtags=hashtags,
                creator=creator or None,
                topics=topics,
                entities=[],
                intent=intent or None,
                sentiment=sentiment or None,
                language=language,
                confidence=min(1.0, confidence),
                completeness=min(1.0, completeness),
                extracted_at=datetime.utcnow(),
                metadata={
                    "extraction_method": "smart_scraper_graph",
                    "llm_model": self.llm_config.get("model"),
                    "raw_result_keys": list(extracted.keys()),
                },
            )

            logger.info(
                f"Extracted content from {url}: "
                f"title={'yes' if title else 'no'} "
                f"caption={len(caption)}ch "
                f"topics={topics} "
                f"confidence={content.confidence:.2f}"
            )
            return content

        except Exception as e:
            logger.error(f"ScrapeGraph extraction failed for {url}: {e}")
            return NormalizedContent(
                content_id=f"content_{uuid.uuid4().hex[:12]}",
                source_url=url,
                provider="scrapegraph",
                title=None,
                caption=None,
                hashtags=[],
                creator=None,
                topics=[],
                entities=[],
                intent=None,
                sentiment=None,
                language="en",
                confidence=0.0,
                completeness=0.0,
                extracted_at=datetime.utcnow(),
                metadata={
                    "extraction_method": "smart_scraper_graph",
                    "error": str(e),
                },
            )

    async def health_check(self) -> bool:
        if not SCRAPEGRAPH_AVAILABLE:
            return False
        try:
            api_key = self.llm_config.get("api_key") or os.getenv("OPENAI_API_KEY")
            return bool(api_key)
        except Exception:
            return False

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "provider": "scrapegraph",
            "status": "ready" if SCRAPEGRAPH_AVAILABLE else "unavailable",
            "implemented": True,
            "available": SCRAPEGRAPH_AVAILABLE,
            "llm_model": self.llm_config.get("model"),
            "features": {
                "llm_extraction": True,
                "smart_scraping": True,
                "multi_provider_llm": True,
                "dynamic_content": True,
                "javascript_rendering": True,
            },
        }

    def validate_config(self) -> bool:
        if "llm" in self.config:
            llm = self.config["llm"]
            if not llm.get("model"):
                logger.error("LLM model not specified in config")
                return False
        return True

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _safe_get(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        return default

    @staticmethod
    def _ensure_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(v) for v in value if v]
        if isinstance(value, str):
            return [value] if value else []
        return []
