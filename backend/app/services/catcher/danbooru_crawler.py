"""
Danbooru Crawler

Collects couple images from Danbooru and compatible sites (Gelbooru, etc.)

Danbooru API is publicly accessible with generous rate limits.
No authentication required for public posts.

Rate Limiting: 2 requests/second for anonymous users
Documentation: https://danbooru.donmai.us/wiki_pages/help:api
"""

from typing import List, Dict, Optional, Any
import logging
from pathlib import Path
from datetime import datetime

from .base_crawler import BaseCrawler, CrawlerConfig, ImageMetadata

logger = logging.getLogger(__name__)


class DanbooruCrawler(BaseCrawler):
    """
    Crawler for Danbooru-style image boards

    Supports:
    - Tag-based search
    - Rating filters (safe, questionable, explicit)
    - Score/popularity filters
    - Multi-tag combinations
    """

    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        base_url: str = "https://danbooru.donmai.us",
        api_key: Optional[str] = None,
        username: Optional[str] = None
    ):
        """
        Initialize Danbooru crawler

        Args:
            config: Crawler configuration
            base_url: Danbooru instance URL (default: official danbooru)
            api_key: Optional API key for higher rate limits
            username: Optional username for authentication
        """
        # Danbooru rate limit: 2 req/sec anonymous, 30 req/sec with auth
        if config is None:
            rate_limit = 0.5 if api_key else 0.6  # Be conservative
            config = CrawlerConfig(
                rate_limit_delay=rate_limit,
                max_concurrent_requests=3,
                timeout=30
            )

        super().__init__(config)

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.username = username

        logger.info(
            f"Initialized Danbooru crawler",
            extra={"base_url": base_url, "authenticated": api_key is not None}
        )

    def get_source_name(self) -> str:
        """Get the name of this image source"""
        return "danbooru"

    def _get_auth_params(self) -> Dict[str, str]:
        """Get authentication parameters if available"""
        if self.api_key and self.username:
            return {
                "login": self.username,
                "api_key": self.api_key
            }
        return {}

    async def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ImageMetadata]:
        """
        Search Danbooru for images

        Args:
            query: Tag search string (e.g., "2girls", "1boy_1girl")
            limit: Maximum number of results
            filters: Additional filters:
                - rating: "g" (safe), "s" (safe), "q" (questionable), "e" (explicit)
                - min_score: Minimum score (default: 10)
                - file_ext: File extension filter (jpg, png, etc.)
                - order: Sort order (score, id, etc.)

        Returns:
            List of image metadata
        """
        filters = filters or {}
        rating = filters.get("rating", "s")  # Safe by default
        min_score = filters.get("min_score", 10)
        file_ext = filters.get("file_ext")
        order = filters.get("order", "score")

        logger.info(
            f"Searching Danbooru: query='{query}', limit={limit}",
            extra={"query": query, "limit": limit, "rating": rating}
        )

        results = []
        page = 1
        page_size = min(200, limit)  # Danbooru max 200 per page

        try:
            while len(results) < limit:
                # Build tag string
                tags = query.split()

                # Add rating filter
                if rating:
                    tags.append(f"rating:{rating}")

                # Add score filter
                if min_score:
                    tags.append(f"score:>={min_score}")

                # Build params
                params = {
                    "tags": " ".join(tags),
                    "limit": min(page_size, limit - len(results)),
                    "page": page
                }

                # Add authentication if available
                params.update(self._get_auth_params())

                # Fetch posts
                response = await self._fetch_with_retry(
                    f"{self.base_url}/posts.json",
                    params=params
                )

                if not response:
                    break

                posts = await response.json()

                if not posts:
                    logger.info("No more results from Danbooru")
                    break

                # Process posts
                for post in posts:
                    if len(results) >= limit:
                        break

                    # Get file URL
                    file_url = post.get("file_url")
                    if not file_url:
                        continue

                    # Make URL absolute
                    if file_url.startswith("/"):
                        file_url = f"{self.base_url}{file_url}"

                    # Filter by file extension if specified
                    if file_ext and not file_url.endswith(f".{file_ext}"):
                        continue

                    # Extract tags
                    tag_string = post.get("tag_string", "")
                    tags_list = tag_string.split() if tag_string else []

                    # Extract metadata
                    metadata = ImageMetadata(
                        url=file_url,
                        source=self.get_source_name(),
                        tags=tags_list,
                        width=post.get("image_width"),
                        height=post.get("image_height"),
                        file_size=post.get("file_size"),
                        danbooru_id=post.get("id"),
                        score=post.get("score"),
                        rating=post.get("rating"),
                        uploader=post.get("uploader_name"),
                        source_url=post.get("source"),
                        created_at=post.get("created_at")
                    )

                    results.append(metadata)

                page += 1

                # Safety limit to prevent infinite loops
                if page > 100:
                    logger.warning("Reached page limit (100) for Danbooru search")
                    break

        except Exception as e:
            logger.error(
                f"Error searching Danbooru: {e}",
                extra={"error": str(e), "query": query}
            )

        logger.info(
            f"Found {len(results)} results from Danbooru",
            extra={"count": len(results), "query": query}
        )

        return results

    async def download_image(
        self,
        url: str,
        save_path: Path
    ) -> bool:
        """
        Download image from Danbooru

        Args:
            url: Image URL
            save_path: Path to save the image

        Returns:
            True if successful
        """
        try:
            response = await self._fetch_with_retry(url)

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
                f"Error downloading Danbooru image: {e}",
                extra={"error": str(e), "url": url}
            )
            return False

    async def get_couple_tags(self) -> List[str]:
        """
        Get common couple-related tags from Danbooru

        Returns:
            List of tag combinations for couple images
        """
        return [
            "1boy_1girl",
            "2girls",
            "couple",
            "heterosexual",
            "yuri",  # Female-female
            "yaoi",  # Male-male
            "multiple_girls 2girls",
            "holding_hands",
            "hug",
            "kiss",
            "romantic"
        ]

    async def search_couples(
        self,
        limit: int = 20,
        couple_type: str = "heterosexual",
        min_score: int = 10,
        safe_only: bool = True
    ) -> List[ImageMetadata]:
        """
        Search specifically for couple images

        Args:
            limit: Maximum number of results
            couple_type: Type of couple ("heterosexual", "yuri", "yaoi", "any")
            min_score: Minimum score threshold
            safe_only: Only return safe-rated images

        Returns:
            List of couple image metadata
        """
        # Build query based on couple type
        if couple_type == "heterosexual":
            query = "1boy_1girl"
        elif couple_type == "yuri":
            query = "2girls yuri"
        elif couple_type == "yaoi":
            query = "2boys yaoi"
        else:  # any
            query = "couple"

        # Build filters
        filters = {
            "min_score": min_score,
            "rating": "s" if safe_only else None,
            "order": "score"
        }

        logger.info(
            f"Searching for couples: type={couple_type}, safe={safe_only}",
            extra={"couple_type": couple_type, "safe_only": safe_only}
        )

        return await self.search(query, limit=limit, filters=filters)

    async def get_popular_couple_posts(
        self,
        limit: int = 20,
        time_period: str = "week"
    ) -> List[ImageMetadata]:
        """
        Get popular couple posts from recent time period

        Args:
            limit: Maximum number of results
            time_period: Time period ("day", "week", "month")

        Returns:
            List of popular couple posts
        """
        # Danbooru popular endpoint
        params = {
            "scale": time_period,
            "limit": limit
        }

        # Add authentication if available
        params.update(self._get_auth_params())

        try:
            response = await self._fetch_with_retry(
                f"{self.base_url}/explore/posts/popular.json",
                params=params
            )

            if not response:
                return []

            posts = await response.json()
            results = []

            for post in posts:
                # Only include couple-related posts
                tag_string = post.get("tag_string", "").lower()
                if any(couple_tag in tag_string for couple_tag in [
                    "1boy_1girl", "2girls", "couple", "yuri", "yaoi"
                ]):
                    file_url = post.get("file_url")
                    if file_url:
                        if file_url.startswith("/"):
                            file_url = f"{self.base_url}{file_url}"

                        metadata = ImageMetadata(
                            url=file_url,
                            source=self.get_source_name(),
                            tags=tag_string.split(),
                            width=post.get("image_width"),
                            height=post.get("image_height"),
                            file_size=post.get("file_size"),
                            danbooru_id=post.get("id"),
                            score=post.get("score"),
                            rating=post.get("rating")
                        )
                        results.append(metadata)

            logger.info(
                f"Found {len(results)} popular couple posts",
                extra={"count": len(results), "period": time_period}
            )

            return results[:limit]

        except Exception as e:
            logger.error(
                f"Error getting popular posts: {e}",
                extra={"error": str(e)}
            )
            return []


