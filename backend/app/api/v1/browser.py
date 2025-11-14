"""
Browser Service API - Image Management & Advanced Search (Phase 4)

Provides endpoints for:
- Advanced search with multiple filters
- Tag management (create, add to images, remove)
- Favorites management
- Collections (create, manage items)
- Image metadata editing
- Search suggestions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from app.core.database import get_db
from app.models.database import (
    Image, Template, Tag, ImageTag, Collection, CollectionItem,
    Favorite, SearchHistory
)
from app.models.schemas import (
    TagCreate, TagResponse, ImageTagCreate, ImageTagResponse,
    CollectionCreate, CollectionUpdate, CollectionResponse,
    CollectionItemCreate, CollectionItemResponse,
    FavoriteCreate, FavoriteResponse,
    AdvancedSearchRequest, AdvancedSearchResponse,
    ImageMetadataUpdate, BatchTagOperation, SearchSuggestionResponse
)

router = APIRouter(prefix="/browser", tags=["browser"])
logger = logging.getLogger(__name__)


# ======================================
# Advanced Search Endpoints
# ======================================

@router.post("/search", response_model=AdvancedSearchResponse)
async def advanced_search(
    request: AdvancedSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Advanced search with multiple filters

    Supports:
    - Text search in names/descriptions
    - Tag filters
    - Category filters
    - Dimension filters (min width/height)
    - Face count filters
    - Preprocessing status filter
    - Custom sorting

    Returns both templates and images based on filters
    """
    try:
        # Start with template query
        query = db.query(Template)

        # Text search
        if request.query:
            query = query.filter(
                or_(
                    Template.name.ilike(f"%{request.query}%"),
                    Template.description.ilike(f"%{request.query}%")
                )
            )

        # Category filter
        if request.category:
            query = query.filter(Template.category == request.category)

        # Dimension filters
        if request.min_width or request.min_height:
            query = query.join(Image, Template.original_image_id == Image.id)
            if request.min_width:
                query = query.filter(Image.width >= request.min_width)
            if request.min_height:
                query = query.filter(Image.height >= request.min_height)

        # Face count filters
        if request.min_faces is not None:
            query = query.filter(Template.face_count >= request.min_faces)
        if request.max_faces is not None:
            query = query.filter(Template.face_count <= request.max_faces)

        # Preprocessing filter
        if request.has_preprocessing is not None:
            query = query.filter(Template.is_preprocessed == request.has_preprocessing)

        # Tag filters
        if request.tags:
            # Find templates with all specified tags
            for tag_name in request.tags:
                query = query.join(ImageTag, Template.original_image_id == ImageTag.image_id)\
                            .join(Tag, ImageTag.tag_id == Tag.id)\
                            .filter(Tag.name == tag_name)

        # Get total count before pagination
        total = query.count()

        # Sorting
        sort_field = getattr(Template, request.sort_by, Template.created_at)
        if request.sort_order == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        # Pagination
        results = query.offset(request.skip).limit(request.limit).all()

        # Convert to dict
        results_list = []
        for template in results:
            results_list.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "face_count": template.face_count,
                "male_face_count": template.male_face_count,
                "female_face_count": template.female_face_count,
                "is_preprocessed": template.is_preprocessed,
                "popularity_score": template.popularity_score,
                "created_at": template.created_at.isoformat()
            })

        # Record search history
        if request.query:
            search_record = SearchHistory(
                query=request.query,
                filters={
                    "category": request.category,
                    "tags": request.tags,
                    "min_width": request.min_width,
                    "min_height": request.min_height
                },
                result_count=total
            )
            db.add(search_record)
            db.commit()

        logger.info(
            f"Advanced search: {total} results",
            extra={"query": request.query, "filters": request.dict()}
        )

        return AdvancedSearchResponse(
            results=results_list,
            total=total,
            query=request.query,
            filters_applied={
                "category": request.category,
                "tags": request.tags,
                "dimensions": {
                    "min_width": request.min_width,
                    "min_height": request.min_height
                },
                "faces": {
                    "min": request.min_faces,
                    "max": request.max_faces
                }
            }
        )

    except Exception as e:
        logger.error(f"Error in advanced search: {e}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/suggestions", response_model=SearchSuggestionResponse)
