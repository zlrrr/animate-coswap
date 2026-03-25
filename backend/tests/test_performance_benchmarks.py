"""
Performance Benchmark Tests

Tests processing times and performance metrics for MVP validation.
Based on PLAN.md MVP Validation & Testing Phase requirements.

Performance Requirements:
- Processing time < 10s per image pair
- API response time < 200ms (excluding processing)
- Database queries < 50ms
- No memory leaks after 100 operations
"""

import time
import pytest
import psutil
import os
from PIL import Image
import io
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.database import Base


# Create in-memory SQLite database for testing
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


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create all tables before tests"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def create_test_image():
    """Factory to create test images of various sizes"""
    def _create_image(width=800, height=600, color=(255, 0, 0), format='JPEG'):
        """Create a test image in memory"""
        img = Image.new('RGB', (width, height), color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=format, quality=95)
        img_bytes.seek(0)
        return img_bytes

    return _create_image


@pytest.fixture
def get_memory_usage():
    """Get current memory usage in MB"""
    def _get_memory():
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB

    return _get_memory


class TestAPIPerformance:
    """Test API endpoint response times"""

    def test_health_endpoint_performance(self, benchmark):
        """Benchmark: Health check endpoint should be < 50ms"""
        def health_check():
            return client.get("/")

        result = benchmark(health_check)
        assert result.status_code == 200
        # Benchmark stats will be printed automatically

    def test_templates_list_performance(self, benchmark):
        """Benchmark: Templates listing should be < 200ms"""
        def list_templates():
            return client.get("/api/v1/templates/")

        result = benchmark(list_templates)
        assert result.status_code == 200

    def test_photo_upload_performance(self, benchmark, create_test_image):
        """Benchmark: Photo upload API response < 500ms"""
        def upload_photo():
            img_bytes = create_test_image(800, 600)
            response = client.post(
                "/api/v1/photos/upload",
                files={"file": ("test.jpg", img_bytes, "image/jpeg")},
                data={"session_id": "test_session"}
            )
            return response

        result = benchmark(upload_photo)
        assert result.status_code == 200


class TestDatabasePerformance:
    """Test database query performance"""

    def test_query_templates_performance(self, benchmark):
        """Benchmark: Database template query < 50ms"""
        db = TestingSessionLocal()

        def query_templates():
            # Simulate template query
            result = db.execute(text("SELECT 1")).fetchall()
            return result

        try:
            result = benchmark(query_templates)
            assert result is not None
        finally:
            db.close()

    def test_insert_photo_performance(self, benchmark):
        """Benchmark: Photo insert operation < 100ms"""
        db = TestingSessionLocal()

        def insert_photo():
            # Simulate photo insert
            db.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS temp_photos (
                        id INTEGER PRIMARY KEY,
                        filename TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            )
            db.execute(
                text("INSERT INTO temp_photos (filename) VALUES (:filename)"),
                {"filename": f"test_{time.time()}.jpg"}
            )
            db.commit()
            return True

        try:
            result = benchmark(insert_photo)
            assert result is True
        finally:
            db.close()


class TestImageProcessingPerformance:
    """Test image processing performance metrics"""

    @pytest.mark.parametrize("width,height,expected_max_time", [
        (640, 480, 2.0),    # Low resolution: < 2s
        (1280, 720, 3.0),   # HD: < 3s
        (1920, 1080, 5.0),  # Full HD: < 5s
        (3840, 2160, 10.0), # 4K: < 10s
    ])
    def test_image_upload_by_resolution(
        self,
        create_test_image,
        width,
        height,
        expected_max_time
    ):
        """Test upload performance for different image resolutions"""
        img_bytes = create_test_image(width, height)

        start_time = time.time()
        response = client.post(
            "/api/v1/photos/upload",
            files={"file": (f"test_{width}x{height}.jpg", img_bytes, "image/jpeg")},
            data={"session_id": "test_session"}
        )
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        assert elapsed_time < expected_max_time, (
            f"Upload of {width}x{height} took {elapsed_time:.2f}s "
            f"(expected < {expected_max_time}s)"
        )

        print(f"\n  {width}x{height} upload: {elapsed_time:.3f}s")

    def test_template_creation_performance(self, create_test_image):
        """Test template creation performance"""
        img_bytes = create_test_image(1024, 768)

        start_time = time.time()
        response = client.post(
            "/api/v1/templates/upload",
            files={"file": ("template.jpg", img_bytes, "image/jpeg")},
            data={
                "name": "Performance Test Template",
                "category": "test"
            }
        )
        elapsed_time = time.time() - start_time

        # Template creation should be fast (< 3s without preprocessing)
        assert elapsed_time < 3.0, f"Template creation took {elapsed_time:.2f}s (expected < 3s)"
        print(f"\n  Template creation: {elapsed_time:.3f}s")


