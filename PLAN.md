# Couple Face-Swap Website Project
AI-powered couple image collection and face-swapping service

**Project Goal:**  
Build a web-based platform that collects couple images from various sources (ACG, movies, TV shows), stores them with metadata, and performs high-quality face-swapping using advanced AI algorithms.

---

## Phase 0 — MVP Planning & Core Algorithm Validation

**MVP Development Philosophy:**  
Build a functional Minimum Viable Product (MVP) first to validate the core face-swap technology, then iteratively expand features. The MVP will focus on manual image upload, basic face-swapping, and local execution.

**Core Critical Path:**  
Phase 0 → Phase 1 (MVP Core) → Phase 2 (MVP Web Interface) → Testing & Validation → Phase 3+ (Feature Expansion)

---

## Technology Stack Selection

### Backend
- **Language**: Python 3.10+ (recommended for AI/ML libraries)
- **Web Framework**: FastAPI (high performance, async support, auto API docs)
- **Database**: PostgreSQL + SQLAlchemy (structured data)
- **Task Queue**: Celery + Redis (background processing)
- **Storage**: MinIO or S3-compatible storage (image files)

### Face-Swap Algorithm (CRITICAL COMPONENT)
**Primary Options (in priority order):**

1. **InsightFace + inswapper** ⭐ RECOMMENDED
   - Library: `insightface`, `onnxruntime`
   - Model: inswapper_128.onnx
   - Pros: Fast, high quality, production-ready
   - Repo: https://github.com/deepinsight/insightface

2. **SimSwap**
   - Research paper implementation
   - Pros: High quality, good for videos
   - Cons: More complex setup
   - Repo: https://github.com/neuralchen/SimSwap

3. **DeepFaceLab** (Fallback)
   - Comprehensive but heavy
   - Best for high-quality results, slower
   - Repo: https://github.com/iperov/DeepFaceLab

**MVP Decision: Use InsightFace + inswapper for speed and quality balance**

### Frontend
- **Framework**: React 18+ with TypeScript
- **UI Library**: Material-UI (MUI) or Ant Design
- **State Management**: React Query + Context API
- **Build Tool**: Vite

### DevOps
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana (Phase 3+)

---

## Phase Breakdown with MVP-First Approach

### Phase 0 — Environment Setup & Algorithm Validation ⭐ CRITICAL

**Duration:** 2-3 days

**Objective:**
- Set up development environment
- Validate face-swap algorithm with real test cases
- Establish project structure and documentation

**Deliverables:**

1. **Project Structure**
   ```
   couple-faceswap/
   ├── backend/
   │   ├── app/
   │   │   ├── core/           # Config, dependencies
   │   │   ├── models/         # Database models
   │   │   ├── api/            # API endpoints
   │   │   ├── services/       # Business logic
   │   │   │   ├── faceswap/  # Face-swap core ⭐
   │   │   │   ├── catcher/   # Image collection (Phase 3+)
   │   │   │   └── browser/   # Image management
   │   │   └── utils/          # Helpers
   │   ├── tests/              # Unit & integration tests
   │   ├── requirements.txt
   │   └── Dockerfile
   ├── frontend/
   │   ├── src/
   │   │   ├── components/
   │   │   ├── pages/
   │   │   ├── services/       # API clients
   │   │   └── utils/
   │   ├── package.json
   │   └── Dockerfile
   ├── docs/
   │   ├── phase-0/
   │   │   ├── environment-setup.md
   │   │   ├── algorithm-validation.md
   │   │   ├── tech-stack-rationale.md
   │   │   └── database-schema.md
   │   └── api/
   ├── scripts/                 # Setup and utility scripts
   ├── tests/                   # E2E tests
   ├── docker-compose.yml
   └── README.md
   ```

2. **Face-Swap Algorithm Validation**
   - Download and test InsightFace models
   - Create validation script with 10+ test image pairs
   - Document quality metrics (SSIM, FID, visual inspection)
   - Performance benchmarks (inference time, GPU memory)

3. **Database Schema Design**
   ```sql
   -- Core MVP tables
   
   CREATE TABLE users (
       id SERIAL PRIMARY KEY,
       email VARCHAR(255) UNIQUE NOT NULL,
       username VARCHAR(100) UNIQUE NOT NULL,
       password_hash VARCHAR(255) NOT NULL,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE TABLE images (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES users(id),
       filename VARCHAR(255) NOT NULL,
       storage_path VARCHAR(500) NOT NULL,
       file_size INTEGER,
       width INTEGER,
       height INTEGER,
       image_type VARCHAR(20), -- 'source', 'template', 'result'
       category VARCHAR(50),   -- 'acg', 'movie', 'tv', 'custom'
       tags TEXT[],            -- Array of tags
       uploaded_at TIMESTAMP DEFAULT NOW(),
       metadata JSONB          -- Flexible metadata storage
   );
   
   CREATE TABLE templates (
       id SERIAL PRIMARY KEY,
       image_id INTEGER REFERENCES images(id),
       title VARCHAR(255) NOT NULL,
       description TEXT,
       artist VARCHAR(255),
       source_url VARCHAR(500),
       face_count INTEGER DEFAULT 2,
       face_positions JSONB,   -- Detected face bounding boxes
       popularity_score INTEGER DEFAULT 0,
       is_active BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE TABLE faceswap_tasks (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES users(id),
       template_id INTEGER REFERENCES templates(id),
       husband_image_id INTEGER REFERENCES images(id),
       wife_image_id INTEGER REFERENCES images(id),
       result_image_id INTEGER REFERENCES images(id),
       status VARCHAR(20),     -- 'pending', 'processing', 'completed', 'failed'
       progress INTEGER DEFAULT 0,
       error_message TEXT,
       processing_time FLOAT,
       started_at TIMESTAMP,
       completed_at TIMESTAMP,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   -- Phase 3+ tables (deferred)
   
   CREATE TABLE crawl_tasks (
       id SERIAL PRIMARY KEY,
       source_type VARCHAR(50), -- 'pixiv', 'danbooru', 'custom'
       search_query TEXT,
       filters JSONB,
       status VARCHAR(20),
       images_collected INTEGER DEFAULT 0,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_images_user ON images(user_id);
   CREATE INDEX idx_images_type ON images(image_type);
   CREATE INDEX idx_templates_category ON templates(category);
   CREATE INDEX idx_tasks_status ON faceswap_tasks(status);
   CREATE INDEX idx_tasks_user ON faceswap_tasks(user_id);
   ```

