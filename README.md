# Animate-CoSwap: AI Couple Face-Swap Platform

[中文文档](./README_CN.md)

An AI-powered web platform for couple face-swapping. Upload photos of two people, select a template, and generate high-quality face-swapped images using state-of-the-art deep learning models.

**Status:** MVP Complete (Phases 0–5) | **294 tests passing** | **Python 3.10+ / React 18+**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client (Browser)                            │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐   │
│  │ ImageUploader │  │TemplateGallery│  │    TaskProgress        │   │
│  │  (React+TS)  │  │  (Ant Design) │  │  (Polling / WebSocket) │   │
│  └──────┬───────┘  └───────┬───────┘  └───────────┬────────────┘   │
│         └──────────────────┼──────────────────────┘                 │
│                            │ Axios HTTP                             │
└────────────────────────────┼────────────────────────────────────────┘
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy (:80)                       │
└──────────────┬─────────────────────────────────┬──────────────────┘
               ▼                                 ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│  Frontend Static (:3000) │    │   FastAPI Backend (:8000)        │
│  Vite + React + TS       │    │                                  │
│                          │    │  ┌──────────────────────────────┐│
│  Pages:                  │    │  │     API Layer (v1)           ││
│  • FaceSwapWorkflow      │    │  │  /photos   /templates       ││
│    (4-step wizard)       │    │  │  /faceswap /admin/cleanup   ││
│                          │    │  │  /catcher  /browser         ││
│  Components:             │    │  └─────────────┬────────────────┘│
│  • ImageUploader         │    │                │                 │
│  • TemplateGallery       │    │  ┌─────────────▼────────────────┐│
│  • TaskProgress          │    │  │     Service Layer            ││
│                          │    │  │  • FaceSwapper (core.py)     ││
└──────────────────────────┘    │  │  • Preprocessor              ││
                                │  │  • FaceMappingService        ││
                                │  │  • BatchProcessingService    ││
                                │  │  • CleanupService            ││
                                │  │  • Catcher (Pixiv/Danbooru)  ││
                                │  │  • Browser (search/filter)   ││
                                │  └─────────────┬────────────────┘│
                                │                │                 │
                                │  ┌─────────────▼────────────────┐│
                                │  │     Data Layer               ││
                                │  │  PostgreSQL + SQLAlchemy ORM ││
                                │  │  Redis (cache + task queue)  ││
                                │  │  Local/S3 file storage       ││
                                │  └──────────────────────────────┘│
                                └──────────────────────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────┐
                    ▼                          ▼                  ▼
            ┌──────────────┐        ┌──────────────┐    ┌──────────────┐
            │ PostgreSQL   │        │    Redis      │    │ File Storage │
            │   (:5432)    │        │   (:6379)     │    │  (local/S3)  │
            │              │        │               │    │              │
            │ • images     │        │ • task queue  │    │ • temp/      │
            │ • templates  │        │ • cache       │    │ • templates/ │
            │ • tasks      │        │ • sessions    │    │ • results/   │
            │ • batches    │        │               │    │              │
            └──────────────┘        └───────────────┘    └──────────────┘
```

### Face-Swap Processing Pipeline

```
Input                    Processing                              Output
─────                    ──────────                              ──────

Husband Photo ──┐
                │     ┌───────────────┐    ┌──────────────┐
                ├────►│ Face Detection │───►│  Face Embed  │
                │     │  (SCRFD/       │    │  (ArcFace    │──┐
Wife Photo ─────┘     │   RetinaFace)  │    │   512-dim)   │  │
                      └───────────────┘    └──────────────┘  │
                                                              │
Template ────────────►┌───────────────┐                       │
  (Couple image)      │ Face Detection │                       │
                      │ + Gender       │                       │
                      │ Classification │                       │
                      └───────┬───────┘                       │
                              │                               │
                              ▼                               ▼
                      ┌───────────────────────────────────────────┐
                      │         Face Mapping & Swapping           │
                      │                                           │
                      │  1. Detect faces in template              │
                      │  2. Classify gender (male/female)         │
                      │  3. Map husband → male face position      │
                      │  4. Map wife → female face position       │
                      │  5. Swap face #1 (inswapper_128.onnx)     │
                      │  6. Swap face #2 (inswapper_128.onnx)     │
                      │  7. Blend & post-process                  │
                      └─────────────────────┬─────────────────────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │ Result Image  │
                                    │  (saved to    │
                                    │   storage)    │
                                    └──────────────┘
