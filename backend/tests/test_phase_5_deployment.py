"""
Phase 5 - Deployment & Production Tests

Tests for deployment configurations, health checks, and production readiness
"""

import pytest
import os
import yaml
from pathlib import Path


@pytest.fixture
def root_dir():
    """Get root directory (parent of backend)"""
    return Path(__file__).parent.parent.parent


class TestDockerConfiguration:
    """Test Docker configuration files"""

    def test_production_docker_compose_exists(self, root_dir):
        """Test production docker-compose.yml exists"""
        compose_file = root_dir / "docker-compose.prod.yml"
        assert compose_file.exists(), "docker-compose.prod.yml not found"

    def test_production_docker_compose_valid(self, root_dir):
        """Test production docker-compose.yml is valid YAML"""
        with open(root_dir / "docker-compose.prod.yml") as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert "services" in config
        assert "postgres" in config["services"]
        assert "redis" in config["services"]
        assert "backend" in config["services"]
        assert "frontend" in config["services"]
        assert "celery_worker" in config["services"]

    def test_backend_production_dockerfile_exists(self, root_dir):
        """Test backend production Dockerfile exists"""
        dockerfile = root_dir / "backend" / "Dockerfile.prod"
        assert dockerfile.exists(), "backend/Dockerfile.prod not found"

    def test_frontend_production_dockerfile_exists(self, root_dir):
        """Test frontend production Dockerfile exists"""
        dockerfile = root_dir / "frontend" / "Dockerfile.prod"
        assert dockerfile.exists(), "frontend/Dockerfile.prod not found"

    def test_backend_dockerfile_has_healthcheck(self, root_dir):
        """Test backend Dockerfile includes health check"""
        with open(root_dir / "backend" / "Dockerfile.prod") as f:
            content = f.read()

        assert "HEALTHCHECK" in content, "Backend Dockerfile missing HEALTHCHECK"
        assert "curl" in content or "wget" in content

    def test_frontend_dockerfile_has_healthcheck(self, root_dir):
        """Test frontend Dockerfile includes health check"""
        with open(root_dir / "frontend" / "Dockerfile.prod") as f:
            content = f.read()

        assert "HEALTHCHECK" in content, "Frontend Dockerfile missing HEALTHCHECK"


class TestNginxConfiguration:
    """Test Nginx configuration files"""

    def test_nginx_config_exists(self, root_dir):
        """Test nginx.conf exists"""
        nginx_conf = root_dir / "nginx" / "nginx.conf"
        assert nginx_conf.exists(), "nginx/nginx.conf not found"

    def test_nginx_faceswap_conf_exists(self, root_dir):
        """Test faceswap.conf exists"""
        faceswap_conf = root_dir / "nginx" / "conf.d" / "faceswap.conf"
        assert faceswap_conf.exists(), "nginx/conf.d/faceswap.conf not found"

    def test_nginx_config_has_gzip(self, root_dir):
        """Test nginx.conf has gzip enabled"""
        with open(root_dir / "nginx" / "nginx.conf") as f:
            content = f.read()

        assert "gzip on" in content, "Gzip not enabled in nginx.conf"

    def test_nginx_config_has_rate_limiting(self, root_dir):
        """Test nginx.conf has rate limiting"""
        with open(root_dir / "nginx" / "nginx.conf") as f:
            content = f.read()

        assert "limit_req_zone" in content, "Rate limiting not configured"

    def test_nginx_faceswap_config_has_backends(self, root_dir):
        """Test faceswap.conf has upstream backends"""
        with open(root_dir / "nginx" / "conf.d" / "faceswap.conf") as f:
            content = f.read()

        assert "upstream backend_api" in content
        assert "upstream frontend_app" in content


class TestMonitoringConfiguration:
    """Test monitoring configuration files"""

    def test_prometheus_config_exists(self, root_dir):
        """Test prometheus.yml exists"""
        prometheus_conf = root_dir / "monitoring" / "prometheus.yml"
        assert prometheus_conf.exists(), "monitoring/prometheus.yml not found"

    def test_prometheus_config_valid(self, root_dir):
        """Test prometheus.yml is valid YAML"""
        with open(root_dir / "monitoring" / "prometheus.yml") as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert "scrape_configs" in config
        assert isinstance(config["scrape_configs"], list)

    def test_prometheus_scrapes_backend(self, root_dir):
        """Test Prometheus configured to scrape backend"""
        with open(root_dir / "monitoring" / "prometheus.yml") as f:
            config = yaml.safe_load(f)

        job_names = [job["job_name"] for job in config["scrape_configs"]]
        assert "backend" in job_names, "Backend not in Prometheus scrape targets"

    def test_grafana_datasource_exists(self, root_dir):
        """Test Grafana datasource config exists"""
        datasource = root_dir / "monitoring" / "grafana" / "datasources" / "prometheus.yml"
        assert datasource.exists(), "Grafana datasource config not found"

    def test_grafana_dashboard_config_exists(self, root_dir):
        """Test Grafana dashboard config exists"""
        dashboard = root_dir / "monitoring" / "grafana" / "dashboards" / "dashboard.yml"
        assert dashboard.exists(), "Grafana dashboard config not found"