4. **Test Cases for Algorithm Validation**
   - Test Case 1: High-quality portrait photos (frontal face)
   - Test Case 2: Side-angle faces
   - Test Case 3: Multiple faces in single image
   - Test Case 4: Low-resolution images
   - Test Case 5: Anime/ACG style faces
   - Test Case 6: Occluded faces (glasses, masks)
   - Test Case 7: Different lighting conditions
   - Test Case 8: Age/gender variations
   - Test Case 9: Extreme facial expressions
   - Test Case 10: Group photos with multiple couples

**Acceptance Criteria:**
- [ ] Development environment (Python 3.10+, Node.js 18+) set up
- [ ] InsightFace models downloaded and loaded successfully
- [ ] Face-swap algorithm produces acceptable results on 8/10 test cases
- [ ] Average processing time < 5 seconds per image pair (with GPU)
- [ ] Database schema designed and documented
- [ ] Project structure created with README
- [ ] All validation tests pass with visual quality score >= 4/5

**Checkpoint 0.1 - Algorithm Validation Complete**
```bash
# Commit after successful algorithm validation
git add .
git commit -m "Phase 0.1: Face-swap algorithm validated with InsightFace"
git tag checkpoint-0.1
```

**Test Script Example:**
```python
# tests/test_faceswap_core.py
import pytest
from app.services.faceswap.core import FaceSwapper

class TestFaceSwapCore:
    @pytest.fixture
    def swapper(self):
        return FaceSwapper(model_path="models/inswapper_128.onnx")
    
    def test_single_face_swap_frontal(self, swapper):
        """Test face swap with frontal portrait"""
        result = swapper.swap_faces(
            source_img="tests/fixtures/husband_front.jpg",
            target_img="tests/fixtures/template_couple_1.jpg",
            face_index=0
        )
        assert result is not None
        assert result.shape[0] > 0
        # Visual quality check (manual for now)
        
    def test_multiple_faces_detection(self, swapper):
        """Test detection of multiple faces in template"""
        faces = swapper.detect_faces("tests/fixtures/template_couple_1.jpg")
        assert len(faces) == 2
        assert all(f.confidence > 0.95 for f in faces)
    
    def test_anime_face_swap(self, swapper):
        """Test face swap with anime/ACG template"""
        result = swapper.swap_faces(
            source_img="tests/fixtures/husband_front.jpg",
            target_img="tests/fixtures/acg_couple_1.png",
            face_index=0
        )
        assert result is not None
        # Anime faces may have lower confidence, adjust threshold
        
    def test_processing_time_performance(self, swapper, benchmark):
        """Test processing time is acceptable"""
        def swap():
            swapper.swap_faces(
                "tests/fixtures/husband_front.jpg",
                "tests/fixtures/template_couple_1.jpg",
                0
            )
        result = benchmark(swap)
        assert result.stats.mean < 5.0  # Less than 5 seconds
```

---

### Phase 1 — MVP Backend Core (Processor Service Only) ⭐ MVP

**Duration:** 4-5 days

**Objective:**
- Implement core face-swap processing service
- Create basic image upload and storage
- Build REST API for face-swap operations
- No crawler/browser features yet (manual upload only)

**Deliverables:**