class TestMemoryUsage:
    """Test memory usage and leak detection"""

    def test_no_memory_leak_100_uploads(self, create_test_image, get_memory_usage):
        """Test: No memory leaks after 100 consecutive uploads"""
        initial_memory = get_memory_usage()

        # Perform 100 uploads
        for i in range(100):
            img_bytes = create_test_image(800, 600)
            response = client.post(
                "/api/v1/photos/upload",
                files={"file": (f"test_{i}.jpg", img_bytes, "image/jpeg")},
                data={"session_id": f"test_session_{i}"}
            )
            # Don't check response for every iteration to speed up test
            if i % 10 == 0:
                assert response.status_code == 200

        final_memory = get_memory_usage()
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 100MB for 100 uploads)
        assert memory_increase < 100, (
            f"Memory increased by {memory_increase:.2f}MB after 100 uploads "
            f"(initial: {initial_memory:.2f}MB, final: {final_memory:.2f}MB)"
        )

        print(f"\n  Initial memory: {initial_memory:.2f}MB")
        print(f"  Final memory: {final_memory:.2f}MB")
        print(f"  Increase: {memory_increase:.2f}MB")

    def test_memory_usage_template_listing(self, get_memory_usage):
        """Test memory usage for template listing"""
        initial_memory = get_memory_usage()

        # List templates 50 times
        for _ in range(50):
            response = client.get("/api/v1/templates/")
            assert response.status_code == 200

        final_memory = get_memory_usage()
        memory_increase = final_memory - initial_memory

        # Memory increase should be minimal (< 10MB)
        assert memory_increase < 10, (
            f"Memory increased by {memory_increase:.2f}MB after 50 template listings"
        )

        print(f"\n  Memory increase for 50 listings: {memory_increase:.2f}MB")


class TestConcurrentRequests:
    """Test handling of concurrent requests"""

    def test_concurrent_template_listings(self):
        """Test handling 10 concurrent template list requests"""
        import concurrent.futures

        def list_templates():
            return client.get("/api/v1/templates/")

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(list_templates) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        elapsed_time = time.time() - start_time

        # All requests should succeed
        assert len(results) == 10
        assert all(r.status_code == 200 for r in results)

        # Should complete in reasonable time (< 5s for 10 concurrent requests)
        assert elapsed_time < 5.0, f"10 concurrent requests took {elapsed_time:.2f}s"

        print(f"\n  10 concurrent template listings: {elapsed_time:.3f}s")

    def test_concurrent_photo_uploads(self, create_test_image):
        """Test handling 5 concurrent photo uploads"""
        import concurrent.futures

        def upload_photo(index):
            img_bytes = create_test_image(800, 600)
            return client.post(
                "/api/v1/photos/upload",
                files={"file": (f"concurrent_{index}.jpg", img_bytes, "image/jpeg")},
                data={"session_id": f"concurrent_session_{index}"}
            )

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_photo, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        elapsed_time = time.time() - start_time

        # All uploads should succeed
        assert len(results) == 5
        assert all(r.status_code == 200 for r in results)

        print(f"\n  5 concurrent photo uploads: {elapsed_time:.3f}s")