class TestCICDConfiguration:
    """Test CI/CD configuration files"""

    def test_github_actions_workflow_exists(self, root_dir):
        """Test GitHub Actions workflow exists"""
        workflow = root_dir / ".github" / "workflows" / "ci-cd.yml"
        assert workflow.exists(), ".github/workflows/ci-cd.yml not found"

    def test_github_actions_workflow_valid(self, root_dir):
        """Test GitHub Actions workflow is valid YAML"""
        with open(root_dir / ".github" / "workflows" / "ci-cd.yml") as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert "jobs" in config

    def test_github_actions_has_backend_tests(self, root_dir):
        """Test GitHub Actions has backend test job"""
        with open(root_dir / ".github" / "workflows" / "ci-cd.yml") as f:
            config = yaml.safe_load(f)

        assert "backend-tests" in config["jobs"]

    def test_github_actions_has_frontend_tests(self, root_dir):
        """Test GitHub Actions has frontend test job"""
        with open(root_dir / ".github" / "workflows" / "ci-cd.yml") as f:
            config = yaml.safe_load(f)

        assert "frontend-tests" in config["jobs"]

    def test_github_actions_has_docker_build(self, root_dir):
        """Test GitHub Actions has Docker build job"""
        with open(root_dir / ".github" / "workflows" / "ci-cd.yml") as f:
            config = yaml.safe_load(f)

        assert "docker-build" in config["jobs"]

    def test_github_actions_has_security_scan(self, root_dir):
        """Test GitHub Actions has security scan job"""
        with open(root_dir / ".github" / "workflows" / "ci-cd.yml") as f:
            config = yaml.safe_load(f)

        assert "security-scan" in config["jobs"]


class TestEnvironmentConfiguration:
    """Test environment configuration files"""

    def test_env_example_exists(self, root_dir):
        """Test .env.example exists"""
        env_example = root_dir / ".env.example"
        assert env_example.exists(), ".env.example not found"

    def test_env_example_has_database_config(self, root_dir):
        """Test .env.example has database configuration"""
        with open(root_dir / ".env.example") as f:
            content = f.read()

        assert "POSTGRES_DB" in content
        assert "POSTGRES_USER" in content
        assert "POSTGRES_PASSWORD" in content

    def test_env_example_has_redis_config(self, root_dir):
        """Test .env.example has Redis configuration"""
        with open(root_dir / ".env.example") as f:
            content = f.read()

        assert "REDIS" in content

    def test_env_example_has_security_config(self, root_dir):
        """Test .env.example has security configuration"""
        with open(root_dir / ".env.example") as f:
            content = f.read()

        assert "SECRET_KEY" in content
        assert "CORS_ORIGINS" in content

    def test_env_example_no_real_secrets(self, root_dir):
        """Test .env.example doesn't contain real secrets"""
        with open(root_dir / ".env.example") as f:
            content = f.read()

        # Check for placeholder values
        assert "CHANGE_ME" in content or "your-" in content or "<" in content


class TestDeploymentDocumentation:
    """Test deployment documentation"""

    def test_deployment_docs_exist(self, root_dir):
        """Test DEPLOYMENT.md exists"""
        docs = root_dir / "docs" / "DEPLOYMENT.md"
        assert docs.exists(), "docs/DEPLOYMENT.md not found"

    def test_deployment_docs_has_sections(self, root_dir):
        """Test DEPLOYMENT.md has required sections"""
        with open(root_dir / "docs" / "DEPLOYMENT.md") as f:
            content = f.read()

        required_sections = [
            "Prerequisites",
            "Development Deployment",
            "Production Deployment",
            "Monitoring",
            "Backup",
            "Troubleshooting"
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"


class TestHealthCheckEndpoints:
    """Test health check endpoints"""

    def test_backend_has_health_endpoint(self, root_dir):
        """Test backend has /health endpoint"""
        with open(root_dir / "backend" / "app" / "main.py") as f:
            content = f.read()

        assert "@app.get(\"/health\")" in content or "async def health" in content

    def test_frontend_nginx_has_health_endpoint(self, root_dir):
        """Test frontend nginx config has health endpoint"""
        with open(root_dir / "frontend" / "nginx.conf") as f:
            content = f.read()

        assert "location /health" in content


class TestProductionReadiness:
    """Test production readiness checks"""

    def test_frontend_nginx_has_security_headers(self, root_dir):
        """Test frontend nginx has security headers"""
        with open(root_dir / "frontend" / "nginx.conf") as f:
            content = f.read()

        security_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection"
        ]

        for header in security_headers:
            assert header in content, f"Missing security header: {header}"

    def test_nginx_has_gzip_compression(self, root_dir):
        """Test nginx has gzip compression"""
        with open(root_dir / "nginx" / "nginx.conf") as f:
            content = f.read()

        assert "gzip on" in content
        assert "gzip_types" in content

    def test_production_compose_has_restart_policy(self, root_dir):
        """Test production compose has restart policies"""
        with open(root_dir / "docker-compose.prod.yml") as f:
            config = yaml.safe_load(f)

        for service_name, service_config in config["services"].items():
            # Skip services with profiles (they might not always run)
            if "profiles" in service_config:
                continue

            assert "restart" in service_config, \
                f"Service {service_name} missing restart policy"

    def test_production_compose_has_healthchecks(self, root_dir):
        """Test production compose has health checks for critical services"""
        with open(root_dir / "docker-compose.prod.yml") as f:
            config = yaml.safe_load(f)

        critical_services = ["postgres", "redis", "backend"]

        for service_name in critical_services:
            service_config = config["services"][service_name]
            assert "healthcheck" in service_config, \
                f"Service {service_name} missing healthcheck"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
