"""
Base Crawler for Image Collection

Provides abstract base class for implementing various image source crawlers.
Includes common functionality for face detection, filtering, and rate limiting.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class CrawlerConfig:
    """Configuration for crawlers"""

    def __init__(
        self,
        rate_limit_delay: float = 1.0,
        max_concurrent_requests: int = 3,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        proxy: Optional[str] = None,
        respect_robots_txt: bool = True
    ):
        self.rate_limit_delay = rate_limit_delay
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout = timeout
        self.user_agent = user_agent or "CoupleFaceSwap-Crawler/1.0 (Educational Purpose)"
        self.proxy = proxy
        self.respect_robots_txt = respect_robots_txt


class ImageMetadata:
    """Metadata for collected images"""

    def __init__(
        self,
        url: str,
        source: str,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        tags: Optional[List[str]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        file_size: Optional[int] = None,
        face_count: Optional[int] = None,
        timestamp: Optional[datetime] = None,
        **kwargs
    ):
        self.url = url
        self.source = source
        self.title = title
        self.artist = artist
        self.tags = tags or []
        self.width = width
        self.height = height
        self.file_size = file_size
        self.face_count = face_count
        self.timestamp = timestamp or datetime.now()
        self.extra = kwargs

        # Generate unique ID based on URL
        self.id = hashlib.md5(url.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "url": self.url,
            "source": self.source,
            "title": self.title,
            "artist": self.artist,
            "tags": self.tags,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
            "face_count": self.face_count,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            **self.extra
        }


class BaseCrawler(ABC):
    """
    Base class for all image crawlers

    Provides common functionality:
    - HTTP session management with rate limiting
    - Face detection and filtering
    - Image metadata extraction
    - Error handling and retry logic
    """

    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = datetime.now() - timedelta(seconds=self.config.rate_limit_delay)
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)

        logger.info(
            f"Initialized {self.__class__.__name__}",
            extra={
                "rate_limit": self.config.rate_limit_delay,
                "max_concurrent": self.config.max_concurrent_requests
            }
        )

    async def _create_session(self) -> aiohttp.ClientSession:
        """Create HTTP session with configured settings"""
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": self.config.user_agent
            }
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
        return self._session

    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info(f"Closed session for {self.__class__.__name__}")

    async def _rate_limit(self):
        """Apply rate limiting between requests"""
        now = datetime.now()
        time_since_last = (now - self._last_request_time).total_seconds()

        if time_since_last < self.config.rate_limit_delay:
            wait_time = self.config.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = datetime.now()

    async def _fetch_with_retry(
        self,
        url: str,
        max_retries: int = 3,
        **kwargs
    ) -> Optional[aiohttp.ClientResponse]:
        """
        Fetch URL with retry logic

        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments for aiohttp request

        Returns:
            Response object or None if all retries failed
        """
        session = await self._create_session()

        for attempt in range(max_retries):
            try:
                async with self._semaphore:
                    await self._rate_limit()

                    async with session.get(url, **kwargs) as response:
                        if response.status == 200:
                            return response
                        elif response.status == 429:  # Too Many Requests
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.warning(
                                f"Rate limited (429), waiting {wait_time}s",
                                extra={"url": url, "attempt": attempt + 1}
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            logger.warning(
                                f"HTTP {response.status} for {url}",
                                extra={"status": response.status, "attempt": attempt + 1}
                            )

            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout fetching {url}",
                    extra={"attempt": attempt + 1}
                )
            except Exception as e:
                logger.error(
                    f"Error fetching {url}: {e}",
                    extra={"error": str(e), "attempt": attempt + 1}
                )

            if attempt < max_retries - 1:
                await asyncio.sleep(1 * (attempt + 1))

        logger.error(f"Failed to fetch {url} after {max_retries} attempts")
        return None

    def filter_couples(
        self,
        images: List[ImageMetadata],
        min_faces: int = 2,
        max_faces: int = 2
    ) -> List[ImageMetadata]:
        """
        Filter images to only include those with specified face count

        Args:
            images: List of image metadata
            min_faces: Minimum number of faces required
            max_faces: Maximum number of faces allowed

        Returns:
            Filtered list of images
        """
        filtered = []

        for img in images:
            if img.face_count is None:
                # If face_count not set, keep image for later processing
                filtered.append(img)
            elif min_faces <= img.face_count <= max_faces:
                filtered.append(img)

        logger.info(
            f"Filtered {len(images)} images to {len(filtered)} couples",
            extra={
                "original_count": len(images),
                "filtered_count": len(filtered),
                "min_faces": min_faces,
                "max_faces": max_faces
            }
        )

        return filtered

    def filter_by_resolution(
        self,
        images: List[ImageMetadata],
        min_width: int = 800,
        min_height: int = 600
    ) -> List[ImageMetadata]:
        """
        Filter images by minimum resolution

        Args:
            images: List of image metadata
            min_width: Minimum width in pixels
            min_height: Minimum height in pixels

        Returns:
            Filtered list of images
        """
        filtered = []

        for img in images:
            if img.width is None or img.height is None:
                # If dimensions not set, keep for later processing
                filtered.append(img)
            elif img.width >= min_width and img.height >= min_height:
                filtered.append(img)

        logger.info(
            f"Filtered by resolution: {len(images)} -> {len(filtered)}",
            extra={
                "min_width": min_width,
                "min_height": min_height,
                "original_count": len(images),
                "filtered_count": len(filtered)
            }
        )

        return filtered

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ImageMetadata]:
        """
        Search for images based on query

        Args:
            query: Search keywords
            limit: Maximum number of results
            filters: Additional filters (implementation-specific)

        Returns:
            List of image metadata
        """
        pass

    @abstractmethod
    async def download_image(
        self,
        url: str,
        save_path: Path
    ) -> bool:
        """
        Download single image

        Args:
            url: Image URL
            save_path: Path to save the image

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this image source"""
        pass

    async def __aenter__(self):
        """Context manager entry"""
        await self._create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