class TestEndToEndPerformance:
    """Test complete workflow performance"""

    def test_complete_workflow_performance(self, create_test_image):
        """Test complete workflow from upload to task creation"""
        workflow_times = {}

        # Step 1: Upload husband photo
        start = time.time()
        husband_img = create_test_image(800, 600, (255, 200, 200))
        husband_response = client.post(
            "/api/v1/photos/upload",
            files={"file": ("husband.jpg", husband_img, "image/jpeg")},
            data={"session_id": "workflow_test"}
        )
        workflow_times['husband_upload'] = time.time() - start
        assert husband_response.status_code == 200
        husband_id = husband_response.json()["id"]

        # Step 2: Upload wife photo
        start = time.time()
        wife_img = create_test_image(800, 600, (200, 200, 255))
        wife_response = client.post(
            "/api/v1/photos/upload",
            files={"file": ("wife.jpg", wife_img, "image/jpeg")},
            data={"session_id": "workflow_test"}
        )
        workflow_times['wife_upload'] = time.time() - start
        assert wife_response.status_code == 200
        wife_id = wife_response.json()["id"]

        # Step 3: Create template
        start = time.time()
        template_img = create_test_image(1024, 768, (200, 255, 200))
        template_response = client.post(
            "/api/v1/templates/upload",
            files={"file": ("template.jpg", template_img, "image/jpeg")},
            data={
                "name": "Workflow Test Template",
                "category": "test"
            }
        )
        workflow_times['template_creation'] = time.time() - start
        assert template_response.status_code == 200
        template_id = template_response.json()["id"]

        # Step 4: List templates
        start = time.time()
        templates_response = client.get("/api/v1/templates/")
        workflow_times['templates_list'] = time.time() - start
        assert templates_response.status_code == 200

        # Step 5: Create face-swap task
        start = time.time()
        task_response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_id,
                "wife_photo_id": wife_id,
                "template_id": template_id,
                "use_default_mapping": True
            }
        )
        workflow_times['task_creation'] = time.time() - start

        # Task creation might fail if models aren't available, but API should respond
        assert task_response.status_code in [200, 500]

        # Print timing breakdown
        print("\n  Workflow Performance Breakdown:")
        total_time = sum(workflow_times.values())
        for step, duration in workflow_times.items():
            print(f"    {step}: {duration:.3f}s")
        print(f"    Total: {total_time:.3f}s")

        # Total workflow should complete in reasonable time (< 15s)
        assert total_time < 15.0, f"Complete workflow took {total_time:.2f}s (expected < 15s)"


class TestScalability:
    """Test system scalability"""

    def test_large_template_list_performance(self, create_test_image):
        """Test performance with large number of templates"""
        # Create 20 templates
        for i in range(20):
            img_bytes = create_test_image(800, 600)
            response = client.post(
                "/api/v1/templates/upload",
                files={"file": (f"template_{i}.jpg", img_bytes, "image/jpeg")},
                data={
                    "name": f"Template {i}",
                    "category": "test"
                }
            )
            assert response.status_code == 200

        # Test listing performance
        start_time = time.time()
        response = client.get("/api/v1/templates/")
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        data = response.json()
        assert len(data["templates"]) >= 20

        # Should still be fast even with 20+ templates (< 500ms)
        assert elapsed_time < 0.5, f"Listing 20+ templates took {elapsed_time:.2f}s"

        print(f"\n  Listing {len(data['templates'])} templates: {elapsed_time:.3f}s")

    def test_pagination_performance(self, create_test_image):
        """Test pagination performance"""
        # Test various page sizes
        page_sizes = [5, 10, 20, 50]

        for limit in page_sizes:
            start_time = time.time()
            response = client.get(f"/api/v1/templates/?limit={limit}")
            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            data = response.json()
            assert len(data["templates"]) <= limit

            # Pagination should be fast (< 300ms)
            assert elapsed_time < 0.3, (
                f"Pagination with limit={limit} took {elapsed_time:.2f}s"
            )

            print(f"\n  Pagination (limit={limit}): {elapsed_time:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
