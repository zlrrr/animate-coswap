"""
Face Mapping Service

Phase 1.5 Checkpoint 1.5.3
Handles flexible face mapping with default and custom rules
"""

import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models.database import Template, TemplatePreprocessing

logger = logging.getLogger(__name__)


class FaceMappingError(Exception):
    """Base exception for face mapping errors"""
    pass


class FaceMappingService:
    """
    Service for managing face mappings

    Provides:
    - Default mapping: husband -> male faces, wife -> female faces
    - Custom mapping: user-defined source-to-target mappings
    - Validation of mapping rules
    """

    @staticmethod
    def generate_default_mapping(
        template_id: int,
        db: Session
    ) -> List[Dict]:
        """
        Generate default face mapping based on gender classification

        Default rules:
        - Husband photo -> Male faces in template
        - Wife photo -> Female faces in template

        Args:
            template_id: Template ID
            db: Database session

        Returns:
            List of face mapping dictionaries
        """
        mappings = []

        # Get template preprocessing data
        preprocessing = db.query(TemplatePreprocessing).filter(
            TemplatePreprocessing.template_id == template_id
        ).first()

        if not preprocessing or not preprocessing.face_data:
            logger.warning(
                f"No preprocessing data for template {template_id}, "
                "using fallback mapping"
            )
            # Fallback: simple sequential mapping
            # Assume 2 faces: husband->0, wife->1
            return [
                {
                    "source_photo": "husband",
                    "source_face_index": 0,
                    "target_face_index": 0
                },
                {
                    "source_photo": "wife",
                    "source_face_index": 0,
                    "target_face_index": 1
                }
            ]

        face_data = preprocessing.face_data

        # Group faces by gender
        male_faces = []
        female_faces = []

        for face in face_data:
            face_idx = face.get("index", len(male_faces) + len(female_faces))
            gender = face.get("gender", "unknown")

            if gender == "male":
                male_faces.append(face_idx)
            elif gender == "female":
                female_faces.append(face_idx)

        logger.info(
            f"Template {template_id}: {len(male_faces)} male faces, "
            f"{len(female_faces)} female faces"
        )

        # Map husband to male faces
        for male_face_idx in male_faces:
            mappings.append({
                "source_photo": "husband",
                "source_face_index": 0,
                "target_face_index": male_face_idx
            })

        # Map wife to female faces
        for female_face_idx in female_faces:
            mappings.append({
                "source_photo": "wife",
                "source_face_index": 0,
                "target_face_index": female_face_idx
            })

        logger.info(f"Generated {len(mappings)} default mappings")

        return mappings

    @staticmethod
    def validate_mapping(
        mapping: Dict,
        max_source_faces: int = 10,
        max_target_faces: int = 10
    ) -> bool:
        """
        Validate a single face mapping

        Args:
            mapping: Face mapping dictionary
            max_source_faces: Maximum source face index
            max_target_faces: Maximum target face index

        Returns:
            True if valid

        Raises:
            FaceMappingError: If mapping is invalid
        """
        # Check required fields
        required_fields = ["source_photo", "source_face_index", "target_face_index"]
        for field in required_fields:
            if field not in mapping:
                raise FaceMappingError(f"Missing required field: {field}")

        # Validate source_photo
        if mapping["source_photo"] not in ["husband", "wife"]:
            raise FaceMappingError(
                f"Invalid source_photo: {mapping['source_photo']}. "
                "Must be 'husband' or 'wife'"
            )

        # Validate indices
        source_idx = mapping["source_face_index"]
        target_idx = mapping["target_face_index"]

        if not isinstance(source_idx, int) or source_idx < 0:
            raise FaceMappingError(
                f"Invalid source_face_index: {source_idx}. Must be >= 0"
            )

        if not isinstance(target_idx, int) or target_idx < 0:
            raise FaceMappingError(
                f"Invalid target_face_index: {target_idx}. Must be >= 0"
            )

        # Check reasonable bounds
        if source_idx >= max_source_faces:
            logger.warning(
                f"source_face_index {source_idx} is high (max {max_source_faces})"
            )

        if target_idx >= max_target_faces:
            logger.warning(
                f"target_face_index {target_idx} is high (max {max_target_faces})"
            )

        return True

    @staticmethod
    def validate_mappings(mappings: List[Dict]) -> bool:
        """
        Validate all face mappings

        Args:
            mappings: List of face mapping dictionaries

        Returns:
            True if all valid

        Raises:
            FaceMappingError: If any mapping is invalid
        """
        if not isinstance(mappings, list):
            raise FaceMappingError("face_mappings must be a list")

        if len(mappings) == 0:
            raise FaceMappingError("face_mappings cannot be empty")

        for idx, mapping in enumerate(mappings):
            try:
                FaceMappingService.validate_mapping(mapping)
            except FaceMappingError as e:
                raise FaceMappingError(f"Invalid mapping at index {idx}: {str(e)}")

        return True

    @staticmethod
    def convert_to_dict(mappings: List) -> List[Dict]:
        """
        Convert mapping objects to dictionaries

        Args:
            mappings: List of mapping objects or dicts

        Returns:
            List of dictionaries
        """
        result = []

        for mapping in mappings:
            if hasattr(mapping, 'dict'):
                # Pydantic model
                result.append(mapping.dict())
            elif isinstance(mapping, dict):
                # Already a dict
                result.append(mapping)
            else:
                logger.warning(f"Unknown mapping type: {type(mapping)}")
                result.append(dict(mapping))

        return result

    @staticmethod
    def apply_mapping_to_task(
        husband_photo_id: int,
        wife_photo_id: int,
        template_id: int,
        use_default_mapping: bool,
        custom_mappings: Optional[List[Dict]],
        db: Session
    ) -> List[Dict]:
        """
        Determine and validate face mappings for a task

        Args:
            husband_photo_id: Husband photo ID
            wife_photo_id: Wife photo ID
            template_id: Template ID
            use_default_mapping: Whether to use default mapping
            custom_mappings: Custom mappings (if any)
            db: Database session

        Returns:
            Final face mappings to use

        Raises:
            FaceMappingError: If mappings are invalid
        """
        # If custom mappings provided, use them
        if custom_mappings and len(custom_mappings) > 0:
            logger.info(f"Using {len(custom_mappings)} custom mappings")

            # Validate custom mappings
            FaceMappingService.validate_mappings(custom_mappings)

            return custom_mappings

        # If default mapping requested, generate it
        if use_default_mapping:
            logger.info(f"Generating default mapping for template {template_id}")

            mappings = FaceMappingService.generate_default_mapping(
                template_id,
                db
            )

            return mappings

        # No mapping specified - use simple fallback
        logger.warning("No mapping specified, using simple fallback")

        return [
            {
                "source_photo": "husband",
                "source_face_index": 0,
                "target_face_index": 0
            },
            {
                "source_photo": "wife",
                "source_face_index": 0,
                "target_face_index": 1
            }
        ]