1. **Face-Swap Service Implementation**
   ```python
   # app/services/faceswap/core.py
   import cv2
   import numpy as np
   import insightface
   from insightface.app import FaceAnalysis
   
   class FaceSwapper:
       """Core face-swapping service using InsightFace"""
       
       def __init__(self, model_path: str):
           """
           Initialize face swapper with model
           
           Args:
               model_path: Path to inswapper model (e.g., 'models/inswapper_128.onnx')
           """
           self.app = FaceAnalysis(name='buffalo_l')
           self.app.prepare(ctx_id=0, det_size=(640, 640))
           self.swapper = insightface.model_zoo.get_model(model_path)
           
       def detect_faces(self, image_path: str):
           """
           Detect all faces in an image
           
           Returns:
               List of Face objects with bounding boxes and embeddings
           """
           img = cv2.imread(image_path)
           faces = self.app.get(img)
           return faces
       
       def swap_faces(
           self, 
           source_img: str, 
           target_img: str, 
           source_face_index: int = 0,
           target_face_index: int = 0
       ):
           """
           Swap face from source image to target image
           
           Args:
               source_img: Path to source image (husband/wife photo)
               target_img: Path to target template image
               source_face_index: Which face to use from source (default 0)
               target_face_index: Which face to replace in target (default 0)
               
           Returns:
               Result image as numpy array
           """
           # Load images
           source = cv2.imread(source_img)
           target = cv2.imread(target_img)
           
           # Detect faces
           source_faces = self.app.get(source)
           target_faces = self.app.get(target)
           
           if len(source_faces) == 0:
               raise ValueError("No face detected in source image")
           if len(target_faces) == 0:
               raise ValueError("No face detected in target image")
               
           # Get specific faces
           source_face = source_faces[source_face_index]
           target_face = target_faces[target_face_index]
           
           # Perform face swap
           result = self.swapper.get(target, target_face, source_face, paste_back=True)
           
           return result
       
       def swap_couple_faces(
           self,
           husband_img: str,
           wife_img: str,
           template_img: str
       ):
           """
           Swap both husband and wife faces into a couple template
           
           Args:
               husband_img: Path to husband's photo
               wife_img: Path to wife's photo
               template_img: Path to couple template image
               
           Returns:
               Result image with both faces swapped
           """
           # Detect faces in template
           template = cv2.imread(template_img)
           template_faces = self.app.get(template)
           
           if len(template_faces) < 2:
               raise ValueError("Template must contain at least 2 faces")
           
           # Sort faces left-to-right (assume male on left, female on right)
           template_faces.sort(key=lambda f: f.bbox[0])
           
           # Swap husband face (left person)
           result = self.swap_faces(husband_img, template_img, 0, 0)
           
           # Save intermediate result
           temp_path = "/tmp/intermediate_swap.jpg"
           cv2.imwrite(temp_path, result)
           
           # Swap wife face (right person) on the intermediate result
           result = self.swap_faces(wife_img, temp_path, 0, 1)
           
           return result
   ```

2. **API Endpoints**
   ```python
   # app/api/v1/faceswap.py
   from fastapi import APIRouter, UploadFile, File, BackgroundTasks
   from app.services.faceswap.processor import FaceSwapProcessor
   from app.models.schemas import FaceSwapRequest, FaceSwapResponse
   
   router = APIRouter()
   
   @router.post("/upload-image")
   async def upload_image(
       file: UploadFile = File(...),
       image_type: str = "source"
   ):
       """
       Upload an image (source photo or template)
       
       Returns: image_id and storage path
       """
       # Save file to storage
       # Create database record
       # Return image metadata
       pass
   
   @router.post("/swap-faces")
   async def swap_faces(
       request: FaceSwapRequest,
       background_tasks: BackgroundTasks
   ):
       """
       Start a face-swap task
       
       Request body:
       {
           "husband_image_id": 123,
           "wife_image_id": 124,
           "template_id": 456
       }
       
       Returns: task_id for status tracking
       """
       # Create task record
       # Queue background processing
       # Return task_id immediately
       pass
   
   @router.get("/task/{task_id}")
   async def get_task_status(task_id: int):
       """
       Get face-swap task status and result
       
       Returns:
       {
           "task_id": 789,
           "status": "completed",
           "progress": 100,
           "result_image_url": "https://...",
           "processing_time": 3.45
       }
       """
       pass
   
   @router.get("/templates")
   async def list_templates(
       category: str = None,
       limit: int = 20,
       offset: int = 0
   ):
       """
       List available templates
       
       Query params:
       - category: 'acg', 'movie', 'tv', 'all'
       - limit: Number of results
       - offset: Pagination offset
       """
       pass
   ```

3. **Background Task Processing**
   ```python
   # app/services/faceswap/processor.py
   from celery import Celery
   from app.services.faceswap.core import FaceSwapper
   from app.models.database import FaceSwapTask, Image
   
   celery_app = Celery('faceswap', broker='redis://localhost:6379')
   
   @celery_app.task
   def process_faceswap_task(task_id: int):
       """
       Background task to process face-swap
       
       Args:
           task_id: ID of FaceSwapTask record
       """
       # Load task from database
       task = FaceSwapTask.get(id=task_id)
       task.status = 'processing'
       task.save()
       
       try:
           # Load images
           husband_img = task.husband_image.storage_path
           wife_img = task.wife_image.storage_path
           template_img = task.template.image.storage_path
           
           # Initialize swapper
           swapper = FaceSwapper(model_path='models/inswapper_128.onnx')
           
           # Perform face swap
           result = swapper.swap_couple_faces(
               husband_img=husband_img,
               wife_img=wife_img,
               template_img=template_img
           )
           
           # Save result
           result_path = f"results/{task_id}_result.jpg"
           cv2.imwrite(result_path, result)
           
           # Create result image record
           result_image = Image.create(
               storage_path=result_path,
               image_type='result',
               user_id=task.user_id
           )
           
           # Update task
           task.status = 'completed'
           task.result_image_id = result_image.id
           task.completed_at = datetime.now()
           task.save()
           
       except Exception as e:
           task.status = 'failed'
           task.error_message = str(e)
           task.save()
           raise
   ```