async def get_search_suggestions(
    query: Optional[str] = Query(None, min_length=1),
    db: Session = Depends(get_db)
):
    """
    Get search suggestions based on query

    Returns:
    - Auto-complete suggestions
    - Popular tags
    - Recent searches
    """
    suggestions = []

    # Get template name suggestions
    if query:
        templates = db.query(Template.name)\
            .filter(Template.name.ilike(f"%{query}%"))\
            .limit(5)\
            .all()
        suggestions = [t.name for t in templates]

    # Get popular tags
    popular_tags = db.query(Tag)\
        .order_by(Tag.usage_count.desc())\
        .limit(10)\
        .all()

    # Get recent searches
    recent_searches = db.query(SearchHistory.query)\
        .order_by(SearchHistory.searched_at.desc())\
        .distinct()\
        .limit(5)\
        .all()

    return SearchSuggestionResponse(
        suggestions=suggestions,
        popular_tags=[TagResponse.from_orm(tag) for tag in popular_tags],
        recent_searches=[s.query for s in recent_searches]
    )


# ======================================
# Tag Management Endpoints
# ======================================

@router.post("/tags", response_model=TagResponse, status_code=201)
async def create_tag(
    request: TagCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new tag

    Tags can be used to categorize and organize images/templates
    """
    # Check if tag already exists
    existing = db.query(Tag).filter(Tag.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag = Tag(
        name=request.name,
        category=request.category,
        description=request.description,
        is_system=False
    )

    db.add(tag)
    db.commit()
    db.refresh(tag)

    logger.info(f"Created tag: {request.name}", extra={"tag_id": tag.id})

    return TagResponse.from_orm(tag)


@router.get("/tags", response_model=List[TagResponse])
async def list_tags(
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List all tags with optional category filter
    """
    query = db.query(Tag)

    if category:
        query = query.filter(Tag.category == category)

    tags = query.order_by(Tag.usage_count.desc()).offset(skip).limit(limit).all()

    return [TagResponse.from_orm(tag) for tag in tags]


@router.post("/tags/add-to-image", response_model=ImageTagResponse, status_code=201)
async def add_tag_to_image(
    request: ImageTagCreate,
    db: Session = Depends(get_db)
):
    """
    Add a tag to an image

    Creates association between image and tag
    """
    # Check if image exists
    image = db.query(Image).filter(Image.id == request.image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Check if tag exists
    tag = db.query(Tag).filter(Tag.id == request.tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Check if association already exists
    existing = db.query(ImageTag).filter(
        ImageTag.image_id == request.image_id,
        ImageTag.tag_id == request.tag_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Tag already added to this image")

    # Create association
    image_tag = ImageTag(
        image_id=request.image_id,
        tag_id=request.tag_id,
        confidence=request.confidence,
        created_by="user"
    )

    # Update tag usage count
    tag.usage_count += 1

    db.add(image_tag)
    db.commit()
    db.refresh(image_tag)

    logger.info(
        f"Added tag {tag.name} to image {request.image_id}",
        extra={"image_id": request.image_id, "tag_id": request.tag_id}
    )

    return ImageTagResponse(
        id=image_tag.id,
        image_id=image_tag.image_id,
        tag_id=image_tag.tag_id,
        tag_name=tag.name,
        confidence=image_tag.confidence,
        created_by=image_tag.created_by,
        created_at=image_tag.created_at
    )


@router.delete("/tags/{image_id}/{tag_id}")
async def remove_tag_from_image(
    image_id: int,
    tag_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove a tag from an image
    """
    image_tag = db.query(ImageTag).filter(
        ImageTag.image_id == image_id,
        ImageTag.tag_id == tag_id
    ).first()

    if not image_tag:
        raise HTTPException(status_code=404, detail="Tag association not found")

    # Update tag usage count
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if tag and tag.usage_count > 0:
        tag.usage_count -= 1

    db.delete(image_tag)
    db.commit()

    logger.info(
        f"Removed tag {tag_id} from image {image_id}",
        extra={"image_id": image_id, "tag_id": tag_id}
    )

    return {"status": "success", "message": "Tag removed"}


@router.post("/tags/batch")
async def batch_tag_operation(
    request: BatchTagOperation,
    db: Session = Depends(get_db)
):
    """
    Perform batch tag operations on multiple images

    Operations:
    - add: Add tags to all specified images
    - remove: Remove tags from all specified images
    """
    results = {
        "success": 0,
        "failed": 0,
        "errors": []
    }

    for image_id in request.image_ids:
        for tag_id in request.tag_ids:
            try:
                if request.operation == "add":
                    # Check if already exists
                    existing = db.query(ImageTag).filter(
                        ImageTag.image_id == image_id,
                        ImageTag.tag_id == tag_id
                    ).first()

                    if not existing:
                        image_tag = ImageTag(
                            image_id=image_id,
                            tag_id=tag_id,
                            created_by="user"
                        )
                        db.add(image_tag)

                        # Update usage count
                        tag = db.query(Tag).filter(Tag.id == tag_id).first()
                        if tag:
                            tag.usage_count += 1

                        results["success"] += 1

                elif request.operation == "remove":
                    image_tag = db.query(ImageTag).filter(
                        ImageTag.image_id == image_id,
                        ImageTag.tag_id == tag_id
                    ).first()

                    if image_tag:
                        db.delete(image_tag)

                        # Update usage count
                        tag = db.query(Tag).filter(Tag.id == tag_id).first()
                        if tag and tag.usage_count > 0:
                            tag.usage_count -= 1

                        results["success"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "image_id": image_id,
                    "tag_id": tag_id,
                    "error": str(e)
                })

    db.commit()

    logger.info(
        f"Batch tag operation: {results['success']} success, {results['failed']} failed",
        extra={"operation": request.operation, "results": results}
    )

    return results


@router.get("/images/{image_id}/tags", response_model=List[ImageTagResponse])
async def get_image_tags(
    image_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all tags for a specific image
    """
    image_tags = db.query(ImageTag, Tag)\
        .join(Tag, ImageTag.tag_id == Tag.id)\
        .filter(ImageTag.image_id == image_id)\
        .all()

    results = []
    for image_tag, tag in image_tags:
        results.append(ImageTagResponse(
            id=image_tag.id,
            image_id=image_tag.image_id,
            tag_id=image_tag.tag_id,
            tag_name=tag.name,
            confidence=image_tag.confidence,
            created_by=image_tag.created_by,
            created_at=image_tag.created_at
        ))

    return results


# ======================================
# Collection Management Endpoints
# ======================================

@router.post("/collections", response_model=CollectionResponse, status_code=201)
async def create_collection(
    request: CollectionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new collection

    Collections allow users to organize images/templates into groups
    """
    collection = Collection(
        name=request.name,
        description=request.description,
        is_public=request.is_public,
        image_count=0
    )

    db.add(collection)
    db.commit()
    db.refresh(collection)

    logger.info(f"Created collection: {request.name}", extra={"collection_id": collection.id})

    return CollectionResponse.from_orm(collection)


@router.get("/collections", response_model=List[CollectionResponse])
async def list_collections(
    is_public: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List collections with optional public filter
    """
    query = db.query(Collection)

    if is_public is not None:
        query = query.filter(Collection.is_public == is_public)

    collections = query.order_by(Collection.created_at.desc())\
        .offset(skip).limit(limit).all()

    return [CollectionResponse.from_orm(c) for c in collections]


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific collection
    """
    collection = db.query(Collection).filter(Collection.id == collection_id).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return CollectionResponse.from_orm(collection)


@router.patch("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    request: CollectionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update collection metadata
    """
    collection = db.query(Collection).filter(Collection.id == collection_id).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if request.name is not None:
        collection.name = request.name
    if request.description is not None:
        collection.description = request.description
    if request.is_public is not None:
        collection.is_public = request.is_public
    if request.cover_image_id is not None:
        collection.cover_image_id = request.cover_image_id

    collection.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(collection)

    logger.info(f"Updated collection {collection_id}", extra={"collection_id": collection_id})

    return CollectionResponse.from_orm(collection)


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a collection and all its items
    """
    collection = db.query(Collection).filter(Collection.id == collection_id).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Delete all items
    db.query(CollectionItem).filter(CollectionItem.collection_id == collection_id).delete()

    # Delete collection
    db.delete(collection)
    db.commit()

    logger.info(f"Deleted collection {collection_id}", extra={"collection_id": collection_id})

    return {"status": "success", "message": "Collection deleted"}


@router.post("/collections/items", response_model=CollectionItemResponse, status_code=201)
async def add_item_to_collection(
    request: CollectionItemCreate,
    db: Session = Depends(get_db)
):
    """
    Add an image or template to a collection
    """
    # Verify collection exists
    collection = db.query(Collection).filter(Collection.id == request.collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Get current max order
    max_order = db.query(func.max(CollectionItem.order))\
        .filter(CollectionItem.collection_id == request.collection_id)\
        .scalar() or 0

    # Create item
    item = CollectionItem(
        collection_id=request.collection_id,
        image_id=request.image_id,
        template_id=request.template_id,
        notes=request.notes,
        order=max_order + 1
    )

    # Update collection count
    collection.image_count += 1
    collection.updated_at = datetime.utcnow()

    db.add(item)
    db.commit()
    db.refresh(item)

    logger.info(
        f"Added item to collection {request.collection_id}",
        extra={"collection_id": request.collection_id, "item_id": item.id}
    )

    return CollectionItemResponse.from_orm(item)


@router.get("/collections/{collection_id}/items", response_model=List[CollectionItemResponse])
async def get_collection_items(
    collection_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get all items in a collection
    """
    items = db.query(CollectionItem)\
        .filter(CollectionItem.collection_id == collection_id)\
        .order_by(CollectionItem.order.asc())\
        .offset(skip).limit(limit)\
        .all()

    return [CollectionItemResponse.from_orm(item) for item in items]


@router.delete("/collections/items/{item_id}")
async def remove_item_from_collection(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove an item from a collection
    """
    item = db.query(CollectionItem).filter(CollectionItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Collection item not found")

    collection_id = item.collection_id

    # Update collection count
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if collection and collection.image_count > 0:
        collection.image_count -= 1
        collection.updated_at = datetime.utcnow()

    db.delete(item)
    db.commit()

    logger.info(
        f"Removed item {item_id} from collection {collection_id}",
        extra={"item_id": item_id, "collection_id": collection_id}
    )

    return {"status": "success", "message": "Item removed from collection"}


# ======================================
# Favorites Endpoints
# ======================================

@router.post("/favorites", response_model=FavoriteResponse, status_code=201)
async def add_favorite(
    request: FavoriteCreate,
    db: Session = Depends(get_db)
):
    """
    Add an image or template to favorites
    """
    # Check if already favorited
    existing = db.query(Favorite).filter(
        or_(
            Favorite.image_id == request.image_id,
            Favorite.template_id == request.template_id
        )
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already favorited")

    favorite = Favorite(
        image_id=request.image_id,
        template_id=request.template_id
    )

    db.add(favorite)
    db.commit()
    db.refresh(favorite)

    logger.info(f"Added favorite", extra={"favorite_id": favorite.id})

    return FavoriteResponse.from_orm(favorite)


@router.get("/favorites", response_model=List[FavoriteResponse])
async def list_favorites(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    List all favorites
    """
    favorites = db.query(Favorite)\
        .order_by(Favorite.favorited_at.desc())\
        .offset(skip).limit(limit)\
        .all()

    return [FavoriteResponse.from_orm(f) for f in favorites]


@router.delete("/favorites/{favorite_id}")
async def remove_favorite(
    favorite_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove a favorite
    """
    favorite = db.query(Favorite).filter(Favorite.id == favorite_id).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(favorite)
    db.commit()

    logger.info(f"Removed favorite {favorite_id}", extra={"favorite_id": favorite_id})

    return {"status": "success", "message": "Favorite removed"}


# ======================================
# Image Metadata Editor
# ======================================

@router.patch("/images/{image_id}/metadata")
async def update_image_metadata(
    image_id: int,
    request: ImageMetadataUpdate,
    db: Session = Depends(get_db)
):
    """
    Update image metadata

    Allows editing:
    - Filename
    - Category
    - Tags (will replace existing tags)
    """
    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if request.filename is not None:
        image.filename = request.filename

    if request.category is not None:
        image.category = request.category

    if request.tags is not None:
        # Remove existing tags
        db.query(ImageTag).filter(ImageTag.image_id == image_id).delete()

        # Add new tags
        for tag_name in request.tags:
            # Find or create tag
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, is_system=False)
                db.add(tag)
                db.flush()

            # Create association
            image_tag = ImageTag(
                image_id=image_id,
                tag_id=tag.id,
                created_by="user"
            )
            db.add(image_tag)

            # Update usage count
            tag.usage_count += 1

    db.commit()
    db.refresh(image)

    logger.info(f"Updated image metadata for {image_id}", extra={"image_id": image_id})

    return {
        "status": "success",
        "message": "Image metadata updated",
        "image_id": image_id
    }
