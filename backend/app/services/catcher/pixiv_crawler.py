"""
Pixiv Crawler

Collects couple illustrations from Pixiv using their API.

Note: Requires Pixiv API credentials.
To use:
1. Create a Pixiv account
2. Get API tokens from Pixiv Developer Console
3. Set PIXIV_REFRESH_TOKEN in environment variables

Rate Limiting: Pixiv allows ~100 requests/hour for free tier
"""

from typing import List, Dict, Optional, Any
import logging
from pathlib import Path
from datetime import datetime
import aiohttp

from .base_crawler import BaseCrawler, CrawlerConfig, ImageMetadata

logger = logging.getLogger(__name__)


class PixivCrawler(BaseCrawler):
    """
    Crawler for Pixiv artwork

    Supports:
    - Search by keywords (Japanese and English)
    - Filter by tags, popularity
    - Couple-specific searches (カップル, 2人, etc.)
    """

    API_BASE = "https://app-api.pixiv.net"
    AUTH_BASE = "https://oauth.secure.pixiv.net"

    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        refresh_token: Optional[str] = None
    ):
        """
        Initialize Pixiv crawler

        Args:
            config: Crawler configuration
            refresh_token: Pixiv API refresh token
        """
        # Pixiv requires stricter rate limiting
        if config is None:
            config = CrawlerConfig(
                rate_limit_delay=2.0,  # 2 seconds between requests
                max_concurrent_requests=2,
                timeout=30
            )

        super().__init__(config)

        self.refresh_token = refresh_token
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        logger.info("Initialized Pixiv crawler")

    def get_source_name(self) -> str:
        """Get the name of this image source"""
        return "pixiv"

    async def _authenticate(self) -> bool:
        """
        Authenticate with Pixiv API

        Returns:
            True if authentication successful
        """
        if not self.refresh_token:
            logger.error("No refresh token provided for Pixiv API")
            return False

        try:
            session = await self._create_session()

            auth_data = {
                "client_id": "MOBrBDS8blbauoSck0ZfDbtuzpyT",
                "client_secret": "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj",
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "get_secure_url": 1
            }

            async with session.post(
                f"{self.AUTH_BASE}/auth/token",
                data=auth_data,
                headers={"User-Agent": "PixivAndroidApp/5.0.234"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data["access_token"]
                    self.refresh_token = data["refresh_token"]
                    # Token expires in 1 hour
                    self.token_expires_at = datetime.now()

                    logger.info("Successfully authenticated with Pixiv API")
                    return True
                else:
                    logger.error(
                        f"Pixiv authentication failed: {response.status}",
                        extra={"status": response.status}
                    )
                    return False

        except Exception as e:
            logger.error(f"Pixiv authentication error: {e}", extra={"error": str(e)})
            return False

    async def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid access token"""
        if self.access_token is None:
            return await self._authenticate()

        # Check if token expired (refresh if older than 50 minutes)
        if self.token_expires_at:
            age = (datetime.now() - self.token_expires_at).total_seconds()
            if age > 3000:  # 50 minutes
                return await self._authenticate()

        return True

    async def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ImageMetadata]:
        """
        Search Pixiv for couple illustrations

        Args:
            query: Search keywords (e.g., "カップル", "couple", "2人")
            limit: Maximum number of results
            filters: Additional filters:
                - sort: "popular" or "date" (default: "popular")
                - min_bookmarks: Minimum bookmark count
                - r18: Include R18 content (default: False)

        Returns:
            List of image metadata
        """
        filters = filters or {}
        sort = filters.get("sort", "popular")
        min_bookmarks = filters.get("min_bookmarks", 100)
        include_r18 = filters.get("r18", False)

        logger.info(
            f"Searching Pixiv: query='{query}', limit={limit}",
            extra={"query": query, "limit": limit, "sort": sort}
        )

        # Check authentication
        if not await self._ensure_authenticated():
            logger.error("Failed to authenticate with Pixiv")
            return []

        results = []
        offset = 0
        page_size = min(30, limit)  # Pixiv max per page is 30

        try:
            while len(results) < limit:
                # Search illustrations
                params = {
                    "word": query,
                    "search_target": "partial_match_for_tags",
                    "sort": sort,
                    "filter": "for_ios" if not include_r18 else "for_android",
                    "offset": offset
                }

                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "User-Agent": "PixivAndroidApp/5.0.234"
                }

                response = await self._fetch_with_retry(
                    f"{self.API_BASE}/v1/search/illust",
                    params=params,
                    headers=headers
                )

                if not response:
                    break

                data = await response.json()
                illusts = data.get("illusts", [])

                if not illusts:
                    logger.info("No more results from Pixiv")
                    break

                # Process results
                for illust in illusts:
                    if len(results) >= limit:
                        break

                    # Filter by bookmarks
                    bookmarks = illust.get("total_bookmarks", 0)
                    if bookmarks < min_bookmarks:
                        continue

                    # Get image URL (use largest available)
                    image_urls = illust.get("image_urls", {})
                    url = (
                        image_urls.get("large") or
                        image_urls.get("medium") or
                        image_urls.get("square_medium")
                    )

                    if not url:
                        continue

                    # Extract metadata
                    metadata = ImageMetadata(
                        url=url,
                        source=self.get_source_name(),
                        title=illust.get("title"),
                        artist=illust.get("user", {}).get("name"),
                        tags=[tag.get("name") for tag in illust.get("tags", [])],
                        width=illust.get("width"),
                        height=illust.get("height"),
                        pixiv_id=illust.get("id"),
                        bookmarks=bookmarks,
                        views=illust.get("total_view", 0),
                        created_at=illust.get("create_date")
                    )

                    results.append(metadata)

                offset += page_size

                # Check if there are more pages
                if not data.get("next_url"):
                    break

        except Exception as e:
            logger.error(
                f"Error searching Pixiv: {e}",
                extra={"error": str(e), "query": query}
            )

        logger.info(
            f"Found {len(results)} results from Pixiv",
            extra={"count": len(results), "query": query}
        )

        return results

    async def download_image(
        self,
        url: str,
        save_path: Path
    ) -> bool:
        """
        Download image from Pixiv

        Pixiv requires Referer header for image downloads

        Args:
            url: Pixiv image URL
            save_path: Path to save the image

        Returns:
            True if successful
        """
        try:
            # Pixiv requires Referer header
            headers = {
                "Referer": "https://www.pixiv.net/"
            }

            response = await self._fetch_with_retry(url, headers=headers)

            if not response:
                return False

            # Save image
            save_path.parent.mkdir(parents=True, exist_ok=True)

            content = await response.read()
            save_path.write_bytes(content)

            logger.info(
                f"Downloaded image to {save_path}",
                extra={"url": url, "path": str(save_path), "size": len(content)}
            )

            return True

        except Exception as e:
            logger.error(
                f"Error downloading Pixiv image: {e}",
                extra={"error": str(e), "url": url}
            )
            return False

    async def get_popular_couple_tags(self) -> List[str]:
        """
        Get popular couple-related tags from Pixiv

        Returns:
            List of tag names
        """
        # Common couple tags in Japanese and English
        return [
            "カップル",  # Couple
            "2人",  # Two people
            "男女",  # Male and female
            "couple",
            "boy and girl",
            "恋人",  # Lovers
            "ペア",  # Pair
            "デート",  # Date
            "romantic"
        ]

    async def search_by_multiple_tags(
        self,
        tags: List[str],
        limit_per_tag: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ImageMetadata]:
        """
        Search by multiple tags and combine results

        Args:
            tags: List of tags to search
            limit_per_tag: Max results per tag
            filters: Search filters

        Returns:
            Combined list of image metadata (deduplicated)
        """
        all_results = []
        seen_urls = set()

        for tag in tags:
            results = await self.search(tag, limit=limit_per_tag, filters=filters)

            for result in results:
                if result.url not in seen_urls:
                    all_results.append(result)
                    seen_urls.add(result.url)

        logger.info(
            f"Found {len(all_results)} unique results from {len(tags)} tags",
            extra={"total": len(all_results), "tags_count": len(tags)}
        )

        return all_results