```

---

## Core Algorithm: How Face-Swapping Works

This project uses the **InsightFace** ecosystem, the industry standard for face analysis and manipulation.

### Pipeline Components

| Stage | Model/Method | Description |
|-------|-------------|-------------|
| **Face Detection** | SCRFD (via `buffalo_l`) | Detects face bounding boxes and 5-point landmarks. SCRFD is a sample-and-computation redistribution-based detector achieving SOTA on WiderFace. |
| **Face Embedding** | ArcFace (via `buffalo_l`) | Extracts 512-dimensional face embeddings for identity representation. Uses additive angular margin loss for discriminative feature learning. |
| **Gender/Age** | Attribute model (via `buffalo_l`) | Classifies detected faces by gender and age. Used for automatic husband→male / wife→female mapping. |
| **Face Swapping** | `inswapper_128.onnx` | The core swapping model. Takes a source face embedding and a target face region, generates the swapped result while preserving target pose, lighting, and expression. Based on a modified encoder-decoder architecture. |
| **Post-Processing** | OpenCV blending | Seamless boundary blending to reduce artifacts at swap boundaries. |

### Key Algorithms Explained

**ArcFace (Additive Angular Margin Loss):**
ArcFace maps faces to a hypersphere in 512-dimensional space where the angular distance between embeddings corresponds to face similarity. The additive angular margin penalty (m=0.5) enforces a geodesic distance margin between classes, making identity features highly discriminative. This enables the swapper to faithfully transfer identity.

**SCRFD (Sample and Computation Redistribution Face Detector):**
SCRFD redistributes positive samples and computation across different feature pyramid levels, achieving a 2.5x speedup over RetinaFace with comparable accuracy. It detects faces at multiple scales and outputs 5-point landmarks (2 eyes, nose, 2 mouth corners) used for face alignment.

**inswapper Architecture:**
The inswapper model uses an encoder-decoder architecture where:
1. The encoder extracts identity features from the source face via ArcFace embedding
2. The decoder generates the swapped face conditioned on the target face's pose, expression, and lighting
3. The 128x128 output is upsampled and blended into the original template image

### Performance Characteristics

| Metric | CPU (x86_64) | GPU (CUDA) | Apple Silicon |
|--------|:----------:|:----------:|:-------------:|
| Face Detection | ~50ms | ~10ms | ~15ms |
| Face Swap (per face) | ~3s | ~0.5s | ~1s |
| Full Couple Swap | ~8s | ~2s | ~3s |
| Face Detection Accuracy | ≥95% | ≥95% | ≥95% |

---

## Comparison with Related Projects

### Overview of Face-Swap Ecosystem

| Project | Stars | Core Tech | Approach | Real-time | Batch | Web UI |
|---------|:-----:|-----------|----------|:---------:|:-----:|:------:|
| **[InsightFace](https://github.com/deepinsight/insightface)** | 24k+ | ArcFace + inswapper | Library/toolkit | No | No | No |
| **[FaceFusion](https://github.com/facefusion/facefusion)** | 20k+ | InsightFace + GFPGAN | CLI + Gradio | Yes | No | Gradio |
| **[roop](https://github.com/s0md3v/roop)** | 26k+ | InsightFace | CLI + Gradio | No | No | Gradio |
| **[DeepFaceLab](https://github.com/iperov/DeepFaceLab)** | 47k+ | Custom autoencoders | Train per-pair | No | No | No |
| **[SimSwap](https://github.com/neuralchen/SimSwap)** | 4k+ | ID injection GAN | Pre-trained GAN | No | No | No |
| **Animate-CoSwap (this)** | — | InsightFace + inswapper | Full-stack web app | No | Yes | React |

### Detailed Comparison

#### vs. FaceFusion
- **FaceFusion** is the most feature-rich CLI/Gradio tool. It supports face swapping, enhancement (GFPGAN, CodeFormer), lip sync, and frame processing for videos.
- **Our advantage:** Production-ready web application with REST API, database-backed template management, batch processing, session-based uploads, auto-cleanup, and multi-user support. FaceFusion is a single-user desktop tool.
- **Their advantage:** Video support, more post-processing options (GFPGAN, CodeFormer), real-time preview, more mature face enhancement pipeline.

#### vs. roop
- **roop** pioneered the one-click face swap approach using InsightFace. It's simple but limited to single face swaps.
- **Our advantage:** Couple-specific workflow (dual face swap with gender mapping), template gallery, batch processing, persistent storage, API-first design.
- **Their advantage:** Simpler to use for quick single-face swaps, active community, video support.

#### vs. DeepFaceLab
- **DeepFaceLab** trains custom autoencoder models per face pair, achieving the highest quality results but requiring hours of training.
- **Our advantage:** Zero training time — instant results using pre-trained inswapper model. Web-based, no local GPU required.
- **Their advantage:** Superior quality for specific face pairs (after training), deepfake video creation, most mature project.

#### vs. SimSwap
- **SimSwap** uses an ID injection module with a GAN-based architecture for arbitrary face swapping.
- **Our advantage:** Full production stack (API, database, frontend), couple-specific features, easier deployment.
- **Their advantage:** Research-grade GAN architecture with published paper, potentially better preservation of target attributes.

### What Makes This Project Unique

1. **Couple-Focused Workflow:** Purpose-built for swapping two faces (husband + wife) into couple templates with automatic gender-based face mapping.
2. **Template Gallery System:** Persistent, categorized template management with preprocessing (face detection, gender classification, face masks).
3. **Production Web Architecture:** Not a Gradio demo — full REST API, React frontend, PostgreSQL persistence, Redis task queue, Docker deployment.
4. **Batch Processing:** Process multiple templates with the same photo pair in one request.
5. **Session-Based Uploads:** Temporary photo storage with automatic expiration and cleanup, suitable for multi-user deployments.

### Areas for Improvement

1. **Face Enhancement:** No GFPGAN/CodeFormer post-processing yet. Adding this would significantly improve output quality, especially at face boundaries.
2. **Video Support:** Currently image-only. Video face-swapping would require frame extraction, per-frame processing, and temporal consistency.
3. **Real-time Preview:** No live preview during processing. Could be added with WebSocket progress streaming.
4. **Multi-face Templates:** Currently optimized for couple (2-face) templates. Extending to group photos would require more flexible mapping.

---

## Features

### Implemented (MVP + Phases 1.5–5)
- Separated photo (temporary) and template (permanent) upload APIs
- Template preprocessing with face detection and gender classification
- Flexible face mapping (automatic gender-based or custom manual mapping)
- Batch face-swap processing across multiple templates
- Auto-cleanup of expired temporary files
- Image collection from Pixiv/Danbooru (Catcher service)
- Advanced image search and filtering (Browser service)
- Full React TypeScript frontend with 4-step wizard workflow
- Docker Compose deployment (dev + production)
- Prometheus + Grafana monitoring (optional)

### Planned
- Face enhancement (GFPGAN / CodeFormer integration)
- Video face-swapping support
- User authentication and rate limiting
- S3/MinIO cloud storage backend
- WebSocket real-time progress updates

---

## Technology Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.10+ |
| Web Framework | FastAPI | 0.104+ |
| ORM | SQLAlchemy | 2.0+ |
| Database | PostgreSQL | 14+ |
| Task Queue | Celery + Redis | 5.3+ |
| Face Analysis | InsightFace | 0.7.3 |
| Face Swapping | inswapper_128.onnx | — |
| ML Runtime | ONNX Runtime | 1.16+ |
| Image Processing | OpenCV, Pillow | — |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React + TypeScript | 18.2+ / 5.3+ |
| Build Tool | Vite | 5.0+ |
| UI Library | Ant Design | 5.11+ |
| HTTP Client | Axios | 1.6+ |
| State | React Query | 3.39+ |

### DevOps
| Component | Technology |
|-----------|-----------|
| Containers | Docker + Docker Compose |
| Reverse Proxy | Nginx |
| Monitoring | Prometheus + Grafana |
| CI/CD | GitHub Actions |

---

## Project Structure

```
animate-coswap/
├── backend/
│   ├── app/
│   │   ├── api/v1/              # REST API endpoints
│   │   │   ├── photos.py        #   Temporary photo uploads
│   │   │   ├── templates.py     #   Template management
│   │   │   ├── faceswap.py      #   Face-swap operations
│   │   │   ├── faceswap_v15.py  #   Enhanced swap + batch
│   │   │   ├── cleanup.py       #   Auto-cleanup admin
│   │   │   ├── catcher.py       #   Image collection
│   │   │   └── browser.py       #   Search & filter
│   │   ├── services/            # Business logic
│   │   │   ├── faceswap/
│   │   │   │   ├── core.py      #   FaceSwapper engine
│   │   │   │   └── processor.py #   Background task runner
│   │   │   ├── preprocessing.py #   Template face analysis
│   │   │   ├── face_mapping.py  #   Gender-based mapping
│   │   │   ├── batch_processing.py
│   │   │   └── cleanup.py       #   Expiration logic
│   │   ├── models/              # SQLAlchemy + Pydantic
│   │   ├── core/                # Config, DB setup
│   │   └── utils/               # Storage, helpers
│   ├── tests/                   # 294+ tests, 17 test files
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # FaceSwapWorkflow (4-step)
│   │   ├── components/          # ImageUploader, TemplateGallery, TaskProgress
│   │   └── services/api.ts      # API client
│   └── package.json
├── docker-compose.yml           # Development stack
├── docker-compose.prod.yml      # Production stack
├── nginx/                       # Reverse proxy config
├── monitoring/                  # Prometheus + Grafana
└── docs/                        # Phase documentation
```

---

## Getting Started

### Prerequisites

- Python 3.10+, Node.js 18+, Docker (optional)
- PostgreSQL 14+ and Redis 7+ (or use Docker Compose)
- ~600MB disk space for the face-swap model

### Quick Start

```bash
# 1. Clone
git clone https://github.com/zlrrr/animate-coswap.git
cd animate-coswap