4. **Unit Tests for MVP**
   ```python
   # tests/test_api_faceswap.py
   import pytest
   from fastapi.testclient import TestClient
   from app.main import app
   
   client = TestClient(app)
   
   class TestFaceSwapAPI:
       def test_upload_image_success(self):
           """Test image upload endpoint"""
           with open("tests/fixtures/husband_front.jpg", "rb") as f:
               response = client.post(
                   "/api/v1/faceswap/upload-image",
                   files={"file": f},
                   data={"image_type": "source"}
               )
           assert response.status_code == 200
           data = response.json()
           assert "image_id" in data
           assert "storage_path" in data
       
       def test_swap_faces_creates_task(self):
           """Test face-swap task creation"""
           response = client.post(
               "/api/v1/faceswap/swap-faces",
               json={
                   "husband_image_id": 1,
                   "wife_image_id": 2,
                   "template_id": 3
               }
           )
           assert response.status_code == 202
           data = response.json()
           assert "task_id" in data
       
       def test_get_task_status(self):
           """Test task status retrieval"""
           response = client.get("/api/v1/faceswap/task/1")
           assert response.status_code == 200
           data = response.json()
           assert data["status"] in ["pending", "processing", "completed", "failed"]
       
       def test_list_templates(self):
           """Test template listing"""
           response = client.get("/api/v1/faceswap/templates?category=acg&limit=10")
           assert response.status_code == 200
           data = response.json()
           assert isinstance(data, list)
           assert len(data) <= 10
   ```

**Acceptance Criteria:**
- [ ] Face-swap service processes images successfully
- [ ] API endpoints return correct responses (201, 200, 404, etc.)
- [ ] Background tasks execute without blocking main thread
- [ ] Database records created for all entities
- [ ] All unit tests pass (coverage >= 80%)
- [ ] API documentation auto-generated (FastAPI /docs)
- [ ] Processing time < 10 seconds for standard image pairs
- [ ] Error handling for invalid images/missing faces

**Checkpoint 1.1 - Backend Core Complete**
```bash
# Commit after all backend tests pass
git add backend/
git commit -m "Phase 1.1: MVP backend core - face-swap processor service"
git tag checkpoint-1.1
```

**Checkpoint 1.2 - API Integration Tests**
```bash
# Commit after integration tests pass
git add tests/integration/
git commit -m "Phase 1.2: Integration tests for face-swap API"
git tag checkpoint-1.2
```

---

### Phase 2 — MVP Frontend & Web Interface ⭐ MVP

**Duration:** 3-4 days

**Objective:**
- Create simple web interface for uploading images
- Display templates and results
- Show real-time task progress
- Complete MVP for initial testing

**Deliverables:**

1. **Core Pages**
   - Landing page with feature overview
   - Upload page (husband/wife photos)
   - Template selection gallery
   - Processing status page
   - Results gallery

