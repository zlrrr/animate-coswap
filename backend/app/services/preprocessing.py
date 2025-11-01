"""
Template Preprocessing Service

Phase 1.5 Checkpoint 1.5.2
Handles template preprocessing including:
- Face detection
- Gender classification
- Face masking
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
import os
from datetime import datetime
from sqlalchemy.orm import Session

# InsightFace will be imported when available
try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    logging.warning("InsightFace not available. Preprocessing functionality will be limited.")

from app.models.database import Template, Image, TemplatePreprocessing
from app.utils.storage import storage_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class PreprocessingError(Exception):
    """Base exception for preprocessing errors"""
    pass


class TemplatePreprocessor:
    """
    Template preprocessing service

    Handles face detection, gender classification, and face masking
    for templates to enable faster and more flexible face-swapping.
    """

    def __init__(self, use_gpu: bool = True, device_id: int = 0):
        """
        Initialize template preprocessor

        Args:
            use_gpu: Whether to use GPU acceleration
            device_id: GPU device ID
        """
        if not INSIGHTFACE_AVAILABLE:
            logger.warning("InsightFace not available - using mock preprocessing")
            self.app = None
            self.use_gpu = False
        else:
            self.use_gpu = use_gpu
            self.device_id = device_id if use_gpu else -1

            # Initialize face analysis app
            logger.info(f"Initializing FaceAnalysis for preprocessing (device_id={self.device_id})")
            self.app = FaceAnalysis(name='buffalo_l')
            self.app.prepare(ctx_id=self.device_id, det_size=(640, 640))

            logger.info("TemplatePreprocessor initialized successfully")

    def detect_and_classify_faces(self, image_path: str) -> Tuple[List[Dict], int, int]:
        """
        Detect faces and classify gender

        Args:
            image_path: Path to template image

        Returns:
            Tuple of (face_data_list, male_count, female_count)
            face_data contains: bbox, gender, landmarks, confidence
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise PreprocessingError(f"Failed to load image: {image_path}")

        face_data_list = []
        male_count = 0
        female_count = 0

        if self.app is None:
            # Mock data for testing when InsightFace is not available
            logger.warning("Using mock face detection")
            return face_data_list, male_count, female_count

        try:
            # Detect faces
            faces = self.app.get(img)
            logger.info(f"Detected {len(faces)} face(s) in {image_path}")

            for idx, face in enumerate(faces):
                # Extract face data
                bbox = face.bbox.astype(int).tolist()  # [x1, y1, x2, y2]

                # Gender classification using InsightFace
                # face.sex: 0 = female, 1 = male
                # face.gender can also be used if available
                gender = "unknown"
                if hasattr(face, 'sex'):
                    if face.sex == 0:
                        gender = "female"
                        female_count += 1
                    elif face.sex == 1:
                        gender = "male"
                        male_count += 1
                elif hasattr(face, 'gender'):
                    # Fallback to gender attribute if sex not available
                    if face.gender == 0:
                        gender = "female"
                        female_count += 1
                    elif face.gender == 1:
                        gender = "male"
                        male_count += 1

                # Extract landmarks if available
                landmarks = None
                if hasattr(face, 'landmark'):
                    landmarks = face.landmark.tolist()

                # Confidence score
                confidence = float(face.det_score) if hasattr(face, 'det_score') else 0.0

                face_data = {
                    "index": idx,
                    "bbox": bbox,
                    "gender": gender,
                    "landmarks": landmarks,
                    "confidence": confidence
                }

                face_data_list.append(face_data)

                logger.info(
                    f"Face {idx}: gender={gender}, "
                    f"bbox={bbox}, confidence={confidence:.3f}"
                )

            return face_data_list, male_count, female_count

        except Exception as e:
            logger.error(f"Face detection failed: {str(e)}")
            raise PreprocessingError(f"Face detection failed: {str(e)}")

    def create_masked_image(
        self,
        image_path: str,
        face_data_list: List[Dict],
        mask_type: str = "black"
    ) -> np.ndarray:
        """
        Create a masked version of the template with faces removed

        Args:
            image_path: Path to template image
            face_data_list: List of face data with bbox information
            mask_type: Type of masking ("black" or "blur")

        Returns:
            Masked image as numpy array
        """
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise PreprocessingError(f"Failed to load image: {image_path}")

        masked = img.copy()

        # Mask each face
        for face_data in face_data_list:
            bbox = face_data["bbox"]
            x1, y1, x2, y2 = bbox

            # Ensure coordinates are within image bounds
            h, w = masked.shape[:2]
            x1 = max(0, min(x1, w))
            x2 = max(0, min(x2, w))
            y1 = max(0, min(y1, h))
            y2 = max(0, min(y2, h))

            if mask_type == "black":
                # Simple black fill (fast, MVP approach)
                masked[y1:y2, x1:x2] = 0
                logger.debug(f"Masked face with black fill at [{x1}, {y1}, {x2}, {y2}]")

            elif mask_type == "blur":
                # Gaussian blur (alternative approach)
                face_region = masked[y1:y2, x1:x2]
                blurred = cv2.GaussianBlur(face_region, (99, 99), 30)
                masked[y1:y2, x1:x2] = blurred
                logger.debug(f"Masked face with blur at [{x1}, {y1}, {x2}, {y2}]")

            else:
                logger.warning(f"Unknown mask type: {mask_type}, using black")
                masked[y1:y2, x1:x2] = 0

        logger.info(f"Created masked image with {len(face_data_list)} faces masked")
        return masked

    def preprocess_template(
        self,
        template_id: int,
        db: Session,
        mask_type: str = "black"
    ) -> Dict:
        """
        Preprocess a template: detect faces, classify gender, create masked image

        Args:
            template_id: Template ID
            db: Database session
            mask_type: Type of face masking

        Returns:
            Preprocessing results dictionary
        """
        logger.info(f"Starting preprocessing for template {template_id}")

        # Get template
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Get original image
        original_image = db.query(Image).filter(
            Image.id == template.original_image_id
        ).first()

        if not original_image:
            raise ValueError(f"Original image for template {template_id} not found")

        # Get image path
        image_path = storage_service.get_file_path(original_image.storage_path)

        try:
            # Step 1: Detect faces and classify gender
            face_data_list, male_count, female_count = self.detect_and_classify_faces(
                str(image_path)
            )

            faces_detected = len(face_data_list)
            logger.info(
                f"Template {template_id}: detected {faces_detected} faces "
                f"({male_count} male, {female_count} female)"
            )

            # Step 2: Create masked image (if faces detected)
            masked_image_id = None
            if faces_detected > 0:
                masked_img = self.create_masked_image(
                    str(image_path),
                    face_data_list,
                    mask_type=mask_type
                )

                # Save masked image
                masked_filename = f"masked_{original_image.filename}"
                masked_storage_path, _ = storage_service.save_image(
                    masked_img,
                    masked_filename,
                    category="preprocessed"
                )

                # Create database record for masked image
                masked_image = Image(
                    filename=masked_filename,
                    storage_path=masked_storage_path,
                    file_size=os.path.getsize(
                        storage_service.get_file_path(masked_storage_path)
                    ),
                    width=masked_img.shape[1],
                    height=masked_img.shape[0],
                    image_type="preprocessed",
                    storage_type="permanent",
                    category="preprocessed",
                    uploaded_at=datetime.utcnow()
                )

                db.add(masked_image)
                db.flush()
                masked_image_id = masked_image.id

                logger.info(f"Saved masked image: id={masked_image_id}")

            # Step 3: Create or update preprocessing record
            preprocessing = db.query(TemplatePreprocessing).filter(
                TemplatePreprocessing.template_id == template_id
            ).first()

            if preprocessing:
                # Update existing record
                preprocessing.faces_detected = faces_detected
                preprocessing.face_data = face_data_list
                preprocessing.masked_image_id = masked_image_id
                preprocessing.preprocessing_status = "completed"
                preprocessing.error_message = None
                preprocessing.processed_at = datetime.utcnow()
            else:
                # Create new record
                preprocessing = TemplatePreprocessing(
                    template_id=template_id,
                    original_image_id=template.original_image_id,
                    faces_detected=faces_detected,
                    face_data=face_data_list,
                    masked_image_id=masked_image_id,
                    preprocessing_status="completed",
                    processed_at=datetime.utcnow()
                )
                db.add(preprocessing)

            # Step 4: Update template with face counts
            template.face_count = faces_detected
            template.male_face_count = male_count
            template.female_face_count = female_count
            template.is_preprocessed = True
            template.updated_at = datetime.utcnow()

            # Commit all changes
            db.commit()
            db.refresh(preprocessing)

            logger.info(f"Preprocessing completed for template {template_id}")

            return {
                "template_id": template_id,
                "faces_detected": faces_detected,
                "male_count": male_count,
                "female_count": female_count,
                "masked_image_id": masked_image_id,
                "preprocessing_status": "completed",
                "processed_at": preprocessing.processed_at
            }

        except Exception as e:
            logger.error(f"Preprocessing failed for template {template_id}: {str(e)}")

            # Record error in preprocessing table
            preprocessing = db.query(TemplatePreprocessing).filter(
                TemplatePreprocessing.template_id == template_id
            ).first()

            if preprocessing:
                preprocessing.preprocessing_status = "failed"
                preprocessing.error_message = str(e)
            else:
                preprocessing = TemplatePreprocessing(
                    template_id=template_id,
                    original_image_id=template.original_image_id,
                    faces_detected=0,
                    face_data=[],
                    preprocessing_status="failed",
                    error_message=str(e)
                )
                db.add(preprocessing)

            db.commit()

            raise PreprocessingError(f"Preprocessing failed: {str(e)}")


# Global preprocessor instance
_preprocessor = None


def get_preprocessor() -> TemplatePreprocessor:
    """Get global preprocessor instance"""
    global _preprocessor
    if _preprocessor is None:
        use_gpu = getattr(settings, 'USE_GPU', False)
        _preprocessor = TemplatePreprocessor(use_gpu=use_gpu)
    return _preprocessor