class GelbooruCrawler(DanbooruCrawler):
    """
    Crawler for Gelbooru (uses similar API to Danbooru)

    Gelbooru has slightly different API but similar structure
    """

    def __init__(self, config: Optional[CrawlerConfig] = None):
        super().__init__(
            config=config,
            base_url="https://gelbooru.com"
        )

    def get_source_name(self) -> str:
        return "gelbooru"

    async def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ImageMetadata]:
        """
        Search Gelbooru (uses XML API)

        Note: Gelbooru API is slightly different from Danbooru
        """
        filters = filters or {}
        rating = filters.get("rating", "safe")

        logger.info(
            f"Searching Gelbooru: query='{query}', limit={limit}",
            extra={"query": query, "limit": limit}
        )

        results = []
        pid = 0  # Page ID for Gelbooru

        try:
            while len(results) < limit:
                params = {
                    "page": "dapi",
                    "s": "post",
                    "q": "index",
                    "json": "1",
                    "tags": query,
                    "limit": min(100, limit - len(results)),
                    "pid": pid
                }

                response = await self._fetch_with_retry(
                    f"{self.base_url}/index.php",
                    params=params
                )

                if not response:
                    break

                data = await response.json()
                posts = data.get("post", []) if isinstance(data, dict) else data

                if not posts:
                    break

                for post in posts:
                    if len(results) >= limit:
                        break

                    file_url = post.get("file_url")
                    if not file_url:
                        continue

                    metadata = ImageMetadata(
                        url=file_url,
                        source=self.get_source_name(),
                        tags=post.get("tags", "").split(),
                        width=post.get("width"),
                        height=post.get("height"),
                        gelbooru_id=post.get("id"),
                        score=post.get("score"),
                        rating=post.get("rating")
                    )

                    results.append(metadata)

                pid += 1

                if pid > 100:
                    break

        except Exception as e:
            logger.error(
                f"Error searching Gelbooru: {e}",
                extra={"error": str(e), "query": query}
            )

        logger.info(
            f"Found {len(results)} results from Gelbooru",
            extra={"count": len(results)}
        )

        return results