2. **React Components**
   ```typescript
   // src/components/ImageUploader.tsx
   import React, { useState } from 'react';
   import { Upload, Button, message } from 'antd';
   import { UploadOutlined } from '@ant-design/icons';
   
   interface ImageUploaderProps {
       onUploadComplete: (imageId: number) => void;
       imageType: 'husband' | 'wife' | 'template';
   }
   
   export const ImageUploader: React.FC<ImageUploaderProps> = ({
       onUploadComplete,
       imageType
   }) => {
       const [uploading, setUploading] = useState(false);
       
       const handleUpload = async (file: File) => {
           setUploading(true);
           const formData = new FormData();
           formData.append('file', file);
           formData.append('image_type', 'source');
           
           try {
               const response = await fetch('/api/v1/faceswap/upload-image', {
                   method: 'POST',
                   body: formData
               });
               
               const data = await response.json();
               message.success('Image uploaded successfully!');
               onUploadComplete(data.image_id);
           } catch (error) {
               message.error('Upload failed!');
           } finally {
               setUploading(false);
           }
       };
       
       return (
           <Upload
               beforeUpload={(file) => {
                   handleUpload(file);
                   return false; // Prevent auto upload
               }}
               accept="image/*"
           >
               <Button icon={<UploadOutlined />} loading={uploading}>
                   Upload {imageType} Photo
               </Button>
           </Upload>
       );
   };
   ```

   ```typescript
   // src/components/TemplateGallery.tsx
   import React, { useEffect, useState } from 'react';
   import { Card, Row, Col, Spin, Tag } from 'antd';
   
   interface Template {
       id: number;
       title: string;
       image_url: string;
       category: string;
       face_count: number;
   }
   
   export const TemplateGallery: React.FC = () => {
       const [templates, setTemplates] = useState<Template[]>([]);
       const [loading, setLoading] = useState(true);
       const [selectedCategory, setSelectedCategory] = useState<string>('all');
       
       useEffect(() => {
           fetchTemplates();
       }, [selectedCategory]);
       
       const fetchTemplates = async () => {
           setLoading(true);
           const response = await fetch(
               `/api/v1/faceswap/templates?category=${selectedCategory}&limit=20`
           );
           const data = await response.json();
           setTemplates(data);
           setLoading(false);
       };
       
       if (loading) return <Spin size="large" />;
       
       return (
           <div>
               <div style={{ marginBottom: 16 }}>
                   <Tag.CheckableTag
                       checked={selectedCategory === 'all'}
                       onChange={() => setSelectedCategory('all')}
                   >
                       All
                   </Tag.CheckableTag>
                   <Tag.CheckableTag
                       checked={selectedCategory === 'acg'}
                       onChange={() => setSelectedCategory('acg')}
                   >
                       ACG/Anime
                   </Tag.CheckableTag>
                   <Tag.CheckableTag
                       checked={selectedCategory === 'movie'}
                       onChange={() => setSelectedCategory('movie')}
                   >
                       Movies
                   </Tag.CheckableTag>
                   <Tag.CheckableTag
                       checked={selectedCategory === 'tv'}
                       onChange={() => setSelectedCategory('tv')}
                   >
                       TV Shows
                   </Tag.CheckableTag>
               </div>
               
               <Row gutter={[16, 16]}>
                   {templates.map((template) => (
                       <Col key={template.id} xs={24} sm={12} md={8} lg={6}>
                           <Card
                               hoverable
                               cover={
                                   <img
                                       alt={template.title}
                                       src={template.image_url}
                                       style={{ height: 200, objectFit: 'cover' }}
                                   />
                               }
                               onClick={() => {
                                   // Handle template selection
                               }}
                           >
                               <Card.Meta
                                   title={template.title}
                                   description={
                                       <Tag color="blue">{template.category}</Tag>
                                   }
                               />
                           </Card>
                       </Col>
                   ))}
               </Row>
           </div>
       );
   };
   ```

   ```typescript
   // src/pages/FaceSwapWorkflow.tsx
   import React, { useState } from 'react';
   import { Steps, Button, message } from 'antd';
   import { ImageUploader } from '../components/ImageUploader';
   import { TemplateGallery } from '../components/TemplateGallery';
   import { TaskProgress } from '../components/TaskProgress';
   
   const { Step } = Steps;
   
   export const FaceSwapWorkflow: React.FC = () => {
       const [currentStep, setCurrentStep] = useState(0);
       const [husbandImageId, setHusbandImageId] = useState<number | null>(null);
       const [wifeImageId, setWifeImageId] = useState<number | null>(null);
       const [templateId, setTemplateId] = useState<number | null>(null);
       const [taskId, setTaskId] = useState<number | null>(null);
       
       const startProcessing = async () => {
           if (!husbandImageId || !wifeImageId || !templateId) {
               message.error('Please complete all steps first!');
               return;
           }
           
           const response = await fetch('/api/v1/faceswap/swap-faces', {
               method: 'POST',
               headers: { 'Content-Type': 'application/json' },
               body: JSON.stringify({
                   husband_image_id: husbandImageId,
                   wife_image_id: wifeImageId,
                   template_id: templateId
               })
           });
           
           const data = await response.json();
           setTaskId(data.task_id);
           setCurrentStep(3);
       };
       
       return (
           <div style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>
               <Steps current={currentStep}>
                   <Step title="Upload Photos" description="Husband & Wife" />
                   <Step title="Select Template" description="Choose style" />
                   <Step title="Process" description="Face swap" />
                   <Step title="Result" description="Download" />
               </Steps>
               
               <div style={{ marginTop: 32 }}>
                   {currentStep === 0 && (
                       <div>
                           <h3>Upload Husband's Photo</h3>
                           <ImageUploader
                               imageType="husband"
                               onUploadComplete={setHusbandImageId}
                           />
                           
                           <h3 style={{ marginTop: 24 }}>Upload Wife's Photo</h3>
                           <ImageUploader
                               imageType="wife"
                               onUploadComplete={setWifeImageId}
                           />
                           
                           <Button
                               type="primary"
                               onClick={() => setCurrentStep(1)}
                               disabled={!husbandImageId || !wifeImageId}
                               style={{ marginTop: 24 }}
                           >
                               Next: Select Template
                           </Button>
                       </div>
                   )}
                   
                   {currentStep === 1 && (
                       <div>
                           <h3>Choose a Template</h3>
                           <TemplateGallery onSelect={setTemplateId} />
                           
                           <Button
                               type="primary"
                               onClick={() => setCurrentStep(2)}
                               disabled={!templateId}
                               style={{ marginTop: 24 }}
                           >
                               Next: Start Processing
                           </Button>
                       </div>
                   )}
                   
                   {currentStep === 2 && (
                       <div>
                           <h3>Ready to Process</h3>
                           <p>Click the button below to start face swapping</p>
                           <Button
                               type="primary"
                               size="large"
                               onClick={startProcessing}
                           >
                               Start Face Swap
                           </Button>
                       </div>
                   )}
                   
                   {currentStep === 3 && taskId && (
                       <TaskProgress taskId={taskId} />
                   )}
               </div>
           </div>
       );
   };
   ```

3. **Frontend Tests**
   ```typescript
   // src/components/__tests__/ImageUploader.test.tsx
   import { render, screen, fireEvent, waitFor } from '@testing-library/react';
   import { ImageUploader } from '../ImageUploader';
   
   describe('ImageUploader', () => {
       it('should upload image successfully', async () => {
           const mockOnComplete = jest.fn();
           
           render(
               <ImageUploader
                   imageType="husband"
                   onUploadComplete={mockOnComplete}
               />
           );
           
           const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
           const input = screen.getByRole('button');
           
           fireEvent.change(input, { target: { files: [file] } });
           
           await waitFor(() => {
               expect(mockOnComplete).toHaveBeenCalledWith(expect.any(Number));
           });
       });
       
       it('should handle upload error', async () => {
           // Mock failed API call
           global.fetch = jest.fn(() => Promise.reject('API error'));
           
           render(
               <ImageUploader
                   imageType="husband"
                   onUploadComplete={() => {}}
               />
           );
           
           const file = new File(['image'], 'test.jpg', { type: 'image/jpeg' });
           const input = screen.getByRole('button');
           
           fireEvent.change(input, { target: { files: [file] } });
           
           await waitFor(() => {
               expect(screen.getByText(/failed/i)).toBeInTheDocument();
           });
       });
   });
   ```

**Acceptance Criteria:**
- [ ] Users can upload husband/wife photos
- [ ] Template gallery displays with categories
- [ ] Face-swap task can be submitted
- [ ] Real-time progress updates work
- [ ] Results display correctly
- [ ] Responsive design (mobile, tablet, desktop)
- [ ] All frontend tests pass
- [ ] Basic error handling and user feedback

