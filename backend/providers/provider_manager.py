"""
Content Provider Manager
Selects and routes content extraction requests to the best available provider.
Falls back through providers if one fails.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from backend.shared.contracts import NormalizedContent
from .base_provider import ContentProvider
from .scrapegraph_provider import ScrapeGraphProvider
from .playwright_provider import PlaywrightProvider

logger = logging.getLogger(__name__)

_PROVIDER_PRIORITY = ["scrapegraph", "playwright"]


class ProviderManager:
    """
    Manages content extraction providers with fallback logic.
    Tries the best provider first, falls back through alternatives.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._providers: Dict[str, ContentProvider] = {}
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return

        try:
            self._providers["scrapegraph"] = ScrapeGraphProvider(
                self.config.get("scrapegraph", {})
            )
            logger.info("ProviderManager: ScrapeGraphProvider loaded")
        except Exception as e:
            logger.warning(f"ProviderManager: Failed to load ScrapeGraphProvider: {e}")

        try:
            self._providers["playwright"] = PlaywrightProvider(
                self.config.get("playwright", {})
            )
            logger.info("ProviderManager: PlaywrightProvider loaded")
        except Exception as e:
            logger.warning(f"ProviderManager: Failed to load PlaywrightProvider: {e}")

        self._initialized = True
        logger.info(
            f"ProviderManager initialized with providers: "
            f"{list(self._providers.keys())}"
        )

    async def extract_content(
        self,
        url: str,
        prompt: Optional[str] = None,
        **kwargs
    ) -> NormalizedContent:
        if not self._initialized:
            await self.initialize()

        errors: List[str] = []

        for provider_name in _PROVIDER_PRIORITY:
            provider = self._providers.get(provider_name)
            if not provider:
                continue

            try:
                healthy = await provider.health_check()
                if not healthy:
                    logger.debug(f"Provider {provider_name} unhealthy, skipping")
                    errors.append(f"{provider_name}: unhealthy")
                    continue

                result = await provider.extract_content(url=url, prompt=prompt, **kwargs)

                if result and result.confidence > 0:
                    logger.info(
                        f"Provider {provider_name} succeeded for {url} "
                        f"(confidence={result.confidence:.2f})"
                    )
                    return result

                errors.append(
                    f"{provider_name}: low confidence ({result.confidence if result else 'None'})"
                )

            except NotImplementedError:
                errors.append(f"{provider_name}: not implemented")
                continue
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed for {url}: {e}")
                errors.append(f"{provider_name}: {e}")
                continue

        logger.error(f"All providers failed for {url}: {'; '.join(errors)}")
        return NormalizedContent(
            content_id=f"content_failed_{abs(hash(url)) % 10**8}",
            source_url=url,
            provider="none",
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
            metadata={"errors": errors},
        )

    async def health_check(self) -> Dict[str, bool]:
        if not self._initialized:
            await self.initialize()

        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results

    def get_available_providers(self) -> List[str]:
        return list(self._providers.keys())


_provider_manager_instance: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    global _provider_manager_instance
    if _provider_manager_instance is None:
        _provider_manager_instance = ProviderManager()
    return _provider_manager_instance
