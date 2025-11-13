"""
Phase 3 - Catcher Service Tests

Tests for image collection crawlers and management API.

Test Coverage:
- Base crawler functionality
- Pixiv crawler (with mocks)
- Danbooru crawler
- Crawl task API endpoints
- Task management (pause/resume/cancel)
- Collected image retrieval
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.database import Base, CrawlTask, CollectedImage
from app.services.catcher.base_crawler import (
    BaseCrawler,
    CrawlerConfig,
    ImageMetadata
)
from app.services.catcher.danbooru_crawler import DanbooruCrawler
from app.services.catcher.pixiv_crawler import PixivCrawler


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create all tables before tests"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestBaseCrawler:
    """Test base crawler functionality"""

    def test_crawler_config(self):
        """Test crawler configuration"""
        config = CrawlerConfig(
            rate_limit_delay=2.0,
            max_concurrent_requests=5,
            timeout=30
        )

        assert config.rate_limit_delay == 2.0
        assert config.max_concurrent_requests == 5
        assert config.timeout == 30
        assert config.respect_robots_txt is True

    def test_image_metadata_creation(self):
        """Test ImageMetadata creation"""
        metadata = ImageMetadata(
            url="https://example.com/image.jpg",
            source="test",
            title="Test Image",
            artist="Test Artist",
            tags=["test", "example"],
            width=1920,
            height=1080
        )

        assert metadata.url == "https://example.com/image.jpg"
        assert metadata.source == "test"
        assert metadata.title == "Test Image"
        assert metadata.artist == "Test Artist"
        assert "test" in metadata.tags
        assert metadata.width == 1920
        assert metadata.height == 1080

        # Test to_dict conversion
        data = metadata.to_dict()
        assert data["url"] == metadata.url
        assert data["tags"] == ["test", "example"]

    @pytest.mark.asyncio
    async def test_filter_couples(self):
        """Test filtering images by face count"""
        # Create mock crawler
        class MockCrawler(BaseCrawler):
            def get_source_name(self):
                return "mock"

            async def search(self, query, limit=20, filters=None):
                return []

            async def download_image(self, url, save_path):
                return True

        crawler = MockCrawler()

        images = [
            ImageMetadata(url="single.jpg", source="test", face_count=1),
            ImageMetadata(url="couple.jpg", source="test", face_count=2),
            ImageMetadata(url="group.jpg", source="test", face_count=5),
            ImageMetadata(url="another_couple.jpg", source="test", face_count=2),
        ]

        # Filter for couples (2 faces)
        filtered = crawler.filter_couples(images, min_faces=2, max_faces=2)

        assert len(filtered) == 2
        assert all(img.face_count == 2 for img in filtered)

    @pytest.mark.asyncio
    async def test_filter_by_resolution(self):
        """Test filtering images by resolution"""
        class MockCrawler(BaseCrawler):
            def get_source_name(self):
                return "mock"

            async def search(self, query, limit=20, filters=None):
                return []

            async def download_image(self, url, save_path):
                return True

        crawler = MockCrawler()

        images = [
            ImageMetadata(url="low_res.jpg", source="test", width=640, height=480),
            ImageMetadata(url="hd.jpg", source="test", width=1920, height=1080),
            ImageMetadata(url="4k.jpg", source="test", width=3840, height=2160),
        ]

        # Filter for HD+ (min 1920x1080)
        filtered = crawler.filter_by_resolution(images, min_width=1920, min_height=1080)

        assert len(filtered) == 2
        assert all(img.width >= 1920 and img.height >= 1080 for img in filtered)


class TestDanbooruCrawler:
    """Test Danbooru crawler"""

    def test_danbooru_crawler_init(self):
        """Test Danbooru crawler initialization"""
        crawler = DanbooruCrawler()

        assert crawler.get_source_name() == "danbooru"
        assert crawler.base_url == "https://danbooru.donmai.us"
        assert crawler.config.rate_limit_delay == 0.6  # Conservative rate

    @pytest.mark.asyncio
    async def test_danbooru_couple_tags(self):
        """Test getting couple tags for Danbooru"""
        crawler = DanbooruCrawler()

        tags = await crawler.get_couple_tags()

        assert isinstance(tags, list)
        assert "1boy_1girl" in tags
        assert "2girls" in tags
        assert "couple" in tags

    @pytest.mark.asyncio
    async def test_danbooru_search_couples(self):
        """Test Danbooru couple search (mocked)"""
        crawler = DanbooruCrawler()

        # Mock the search method
        with patch.object(crawler, 'search', new=AsyncMock()) as mock_search:
            mock_search.return_value = [
                ImageMetadata(
                    url="https://danbooru.donmai.us/data/test1.jpg",
                    source="danbooru",
                    tags=["1boy_1girl", "couple"],
                    width=1920,
                    height=1080
                )
            ]

            results = await crawler.search_couples(limit=10, safe_only=True)

            # Verify search was called with correct parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args

            assert "limit" in call_args.kwargs
            assert call_args.kwargs["limit"] == 10


class TestPixivCrawler:
    """Test Pixiv crawler"""

    def test_pixiv_crawler_init(self):
        """Test Pixiv crawler initialization"""
        crawler = PixivCrawler(refresh_token="test_token")

        assert crawler.get_source_name() == "pixiv"
        assert crawler.refresh_token == "test_token"
        assert crawler.config.rate_limit_delay == 2.0  # Stricter for Pixiv

    @pytest.mark.asyncio
    async def test_pixiv_popular_couple_tags(self):
        """Test getting popular couple tags for Pixiv"""
        crawler = PixivCrawler()

        tags = await crawler.get_popular_couple_tags()

        assert isinstance(tags, list)
        assert "カップル" in tags  # "Couple" in Japanese
        assert "2人" in tags  # "Two people"
        assert "couple" in tags


class TestCatcherAPI:
    """Test Catcher API endpoints"""

    def test_create_crawl_task(self):
        """Test creating a crawl task"""
        response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "danbooru",
                "search_query": "1boy_1girl",
                "category": "acg",
                "filters": {
                    "min_score": 10,
                    "rating": "s"
                },
                "limit": 50
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert "task_id" in data
        assert data["source_type"] == "danbooru"
        assert data["search_query"] == "1boy_1girl"
        assert data["status"] == "pending"
        assert data["target_count"] == 50

    def test_create_crawl_task_invalid_source(self):
        """Test creating task with invalid source"""
        response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "invalid_source",
                "search_query": "test",
                "limit": 10
            }
        )

        assert response.status_code == 400
        assert "Invalid source_type" in response.json()["detail"]

    def test_get_crawl_task_status(self):
        """Test getting crawl task status"""
        # First create a task
        create_response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "danbooru",
                "search_query": "couple",
                "limit": 20
            }
        )

        task_id = create_response.json()["task_id"]

        # Get task status
        response = client.get(f"/api/v1/catcher/crawl-tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == task_id
        assert data["status"] == "pending"
        assert "images_collected" in data
        assert "progress" in data

    def test_get_nonexistent_task(self):
        """Test getting non-existent task"""
        response = client.get("/api/v1/catcher/crawl-tasks/nonexistent_task_id")

        assert response.status_code == 404

    def test_list_crawl_tasks(self):
        """Test listing crawl tasks"""
        # Create a few tasks
        for i in range(3):
            client.post(
                "/api/v1/catcher/crawl-tasks",
                json={
                    "source_type": "danbooru",
                    "search_query": f"query_{i}",
                    "limit": 10
                }
            )

        # List all tasks
        response = client.get("/api/v1/catcher/crawl-tasks")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 3

    def test_list_crawl_tasks_with_filters(self):
        """Test listing tasks with status filter"""
        response = client.get(
            "/api/v1/catcher/crawl-tasks",
            params={"status": "pending", "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()

        # All returned tasks should be pending
        for task in data:
            assert task["status"] == "pending"


class TestCrawlTaskManagement:
    """Test crawl task lifecycle management"""

    def test_start_crawl_task(self):
        """Test starting a crawl task"""
        # Create task
        create_response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "danbooru",
                "search_query": "test",
                "limit": 10
            }
        )

        task_id = create_response.json()["task_id"]

        # Start task
        response = client.post(f"/api/v1/catcher/crawl-tasks/{task_id}/start")

        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify status changed
        status_response = client.get(f"/api/v1/catcher/crawl-tasks/{task_id}")
        assert status_response.json()["status"] == "running"

    def test_pause_crawl_task(self):
        """Test pausing a running task"""
        # Create and start task
        create_response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "danbooru",
                "search_query": "test",
                "limit": 10
            }
        )

        task_id = create_response.json()["task_id"]
        client.post(f"/api/v1/catcher/crawl-tasks/{task_id}/start")

        # Pause task
        response = client.post(f"/api/v1/catcher/crawl-tasks/{task_id}/pause")

        assert response.status_code == 200

        # Verify status
        status_response = client.get(f"/api/v1/catcher/crawl-tasks/{task_id}")
        assert status_response.json()["status"] == "paused"

    def test_resume_crawl_task(self):
        """Test resuming a paused task"""
        # Create, start, and pause task
        create_response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "danbooru",
                "search_query": "test",
                "limit": 10
            }
        )

        task_id = create_response.json()["task_id"]
        client.post(f"/api/v1/catcher/crawl-tasks/{task_id}/start")
        client.post(f"/api/v1/catcher/crawl-tasks/{task_id}/pause")

        # Resume task
        response = client.post(f"/api/v1/catcher/crawl-tasks/{task_id}/resume")

        assert response.status_code == 200

        # Verify status
        status_response = client.get(f"/api/v1/catcher/crawl-tasks/{task_id}")
        assert status_response.json()["status"] == "running"

    def test_cancel_crawl_task(self):
        """Test cancelling a task"""
        # Create and start task
        create_response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "danbooru",
                "search_query": "test",
                "limit": 10
            }
        )

        task_id = create_response.json()["task_id"]
        client.post(f"/api/v1/catcher/crawl-tasks/{task_id}/start")

        # Cancel task
        response = client.post(f"/api/v1/catcher/crawl-tasks/{task_id}/cancel")

        assert response.status_code == 200

        # Verify status
        status_response = client.get(f"/api/v1/catcher/crawl-tasks/{task_id}")
        assert status_response.json()["status"] == "failed"
        assert "Cancelled" in status_response.json()["error_message"]


class TestCollectedImages:
    """Test collected images API"""

    def test_get_collected_images_empty(self):
        """Test getting images from a task with no images"""
        # Create task
        create_response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "danbooru",
                "search_query": "test",
                "limit": 10
            }
        )

        task_id = create_response.json()["task_id"]

        # Get collected images
        response = client.get(f"/api/v1/catcher/crawl-tasks/{task_id}/images")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0  # No images collected yet


class TestCatcherStatistics:
    """Test crawler statistics endpoint"""

    def test_get_crawler_stats(self):
        """Test getting overall crawler statistics"""
        response = client.get("/api/v1/catcher/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_tasks" in data
        assert "tasks_by_status" in data
        assert "total_images_collected" in data
        assert "images_saved_as_templates" in data

        # Verify tasks_by_status structure
        assert "pending" in data["tasks_by_status"]
        assert "running" in data["tasks_by_status"]
        assert "completed" in data["tasks_by_status"]


class TestAvailableSources:
    """Test available sources listing"""

    def test_list_sources(self):
        """Test listing available image sources"""
        response = client.get("/api/v1/catcher/sources")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 2  # At least pixiv and danbooru

        # Find pixiv source
        pixiv = next((s for s in data if s["name"] == "pixiv"), None)
        assert pixiv is not None
        assert pixiv["requires_auth"] is True
        assert "rate_limit" in pixiv
        assert "couple_tags" in pixiv

        # Find danbooru source
        danbooru = next((s for s in data if s["name"] == "danbooru"), None)
        assert danbooru is not None
        assert danbooru["requires_auth"] is False


class TestCatcherValidation:
    """Test input validation"""

    def test_create_task_missing_fields(self):
        """Test creating task with missing required fields"""
        response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "danbooru"
                # Missing search_query and limit
            }
        )

        assert response.status_code == 422  # Validation error

    def test_create_task_invalid_limit(self):
        """Test creating task with invalid limit"""
        response = client.post(
            "/api/v1/catcher/crawl-tasks",
            json={
                "source_type": "danbooru",
                "search_query": "test",
                "limit": 10000  # Exceeds maximum
            }
        )

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