**Checkpoint 2.1 - Frontend Core Components**
```bash
git add frontend/src/components/
git commit -m "Phase 2.1: Core React components - uploader, gallery, workflow"
git tag checkpoint-2.1
```

**Checkpoint 2.2 - Frontend Integration**
```bash
git add frontend/
git commit -m "Phase 2.2: Complete MVP frontend with API integration"
git tag checkpoint-2.2
```

---

### MVP Validation & Testing Phase ⭐ CRITICAL

**Duration:** 2 days

**Objective:**
- End-to-end testing of complete MVP
- Performance benchmarking
- Bug fixes and optimization
- User acceptance testing

**Test Suite:**

1. **E2E Test Scenarios**
   ```python
   # tests/e2e/test_complete_workflow.py
   import pytest
   from playwright.sync_api import Page, expect
   
   class TestCompleteWorkflow:
       def test_full_faceswap_workflow(self, page: Page):
           """Test complete user workflow from upload to result"""
           # Navigate to homepage
           page.goto("http://localhost:3000")
           
           # Upload husband photo
           page.locator("input[type='file']").first.set_input_files(
               "tests/fixtures/husband_front.jpg"
           )
           expect(page.locator("text=Upload successful")).to_be_visible()
           
           # Upload wife photo
           page.locator("input[type='file']").nth(1).set_input_files(
               "tests/fixtures/wife_front.jpg"
           )
           
           # Click next to templates
           page.click("text=Next: Select Template")
           
           # Select a template
           page.click(".template-card").first
           
           # Start processing
           page.click("text=Start Face Swap")
           
           # Wait for completion (max 30 seconds)
           expect(page.locator("text=Completed")).to_be_visible(timeout=30000)
           
           # Verify result image is displayed
           expect(page.locator("img[alt='Result']")).to_be_visible()
           
       def test_error_handling_no_face(self, page: Page):
           """Test error handling when no face detected"""
           page.goto("http://localhost:3000")
           
           # Upload image without face
           page.locator("input[type='file']").first.set_input_files(
               "tests/fixtures/no_face_landscape.jpg"
           )
           
           # Should show error message
           expect(page.locator("text=No face detected")).to_be_visible()
   ```

2. **Performance Benchmarks**
   ```python
   # tests/performance/test_benchmarks.py
   import time
   import pytest
   from app.services.faceswap.core import FaceSwapper
   
   class TestPerformanceBenchmarks:
       @pytest.fixture
       def swapper(self):
           return FaceSwapper(model_path="models/inswapper_128.onnx")
       
       def test_processing_time_benchmarks(self, swapper):
           """Benchmark processing times for different scenarios"""
           test_cases = [
               ("High quality 4K", "tests/fixtures/hq_4k_couple.jpg"),
               ("Medium 1080p", "tests/fixtures/med_1080p_couple.jpg"),
               ("Low 720p", "tests/fixtures/low_720p_couple.jpg"),
               ("Anime/ACG", "tests/fixtures/acg_couple.png"),
           ]
           
           results = {}
           for name, template_path in test_cases:
               start = time.time()
               swapper.swap_couple_faces(
                   husband_img="tests/fixtures/husband_front.jpg",
                   wife_img="tests/fixtures/wife_front.jpg",
                   template_img=template_path
               )
               elapsed = time.time() - start
               results[name] = elapsed
               
               # Assert performance requirements
               assert elapsed < 10.0, f"{name} took too long: {elapsed}s"
           
           print("\nPerformance Benchmarks:")
           for name, elapsed in results.items():
               print(f"  {name}: {elapsed:.2f}s")
       
       def test_concurrent_processing(self, swapper):
           """Test handling multiple concurrent requests"""
           import concurrent.futures
           
           def process_single():
               return swapper.swap_couple_faces(
                   "tests/fixtures/husband_front.jpg",
                   "tests/fixtures/wife_front.jpg",
                   "tests/fixtures/template_1.jpg"
               )
           
           with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
               futures = [executor.submit(process_single) for _ in range(5)]
               results = [f.result() for f in futures]
               
           assert len(results) == 5
           assert all(r is not None for r in results)
   ```

3. **Quality Assurance Checklist**
   - [ ] Face detection accuracy >= 95% on test set
   - [ ] Face swap visual quality score >= 4/5 (manual review)
   - [ ] Processing time < 10s per image pair
   - [ ] API response time < 200ms (excluding processing)
   - [ ] Database queries optimized (< 50ms)
   - [ ] No memory leaks after 100 consecutive operations
   - [ ] Error messages are user-friendly
   - [ ] All edge cases handled (no face, multiple faces, etc.)

**Acceptance Criteria:**
- [ ] All E2E tests pass
- [ ] Performance benchmarks meet requirements
- [ ] No critical bugs found
- [ ] MVP ready for user testing
- [ ] Documentation complete

**Checkpoint MVP Complete**
```bash
git add .
git commit -m "MVP Complete: Full face-swap workflow tested and validated"
git tag mvp-v1.0
```

---

### Phase 3 — Catcher Service (Image Collection) 🔄 POST-MVP

**Duration:** 5-7 days

**Objective:**
- Implement web crawler for collecting couple images
- Support multiple sources (Pixiv, Danbooru, custom)
- Tag and categorize collected images
- Task configuration and management

**Deliverables:**

