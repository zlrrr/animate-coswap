"""
Core face-swapping service using InsightFace

This module provides the main FaceSwapper class that handles:
- Face detection using InsightFace
- Face embedding extraction
- Face swapping using the inswapper model
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple
import logging
import os

# InsightFace will be imported when available
try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    logging.warning("InsightFace not available. Face-swap functionality will be limited.")

logger = logging.getLogger(__name__)


class FaceSwapError(Exception):
    """Base exception for face-swap errors"""
    pass


class FaceDetectionError(FaceSwapError):
    """Raised when face detection fails"""
    pass


class FaceSwapper:
    """
    Core face-swapping service using InsightFace

    This class provides methods for:
    - Detecting faces in images
    - Swapping individual faces
    - Swapping couple faces (both husband and wife)

    Example:
        >>> swapper = FaceSwapper(model_path="models/inswapper_128.onnx")
        >>> result = swapper.swap_couple_faces(
        ...     husband_img="photos/john.jpg",
        ...     wife_img="photos/jane.jpg",
        ...     template_img="templates/couple.jpg"
        ... )
    """

    def __init__(self, model_path: str, use_gpu: bool = True, device_id: int = 0):
        """
        Initialize face swapper with model

        Args:
            model_path: Path to inswapper model (e.g., 'models/inswapper_128.onnx')
            use_gpu: Whether to use GPU acceleration
            device_id: GPU device ID (0 for first GPU)

        Raises:
            FileNotFoundError: If model file doesn't exist
            ImportError: If InsightFace is not installed
        """
        if not INSIGHTFACE_AVAILABLE:
            raise ImportError(
                "InsightFace is not installed. Please install it with: "
                "pip install insightface onnxruntime-gpu"
            )

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self.model_path = model_path
        self.use_gpu = use_gpu
        self.device_id = device_id if use_gpu else -1

        # Initialize face analysis app
        logger.info(f"Initializing FaceAnalysis with device_id={self.device_id}")
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=self.device_id, det_size=(640, 640))

        # Load face swapper model
        logger.info(f"Loading face swapper model from {model_path}")
        self.swapper = insightface.model_zoo.get_model(model_path, download=False)

        logger.info("FaceSwapper initialized successfully")

    def detect_faces(self, image_path: str) -> List:
        """
        Detect all faces in an image

        Args:
            image_path: Path to the image file

        Returns:
            List of Face objects with bounding boxes and embeddings

        Raises:
            FileNotFoundError: If image file doesn't exist
            FaceDetectionError: If face detection fails
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        try:
            img = cv2.imread(image_path)
            if img is None:
                raise FaceDetectionError(f"Failed to load image: {image_path}")

            faces = self.app.get(img)

            logger.info(f"Detected {len(faces)} face(s) in {image_path}")
            return faces

        except Exception as e:
            logger.error(f"Face detection failed: {str(e)}")
            raise FaceDetectionError(f"Face detection failed: {str(e)}")

    def swap_faces(
        self,
        source_img: str,
        target_img: str,
        source_face_index: int = 0,
        target_face_index: int = 0
    ) -> np.ndarray:
        """
        Swap face from source image to target image

        Args:
            source_img: Path to source image (husband/wife photo)
            target_img: Path to target template image
            source_face_index: Which face to use from source (default 0)
            target_face_index: Which face to replace in target (default 0)

        Returns:
            Result image as numpy array (BGR format)

        Raises:
            FaceDetectionError: If no face detected in either image
            ValueError: If face index is out of range
        """
        logger.info(
            f"Starting face swap: {source_img} -> {target_img} "
            f"(source_idx={source_face_index}, target_idx={target_face_index})"
        )

        # Load images
        source = cv2.imread(source_img)
        target = cv2.imread(target_img)

        if source is None:
            raise FileNotFoundError(f"Failed to load source image: {source_img}")
        if target is None:
            raise FileNotFoundError(f"Failed to load target image: {target_img}")

        # Detect faces
        source_faces = self.app.get(source)
        target_faces = self.app.get(target)

        if len(source_faces) == 0:
            raise FaceDetectionError(f"No face detected in source image: {source_img}")
        if len(target_faces) == 0:
            raise FaceDetectionError(f"No face detected in target image: {target_img}")

        # Validate face indices
        if source_face_index >= len(source_faces):
            raise ValueError(
                f"Source face index {source_face_index} out of range "
                f"(detected {len(source_faces)} faces)"
            )
        if target_face_index >= len(target_faces):
            raise ValueError(
                f"Target face index {target_face_index} out of range "
                f"(detected {len(target_faces)} faces)"
            )

        # Get specific faces
        source_face = source_faces[source_face_index]
        target_face = target_faces[target_face_index]

        logger.info(
            f"Swapping faces: source confidence={source_face.det_score:.3f}, "
            f"target confidence={target_face.det_score:.3f}"
        )

        # Perform face swap
        result = self.swapper.get(target, target_face, source_face, paste_back=True)

        logger.info("Face swap completed successfully")
        return result

    def swap_couple_faces(
        self,
        husband_img: str,
        wife_img: str,
        template_img: str
    ) -> np.ndarray:
        """
        Swap both husband and wife faces into a couple template

        This function performs sequential face swaps:
        1. Detect all faces in the template image
        2. Sort faces by position (left-to-right)
        3. Swap husband's face onto the left person
        4. Swap wife's face onto the right person

        Args:
            husband_img: Path to husband's photo (should contain single face)
            wife_img: Path to wife's photo (should contain single face)
            template_img: Path to couple template (must contain 2+ faces)

        Returns:
            Result image as numpy array (BGR format) with both faces swapped

        Raises:
            ValueError: If template has less than 2 faces
            FaceDetectionError: If no face found in source images

        Example:
            >>> result = swapper.swap_couple_faces(
            ...     "photos/john.jpg",
            ...     "photos/jane.jpg",
            ...     "templates/movie_couple.jpg"
            ... )
            >>> cv2.imwrite("result.jpg", result)
        """
        logger.info(
            f"Starting couple face swap: "
            f"husband={husband_img}, wife={wife_img}, template={template_img}"
        )

        # Detect faces in template
        template = cv2.imread(template_img)
        if template is None:
            raise FileNotFoundError(f"Failed to load template image: {template_img}")

        template_faces = self.app.get(template)

        if len(template_faces) < 2:
            raise ValueError(
                f"Template must contain at least 2 faces, but only {len(template_faces)} detected"
            )

        logger.info(f"Detected {len(template_faces)} faces in template")

        # Sort faces left-to-right (assume male on left, female on right)
        # This is a common convention in couple photos
        template_faces.sort(key=lambda f: f.bbox[0])

        logger.info("Step 1/2: Swapping husband's face (left position)")
        # Swap husband face (left person)
        result = self.swap_faces(husband_img, template_img, 0, 0)

        # Save intermediate result
        temp_path = "/tmp/intermediate_swap.jpg"
        cv2.imwrite(temp_path, result)

        logger.info("Step 2/2: Swapping wife's face (right position)")
        # Swap wife face (right person) on the intermediate result
        result = self.swap_faces(wife_img, temp_path, 0, 1)

        # Clean up temporary file
        try:
            os.remove(temp_path)
        except:
            pass

        logger.info("Couple face swap completed successfully")
        return result

    def get_face_info(self, image_path: str) -> dict:
        """
        Get detailed information about faces in an image

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary containing face count and detailed face information
        """
        faces = self.detect_faces(image_path)

        face_info = {
            "face_count": len(faces),
            "faces": []
        }

        for i, face in enumerate(faces):
            info = {
                "index": i,
                "bbox": face.bbox.tolist(),
                "confidence": float(face.det_score),
                "landmark": face.landmark_2d_106.tolist() if hasattr(face, 'landmark_2d_106') else None,
                "age": int(face.age) if hasattr(face, 'age') else None,
                "gender": int(face.gender) if hasattr(face, 'gender') else None,
            }
            face_info["faces"].append(info)

        return face_info