# 2. Start infrastructure
docker-compose up -d postgres redis

# 3. Backend setup
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 4. Download face-swap model (~554MB)
mkdir -p models
wget https://huggingface.co/ezioruan/inswapper_128.onnx -O models/inswapper_128.onnx

# 5. Run backend
uvicorn app.main:app --reload --port 8000

# 6. Frontend setup (new terminal)
cd frontend
npm install && npm run dev
```

Access: Frontend at `http://localhost:3000` | API docs at `http://localhost:8000/docs`

### Docker (Full Stack)

```bash
docker-compose --profile full up --build

# With monitoring:
docker-compose --profile full --profile monitoring up --build
```

### Run Tests

```bash
cd backend
pytest tests/ -v --tb=short         # All tests
pytest tests/ --benchmark-only      # Performance benchmarks
pytest tests/ --cov=app             # With coverage report
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/photos/upload` | Upload temporary photo |
| `POST` | `/api/v1/templates/upload` | Upload permanent template |
| `GET` | `/api/v1/templates/` | List/filter templates |
| `POST` | `/api/v1/faceswap/swap` | Create face-swap task |
| `GET` | `/api/v1/faceswap/task/{id}` | Get task status |
| `POST` | `/api/v1/faceswap/batch` | Batch swap (multiple templates) |
| `POST` | `/api/v1/admin/cleanup/expired` | Clean expired files |