1. **Crawler Architecture**
   ```python
   # app/services/catcher/base_crawler.py
   from abc import ABC, abstractmethod
   from typing import List, Dict
   
   class BaseCrawler(ABC):
       """Base class for all image crawlers"""
       
       def __init__(self, config: Dict):
           self.config = config
           self.session = self._create_session()
       
       @abstractmethod
       async def search(self, query: str, limit: int) -> List[Dict]:
           """Search for images based on query"""
           pass
       
       @abstractmethod
       async def download_image(self, url: str, save_path: str):
           """Download single image"""
           pass
       
       def filter_couples(self, images: List[Dict]) -> List[Dict]:
           """Filter images to only include couples (2 people)"""
           # Use face detection to verify 2 faces present
           pass
   
   # app/services/catcher/pixiv_crawler.py
   class PixivCrawler(BaseCrawler):
       """Crawler for Pixiv artwork"""
       
       async def search(self, query: str, limit: int):
           """
           Search Pixiv for couple artwork
           
           Args:
               query: Search keywords (e.g., "カップル", "couple")
               limit: Max number of images to collect
           """
           # Implementation using Pixiv API
           pass
   
   # app/services/catcher/danbooru_crawler.py
   class DanbooruCrawler(BaseCrawler):
       """Crawler for Danbooru/Gelbooru style sites"""
       
       async def search(self, query: str, limit: int):
           # Implementation using Danbooru API
           # Tags: "2girls", "1girl 1boy", etc.
           pass
   ```

2. **Crawler Management API**
   ```python
   # app/api/v1/catcher.py
   @router.post("/crawl-tasks")
   async def create_crawl_task(request: CrawlTaskRequest):
       """
       Create a new image collection task
       
       Request body:
       {
           "source_type": "pixiv",
           "search_query": "couple illustration",
           "category": "acg",
           "filters": {
               "min_faces": 2,
               "max_faces": 2,
               "min_resolution": [800, 600]
           },
           "limit": 100
       }
       """
       pass
   
   @router.get("/crawl-tasks/{task_id}")
   async def get_crawl_task_status(task_id: int):
       """Get crawl task progress and statistics"""
       pass
   
   @router.post("/crawl-tasks/{task_id}/pause")
   async def pause_crawl_task(task_id: int):
       """Pause a running crawl task"""
       pass
   
   @router.post("/crawl-tasks/{task_id}/resume")
   async def resume_crawl_task(task_id: int):
       """Resume a paused crawl task"""
       pass
   ```

3. **Tests for Catcher Service**
   ```python
   # tests/test_catcher_service.py
   class TestCatcherService:
       def test_pixiv_search_returns_results(self):
           """Test Pixiv crawler returns valid results"""
           crawler = PixivCrawler(config={})
           results = crawler.search("カップル", limit=10)
           assert len(results) > 0
           assert all('url' in r for r in results)
       
       def test_filter_couples_only_two_faces(self):
           """Test filtering only keeps images with 2 faces"""
           crawler = BaseCrawler(config={})
           images = [
               {"url": "single_person.jpg", "faces": 1},
               {"url": "couple.jpg", "faces": 2},
               {"url": "group.jpg", "faces": 5},
           ]
           filtered = crawler.filter_couples(images)
           assert len(filtered) == 1
           assert filtered[0]["faces"] == 2
       
       def test_crawl_task_pause_resume(self):
           """Test pausing and resuming crawl tasks"""
           # Create task
           task = CrawlTask.create(source_type="pixiv", limit=100)
           
           # Start task
           task.start()
           time.sleep(2)
           
           # Pause task
           task.pause()
           progress_at_pause = task.images_collected
           
           # Resume task
           task.resume()
           time.sleep(2)
           
           assert task.images_collected > progress_at_pause
   ```

**Acceptance Criteria:**
- [ ] Can crawl from at least 2 different sources
- [ ] Face detection filters work correctly
- [ ] Collected images saved with metadata
- [ ] Tasks can be paused/resumed
- [ ] Rate limiting prevents API bans
- [ ] All unit tests pass

**Checkpoint 3.1 - Catcher Service Complete**
```bash
git add app/services/catcher/
git commit -m "Phase 3.1: Image collection service (Catcher) implemented"
git tag checkpoint-3.1
```

---

### Phase 4 — Browser Service (Image Management) 🔄 POST-MVP

**Duration:** 3-4 days

**Objective:**
- Advanced search and filtering
- Tag management system
- Image metadata editor
- Batch operations

**Features:**
- Search by tags, artist, category
- Auto-tagging using AI
- Favorites and collections
- Image quality filtering

**Checkpoint 4.1**
```bash
git commit -m "Phase 4.1: Browser service with advanced search"
git tag checkpoint-4.1
```

---

### Phase 5 — Web Deployment & Production 🔄 POST-MVP

**Duration:** 3-4 days

**Deliverables:**
- Docker containerization
- CI/CD pipeline (GitHub Actions)
- Cloud deployment (AWS/GCP)
- Monitoring and logging
- SSL/HTTPS setup
- Domain configuration

**Checkpoint 5.1 - Production Deployment**
```bash
git commit -m "Phase 5.1: Production deployment complete"
git tag production-v1.0
```

---

## Development Guidelines

### Code Quality Standards

1. **Logging Requirements**
   ```python
   # All services must use structured logging
   import logging
   
   logger = logging.getLogger(__name__)
   
   # Good logging examples
   logger.info(f"Starting face swap task {task_id}", extra={
       "task_id": task_id,
       "user_id": user_id,
       "template_id": template_id
   })
   
   logger.error(f"Face swap failed: {error}", extra={
       "task_id": task_id,
       "error": str(error),
       "traceback": traceback.format_exc()
   })
   ```

