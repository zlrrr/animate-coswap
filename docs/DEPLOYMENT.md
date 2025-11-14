# FaceSwap Application - Deployment Guide

## Overview

Production deployment guide for the FaceSwap application.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- Git 2.30+
- 4+ CPU cores, 8GB+ RAM, 50GB+ storage

## Development Deployment

### Quick Start

```bash
# Start services
docker-compose up -d postgres redis

# Run backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Production Deployment

### 1. Environment Configuration

```bash
cp .env.example .env
# Edit .env with production values
```

### 2. Build and Start

```bash
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 3. With Monitoring

```bash
docker-compose -f docker-compose.prod.yml --profile monitoring up -d
```

## Monitoring

- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090

## Backup

```bash
docker-compose -f docker-compose.prod.yml exec postgres pg_dump \
  -U faceswap_user faceswap > backup.sql
```

## Troubleshooting

### Database Connection Issues

```bash
docker-compose logs postgres
docker-compose exec postgres psql -U faceswap_user -d faceswap -c "SELECT 1;"
```

### Check Health

```bash
curl http://localhost:8000/health
```

## Security Checklist

- [ ] Change default passwords
- [ ] Configure CORS origins
- [ ] Enable SSL/HTTPS
- [ ] Set up backups
- [ ] Configure monitoring