Full interactive docs: `http://localhost:8000/docs` (Swagger UI)

---

## Platform Support

| Platform | Architecture | Acceleration | Performance |
|----------|:------------|:------------|:-----------|
| Linux x86_64 | x86_64 | NVIDIA CUDA / CPU | Best |
| macOS Apple Silicon | ARM64 | CoreML + Neural Engine | Excellent |
| Windows | x86_64 | NVIDIA CUDA / CPU | Very Good |
| Linux ARM64 | ARM64 | CUDA (Jetson) / CPU | Good |

---

## Roadmap

- [x] Phase 0: Environment & Algorithm Validation
- [x] Phase 1: Backend REST API
- [x] Phase 1.5: Enhanced Features (preprocessing, batch, mapping, cleanup)
- [x] Phase 2: React Frontend
- [x] Phase 3: Catcher Service (Pixiv/Danbooru collection)
- [x] Phase 4: Browser Service (search & filtering)
- [x] Phase 5: Production Deployment
- [ ] Phase 6: Face Enhancement (GFPGAN/CodeFormer)
- [ ] Phase 7: Video Face-Swapping
- [ ] Phase 8: User Auth & Multi-tenant

---

## Documentation

- [Project Plan (PLAN.md)](./PLAN.md) — Full roadmap with phase details
- [Quick Start Guide](./QUICKSTART.md) — 5-minute setup
- [API Documentation](./docs/phase-1/api-documentation.md) — Endpoint reference
- [MVP Report](./docs/MVP-COMPLETE.md) — Completion summary
- [Platform Support](./docs/PLATFORM-SUPPORT.md) — OS-specific guides
- [Deployment Guide](./docs/DEPLOYMENT.md) — Production deployment
- [Database Troubleshooting](./docs/TROUBLESHOOTING-DATABASE.md)

---

## License

See [LICENSE](./LICENSE) file for details.

## Acknowledgments

- [InsightFace](https://github.com/deepinsight/insightface) — Face detection, recognition, and swapping models
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [React](https://react.dev/) — Frontend UI library
- [Ant Design](https://ant.design/) — UI component library