2. **Code Comments**
   ```python
   # Use docstrings for all functions and classes
   def swap_couple_faces(husband_img: str, wife_img: str, template_img: str):
       """
       Swap both husband and wife faces into a couple template.
       
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
           numpy.ndarray: Result image with both faces swapped
       
       Raises:
           ValueError: If template has less than 2 faces
           FaceDetectionError: If no face found in source images
       
       Example:
           >>> result = swap_couple_faces(
           ...     "photos/john.jpg",
           ...     "photos/jane.jpg", 
           ...     "templates/movie_couple.jpg"
           ... )
       """
       pass
   ```

3. **Git Commit Standards**
   ```bash
   # Format: [Phase X.Y] Component: Brief description
   
   # Good examples:
   git commit -m "[Phase 1.1] FaceSwap: Implement InsightFace integration"
   git commit -m "[Phase 2.1] Frontend: Add image uploader component"
   git commit -m "[Testing] API: Add integration tests for face-swap endpoint"
   git commit -m "[Bugfix] Core: Fix face detection on anime images"
   
   # Use tags for checkpoints
   git tag checkpoint-1.1 -m "Backend core MVP complete with tests"
   ```

### Testing Strategy

1. **Test-Driven Development (TDD)**
   - Write tests BEFORE implementing features
   - Run tests after every significant change
   - Maintain >= 80% code coverage

2. **Test Pyramid**
   - 70% Unit tests (fast, isolated)
   - 20% Integration tests (API, database)
   - 10% E2E tests (full workflow)

3. **Continuous Testing**
   ```bash
   # Run tests before every commit
   pytest tests/ -v --cov=app --cov-report=html
   
   # Run specific test suite
   pytest tests/test_faceswap_core.py -v
   
   # Run E2E tests (slower)
   pytest tests/e2e/ --headed
   ```

---

## Critical Success Factors

### 1. Face-Swap Algorithm Quality ⭐⭐⭐
- **Priority**: HIGHEST
- **Action**: Extensive testing with diverse image types
- **Metrics**: 
  - Visual quality >= 4/5 rating
  - Face detection accuracy >= 95%
  - Processing time < 10s per image pair

### 2. MVP First Approach
- **Don't build** Catcher/Browser until MVP validated
- **Focus on** Core face-swap functionality
- **Validate** with real users before expanding

### 3. Checkpoint Discipline
- **MUST commit** after every checkpoint
- **MUST tag** checkpoints for easy recovery
- **MUST test** before moving to next phase

### 4. Performance Optimization
- Use GPU acceleration (CUDA)
- Implement image caching
- Optimize database queries
- Use CDN for static assets

---

## Risk Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Face-swap quality poor | HIGH | MEDIUM | Test multiple algorithms in Phase 0, validate early |
| Processing too slow | MEDIUM | MEDIUM | Use GPU, optimize image preprocessing, implement queue |
| Crawler blocked/banned | MEDIUM | HIGH | Implement rate limiting, respect robots.txt, use proxies |
| Storage costs high | LOW | MEDIUM | Implement image compression, cleanup old results |
| GPU memory overflow | MEDIUM | LOW | Batch processing, automatic image resizing |

---

## Success Metrics (KPI)

### MVP Stage (Phases 0-2)
- [ ] Core algorithm validated on 10+ test cases
- [ ] Average processing time < 10 seconds
- [ ] API response time < 200ms (excluding processing)
- [ ] 0 critical bugs after testing phase
- [ ] 5+ users test MVP successfully

### Post-MVP (Phases 3-5)
- [ ] 100+ templates in database
- [ ] Catcher collects 1000+ images/day
- [ ] System handles 50+ concurrent users
- [ ] 99.9% uptime
- [ ] User satisfaction >= 4/5

---

## Quick Start Commands

```bash
# Phase 0 - Setup
git clone <repo-url>
cd couple-faceswap
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
docker-compose up -d postgres redis

# Download models
mkdir -p backend/models
wget https://huggingface.co/ezioruan/inswapper_128.onnx -O backend/models/inswapper_128.onnx

# Run algorithm validation
python tests/validate_algorithm.py

# Phase 1 - Backend MVP
cd backend
uvicorn app.main:app --reload --port 8000

# Phase 2 - Frontend MVP
cd frontend
npm install
npm run dev

# Run tests
pytest tests/ -v
npm test

# Phase 3+ - Full deployment
docker-compose up --build
```

---

## Documentation Structure

```
docs/
├── phase-0/
│   ├── environment-setup.md
│   ├── algorithm-validation.md
│   ├── tech-stack-rationale.md
│   └── database-schema.md
├── phase-1/
│   ├── api-documentation.md
│   ├── faceswap-service-design.md
│   └── testing-strategy.md
├── phase-2/
│   ├── frontend-architecture.md
│   ├── component-library.md
│   └── user-guide.md
├── phase-3/
│   ├── crawler-design.md
│   └── data-collection-guide.md
├── phase-4/
│   ├── browser-service-api.md
│   └── search-optimization.md
└── phase-5/
    ├── deployment-guide.md
    ├── monitoring-setup.md
    └── production-runbook.md
```

---

## Conclusion

This plan prioritizes:
1. ⭐ **MVP first** - Get core face-swap working quickly
2. ⭐ **Testing rigor** - Tests before features, checkpoints before commits
3. ⭐ **Algorithm quality** - Extensive validation of face-swap technology
4. ⭐ **Incremental expansion** - Only add Catcher/Browser after MVP success

**Next Step:** Begin Phase 0 - Algorithm Validation and Environment Setup
