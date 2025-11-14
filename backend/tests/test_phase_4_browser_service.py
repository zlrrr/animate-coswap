"""
Phase 4 - Browser Service Tests

Tests for image management, advanced search, tags, collections, and favorites.

Test Coverage:
- Advanced search with multiple filters
- Tag management (CRUD operations)
- Image tagging
- Collections (create, update, add/remove items)
- Favorites management
- Image metadata editing
- Search suggestions
- Batch operations
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import io
from PIL import Image

from app.main import app
from app.core.database import get_db
from app.models.database import Base

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


@pytest.fixture
def create_test_image():
    """Factory to create test images"""
    def _create_image(width=800, height=600, color=(255, 0, 0)):
        img = Image.new('RGB', (width, height), color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes

    return _create_image


@pytest.fixture
def create_test_template(create_test_image):
    """Create a test template for testing"""
    img_bytes = create_test_image()

    response = client.post(
        "/api/v1/templates/upload",
        files={"file": ("test_template.jpg", img_bytes, "image/jpeg")},
        data={
            "name": "Test Template",
            "category": "test"
        }
    )

    return response.json()


# ======================================
# Tag Management Tests
# ======================================

class TestTagManagement:
    """Test tag CRUD operations"""

    def test_create_tag(self):
        """Test creating a new tag"""
        response = client.post(
            "/api/v1/browser/tags",
            json={
                "name": "romantic",
                "category": "scene",
                "description": "Romantic scenes"
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "romantic"
        assert data["category"] == "scene"
        assert data["usage_count"] == 0
        assert data["is_system"] is False

    def test_create_duplicate_tag(self):
        """Test creating duplicate tag fails"""
        # Create first tag
        client.post(
            "/api/v1/browser/tags",
            json={"name": "duplicate_tag"}
        )

        # Try to create duplicate
        response = client.post(
            "/api/v1/browser/tags",
            json={"name": "duplicate_tag"}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_list_tags(self):
        """Test listing all tags"""
        # Create a few tags
        for i in range(3):
            client.post(
                "/api/v1/browser/tags",
                json={"name": f"test_tag_{i}", "category": "test"}
            )

        response = client.get("/api/v1/browser/tags")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 3

    def test_list_tags_by_category(self):
        """Test filtering tags by category"""
        response = client.get("/api/v1/browser/tags?category=test")

        assert response.status_code == 200
        data = response.json()

        # All returned tags should have category="test"
        for tag in data:
            assert tag["category"] == "test"


# ======================================
# Image Tagging Tests
# ======================================

class TestImageTagging:
    """Test image-tag associations"""

    def test_add_tag_to_image(self, create_test_template):
        """Test adding a tag to an image"""
        template = create_test_template

        # Create a tag
        tag_response = client.post(
            "/api/v1/browser/tags",
            json={"name": "beautiful"}
        )
        tag_id = tag_response.json()["id"]

        # Add tag to template's image
        response = client.post(
            "/api/v1/browser/tags/add-to-image",
            json={
                "image_id": template["original_image_id"],
                "tag_id": tag_id
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["image_id"] == template["original_image_id"]
        assert data["tag_id"] == tag_id
        assert data["tag_name"] == "beautiful"
        assert data["created_by"] == "user"

    def test_add_duplicate_tag_to_image(self, create_test_template):
        """Test adding same tag twice fails"""
        template = create_test_template

        tag_response = client.post(
            "/api/v1/browser/tags",
            json={"name": "duplicate_image_tag"}
        )
        tag_id = tag_response.json()["id"]

        # Add tag first time
        client.post(
            "/api/v1/browser/tags/add-to-image",
            json={
                "image_id": template["original_image_id"],
                "tag_id": tag_id
            }
        )

        # Try to add again
        response = client.post(
            "/api/v1/browser/tags/add-to-image",
            json={
                "image_id": template["original_image_id"],
                "tag_id": tag_id
            }
        )

        assert response.status_code == 400

    def test_remove_tag_from_image(self, create_test_template):
        """Test removing a tag from an image"""
        template = create_test_template

        # Create and add tag
        tag_response = client.post(
            "/api/v1/browser/tags",
            json={"name": "to_remove"}
        )
        tag_id = tag_response.json()["id"]

        client.post(
            "/api/v1/browser/tags/add-to-image",
            json={
                "image_id": template["original_image_id"],
                "tag_id": tag_id
            }
        )

        # Remove tag
        response = client.delete(
            f"/api/v1/browser/tags/{template['original_image_id']}/{tag_id}"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_get_image_tags(self, create_test_template):
        """Test getting all tags for an image"""
        template = create_test_template

        # Add multiple tags
        tag_names = ["tag1", "tag2", "tag3"]
        for name in tag_names:
            tag_resp = client.post(
                "/api/v1/browser/tags",
                json={"name": name}
            )
            tag_id = tag_resp.json()["id"]

            client.post(
                "/api/v1/browser/tags/add-to-image",
                json={
                    "image_id": template["original_image_id"],
                    "tag_id": tag_id
                }
            )

        # Get all tags
        response = client.get(
            f"/api/v1/browser/images/{template['original_image_id']}/tags"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 3


# ======================================
# Batch Operations Tests
# ======================================

class TestBatchOperations:
    """Test batch tag operations"""

    def test_batch_add_tags(self, create_test_template):
        """Test adding tags to multiple images in batch"""
        # Create multiple templates
        templates = [create_test_template for _ in range(3)]
        image_ids = [t["original_image_id"] for t in templates]

        # Create tags
        tag_ids = []
        for i in range(2):
            tag_resp = client.post(
                "/api/v1/browser/tags",
                json={"name": f"batch_tag_{i}"}
            )
            tag_ids.append(tag_resp.json()["id"])

        # Batch add
        response = client.post(
            "/api/v1/browser/tags/batch",
            json={
                "image_ids": image_ids,
                "tag_ids": tag_ids,
                "operation": "add"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] >= 1
        assert data["failed"] == 0

    def test_batch_remove_tags(self, create_test_template):
        """Test removing tags from multiple images in batch"""
        template = create_test_template
        image_ids = [template["original_image_id"]]

        # Create and add tag
        tag_resp = client.post(
            "/api/v1/browser/tags",
            json={"name": "batch_remove_tag"}
        )
        tag_id = tag_resp.json()["id"]

        client.post(
            "/api/v1/browser/tags/add-to-image",
            json={"image_id": image_ids[0], "tag_id": tag_id}
        )

        # Batch remove
        response = client.post(
            "/api/v1/browser/tags/batch",
            json={
                "image_ids": image_ids,
                "tag_ids": [tag_id],
                "operation": "remove"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] >= 1


# ======================================
# Collection Tests
# ======================================

class TestCollections:
    """Test collection management"""

    def test_create_collection(self):
        """Test creating a new collection"""
        response = client.post(
            "/api/v1/browser/collections",
            json={
                "name": "My Favorite Templates",
                "description": "Collection of my favorite couple templates",
                "is_public": False
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "My Favorite Templates"
        assert data["is_public"] is False
        assert data["image_count"] == 0

    def test_list_collections(self):
        """Test listing collections"""
        # Create a few collections
        for i in range(3):
            client.post(
                "/api/v1/browser/collections",
                json={"name": f"Collection {i}", "is_public": i % 2 == 0}
            )

        response = client.get("/api/v1/browser/collections")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 3

    def test_get_collection(self):
        """Test getting a specific collection"""
        # Create collection
        create_resp = client.post(
            "/api/v1/browser/collections",
            json={"name": "Test Collection"}
        )
        collection_id = create_resp.json()["id"]

        # Get collection
        response = client.get(f"/api/v1/browser/collections/{collection_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == collection_id
        assert data["name"] == "Test Collection"

    def test_update_collection(self):
        """Test updating collection"""
        # Create collection
        create_resp = client.post(
            "/api/v1/browser/collections",
            json={"name": "Original Name"}
        )
        collection_id = create_resp.json()["id"]

        # Update collection
        response = client.patch(
            f"/api/v1/browser/collections/{collection_id}",
            json={
                "name": "Updated Name",
                "description": "New description",
                "is_public": True
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"
        assert data["is_public"] is True

    def test_delete_collection(self):
        """Test deleting a collection"""
        # Create collection
        create_resp = client.post(
            "/api/v1/browser/collections",
            json={"name": "To Delete"}
        )
        collection_id = create_resp.json()["id"]

        # Delete collection
        response = client.delete(f"/api/v1/browser/collections/{collection_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify deleted
        get_resp = client.get(f"/api/v1/browser/collections/{collection_id}")
        assert get_resp.status_code == 404


# ======================================
# Collection Items Tests
# ======================================

class TestCollectionItems:
    """Test collection item management"""

    def test_add_item_to_collection(self, create_test_template):
        """Test adding an item to a collection"""
        template = create_test_template

        # Create collection
        coll_resp = client.post(
            "/api/v1/browser/collections",
            json={"name": "Test Collection"}
        )
        collection_id = coll_resp.json()["id"]

        # Add template to collection
        response = client.post(
            "/api/v1/browser/collections/items",
            json={
                "collection_id": collection_id,
                "template_id": template["id"],
                "notes": "Great template!"
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["collection_id"] == collection_id
        assert data["template_id"] == template["id"]
        assert data["notes"] == "Great template!"

    def test_list_collection_items(self, create_test_template):
        """Test listing items in a collection"""
        template = create_test_template

        # Create collection and add items
        coll_resp = client.post(
            "/api/v1/browser/collections",
            json={"name": "Test Collection"}
        )
        collection_id = coll_resp.json()["id"]

        # Add multiple items
        for i in range(3):
            client.post(
                "/api/v1/browser/collections/items",
                json={
                    "collection_id": collection_id,
                    "template_id": template["id"]
                }
            )

        # List items
        response = client.get(f"/api/v1/browser/collections/{collection_id}/items")

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1

    def test_remove_item_from_collection(self, create_test_template):
        """Test removing an item from collection"""
        template = create_test_template

        # Create collection and add item
        coll_resp = client.post(
            "/api/v1/browser/collections",
            json={"name": "Test Collection"}
        )
        collection_id = coll_resp.json()["id"]

        item_resp = client.post(
            "/api/v1/browser/collections/items",
            json={
                "collection_id": collection_id,
                "template_id": template["id"]
            }
        )
        item_id = item_resp.json()["id"]

        # Remove item
        response = client.delete(f"/api/v1/browser/collections/items/{item_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "success"


# ======================================
# Favorites Tests
# ======================================

class TestFavorites:
    """Test favorites management"""

    def test_add_favorite(self, create_test_template):
        """Test adding a favorite"""
        template = create_test_template

        response = client.post(
            "/api/v1/browser/favorites",
            json={"template_id": template["id"]}
        )

        assert response.status_code == 201
        data = response.json()

        assert data["template_id"] == template["id"]

    def test_add_duplicate_favorite(self, create_test_template):
        """Test adding duplicate favorite fails"""
        template = create_test_template

        # Add first time
        client.post(
            "/api/v1/browser/favorites",
            json={"template_id": template["id"]}
        )

        # Try to add again
        response = client.post(
            "/api/v1/browser/favorites",
            json={"template_id": template["id"]}
        )

        assert response.status_code == 400

    def test_list_favorites(self, create_test_template):
        """Test listing favorites"""
        template = create_test_template

        # Add favorite
        client.post(
            "/api/v1/browser/favorites",
            json={"template_id": template["id"]}
        )

        # List favorites
        response = client.get("/api/v1/browser/favorites")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1

    def test_remove_favorite(self, create_test_template):
        """Test removing a favorite"""
        template = create_test_template

        # Add favorite (might already exist from previous tests)
        fav_resp = client.post(
            "/api/v1/browser/favorites",
            json={"template_id": template["id"]}
        )

        # If it already exists (400), get it from the list
        if fav_resp.status_code == 400:
            list_resp = client.get("/api/v1/browser/favorites")
            favorites = list_resp.json()
            # Find the favorite for this template
            favorite_id = next(
                (f["id"] for f in favorites if f.get("template_id") == template["id"]),
                None
            )
            if not favorite_id:
                pytest.skip("Could not find or create favorite for testing")
        else:
            favorite_id = fav_resp.json()["id"]

        # Remove favorite
        response = client.delete(f"/api/v1/browser/favorites/{favorite_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "success"


# ======================================
# Advanced Search Tests
# ======================================

class TestAdvancedSearch:
    """Test advanced search functionality"""

    def test_search_by_query(self, create_test_template):
        """Test text search"""
        template = create_test_template

        response = client.post(
            "/api/v1/browser/search",
            json={
                "query": "Test",
                "skip": 0,
                "limit": 20
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "total" in data
        assert "filters_applied" in data

    def test_search_by_category(self, create_test_template):
        """Test category filter"""
        response = client.post(
            "/api/v1/browser/search",
            json={
                "category": "test",
                "skip": 0,
                "limit": 20
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["results"], list)

    def test_search_by_dimensions(self):
        """Test dimension filters"""
        response = client.post(
            "/api/v1/browser/search",
            json={
                "min_width": 800,
                "min_height": 600,
                "skip": 0,
                "limit": 20
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data

    def test_search_with_pagination(self):
        """Test pagination in search"""
        # First page
        response1 = client.post(
            "/api/v1/browser/search",
            json={"skip": 0, "limit": 5}
        )

        # Second page
        response2 = client.post(
            "/api/v1/browser/search",
            json={"skip": 5, "limit": 5}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200


class TestSearchSuggestions:
    """Test search suggestions"""

    def test_get_suggestions(self):
        """Test getting search suggestions"""
        response = client.get("/api/v1/browser/search/suggestions?query=test")

        assert response.status_code == 200
        data = response.json()

        assert "suggestions" in data
        assert "popular_tags" in data
        assert "recent_searches" in data


# ======================================
# Image Metadata Editor Tests
# ======================================

class TestImageMetadataEditor:
    """Test image metadata editing"""

    def test_update_image_metadata(self, create_test_template):
        """Test updating image metadata"""
        template = create_test_template
        image_id = template["original_image_id"]

        response = client.patch(
            f"/api/v1/browser/images/{image_id}/metadata",
            json={
                "filename": "updated_filename.jpg",
                "category": "updated_category",
                "tags": ["new_tag1", "new_tag2"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["image_id"] == image_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
