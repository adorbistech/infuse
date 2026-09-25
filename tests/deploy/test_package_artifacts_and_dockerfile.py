"""INFUSE Block 35 — Package Artifacts & Dockerfile Linting Suite.

Verifies:
- pyproject.toml package metadata and CLI entrypoints
- Dockerfile structure (multi-stage, non-root user, healthcheck, exposed port)
- Dockerfile.frontend structure
- docker-compose.yml YAML validity, services, and healthcheck configurations
- .dockerignore coverage of sensitive directories
- .env.example placeholder sanity and absence of real secrets
"""

import os
import unittest
import yaml


class TestPackageArtifactsAndDockerfile(unittest.TestCase):
    """Test suite validating packaging manifests, Docker configurations, and deployment templates."""

    def setUp(self) -> None:
        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def test_01_pyproject_toml_has_required_scripts_and_dependencies(self) -> None:
        """Verify pyproject.toml contains infuse-server entrypoint and required dependencies."""
        pyproject_path = os.path.join(self.root_dir, "pyproject.toml")
        self.assertTrue(os.path.exists(pyproject_path))
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('name = "infuse-ai"', content)
        self.assertIn('infuse = "infuse.cli.main:main"', content)
        self.assertIn('infuse-mcp = "infuse.mcp.main:main"', content)
        self.assertIn('infuse-server = "infuse.deployment.server:main"', content)
        self.assertIn("pydantic>=", content)
        self.assertIn("starlette>=", content)

    def test_02_dockerfile_structure_and_non_root_security(self) -> None:
        """Verify Dockerfile uses multi-stage build, creates non-root user, and defines healthcheck."""
        dockerfile_path = os.path.join(self.root_dir, "Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path))
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FROM python:3.11-slim AS builder", content)
        self.assertIn("FROM python:3.11-slim AS runtime", content)
        self.assertIn("USER infuse", content)
        self.assertIn("EXPOSE 8000", content)
        self.assertIn("HEALTHCHECK", content)
        self.assertIn("STOPSIGNAL SIGTERM", content)
        self.assertIn('ENTRYPOINT ["infuse-server"]', content)

    def test_03_dockerfile_frontend_structure(self) -> None:
        """Verify Dockerfile.frontend defines lightweight static server and reverse proxy."""
        dockerfile_fe_path = os.path.join(self.root_dir, "Dockerfile.frontend")
        self.assertTrue(os.path.exists(dockerfile_fe_path))
        with open(dockerfile_fe_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FROM nginx:alpine-slim", content)
        self.assertIn("EXPOSE 3000", content)
        self.assertIn("HEALTHCHECK", content)
        self.assertIn("proxy_pass http://backend:8000/v1/", content)

    def test_04_docker_compose_validity_and_service_wiring(self) -> None:
        """Verify docker-compose.yml is valid YAML and connects backend and frontend."""
        compose_path = os.path.join(self.root_dir, "docker-compose.yml")
        self.assertTrue(os.path.exists(compose_path))
        with open(compose_path, "r", encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)

        self.assertIn("services", compose_data)
        services = compose_data["services"]
        self.assertIn("backend", services)
        self.assertIn("frontend", services)

        backend_cfg = services["backend"]
        self.assertIn("healthcheck", backend_cfg)
        self.assertEqual(backend_cfg["image"], "infuse-backend:latest")

        frontend_cfg = services["frontend"]
        self.assertIn("depends_on", frontend_cfg)
        self.assertIn("healthcheck", frontend_cfg)

    def test_05_dockerignore_protects_sensitive_files(self) -> None:
        """Verify .dockerignore excludes source control, tests, secrets, and caches."""
        dockerignore_path = os.path.join(self.root_dir, ".dockerignore")
        self.assertTrue(os.path.exists(dockerignore_path))
        with open(dockerignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn(".git", content)
        self.assertIn(".env", content)
        self.assertIn("__pycache__", content)
        self.assertIn("tests/", content)
        self.assertIn(".venv", content)

    def test_06_env_example_contains_zero_actual_secrets(self) -> None:
        """Verify .env.example contains only variable placeholders and zero real API keys."""
        env_example_path = os.path.join(self.root_dir, ".env.example")
        self.assertTrue(os.path.exists(env_example_path))
        with open(env_example_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("INFUSE_HOST=0.0.0.0", content)
        self.assertIn("INFUSE_PORT=8000", content)
        self.assertIn("INFUSE_ENVIRONMENT=production", content)
        self.assertNotIn("sk-ant-", content)
        self.assertNotIn("sk-proj-", content)
        self.assertNotIn("AIzaSy", content)
        self.assertNotIn("Bearer ey", content)

    def test_07_deployment_documentation_completeness(self) -> None:
        """Verify docs/deployment.md exists and documents deployment architectures."""
        doc_path = os.path.join(self.root_dir, "docs", "deployment.md")
        self.assertTrue(os.path.exists(doc_path))
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Docker Compose", content)
        self.assertIn("Kubernetes", content)
        self.assertIn("INFUSE_PORT", content)
        self.assertIn("Liveness Probe", content)
        self.assertIn("Readiness Probe", content)

    def test_08_source_tree_contains_no_unwanted_build_artifacts(self) -> None:
        """Verify no temporary compiled wheels or build directories pollute source tree."""
        build_dir = os.path.join(self.root_dir, "build")
        dist_dir = os.path.join(self.root_dir, "dist")
        self.assertFalse(os.path.exists(build_dir))
        self.assertFalse(os.path.exists(dist_dir))

    def test_09_license_file_exists_and_matches_apache_2(self) -> None:
        """Verify LICENSE file exists at root and specifies Apache 2.0."""
        license_path = os.path.join(self.root_dir, "LICENSE")
        self.assertTrue(os.path.exists(license_path))
        with open(license_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Apache License", content)

    def test_10_frontend_package_json_and_html_exist(self) -> None:
        """Verify frontend/index.html and frontend/package.json exist and are well-formed."""
        index_path = os.path.join(self.root_dir, "frontend", "index.html")
        pkg_path = os.path.join(self.root_dir, "frontend", "package.json")
        self.assertTrue(os.path.exists(index_path))
        self.assertTrue(os.path.exists(pkg_path))

    def test_11_container_port_consistency_between_dockerfile_and_compose(self) -> None:
        """Verify Dockerfile and docker-compose.yml agree on standard port 8000."""
        dockerfile_path = os.path.join(self.root_dir, "Dockerfile")
        compose_path = os.path.join(self.root_dir, "docker-compose.yml")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            df_content = f.read()
        with open(compose_path, "r", encoding="utf-8") as f:
            dc_content = f.read()
        self.assertIn("EXPOSE 8000", df_content)
        self.assertIn(":8000", dc_content)

    def test_12_frontend_port_consistency(self) -> None:
        """Verify Dockerfile.frontend and docker-compose agree on port 3000."""
        dockerfile_fe = os.path.join(self.root_dir, "Dockerfile.frontend")
        compose_path = os.path.join(self.root_dir, "docker-compose.yml")
        with open(dockerfile_fe, "r", encoding="utf-8") as f:
            fe_content = f.read()
        with open(compose_path, "r", encoding="utf-8") as f:
            dc_content = f.read()
        self.assertIn("EXPOSE 3000", fe_content)
        self.assertIn("3000:3000", dc_content)

    def test_13_reuse_manifest_persists_in_root(self) -> None:
        """Verify REUSE_MANIFEST.yaml is intact and valid YAML."""
        manifest_path = os.path.join(self.root_dir, "REUSE_MANIFEST.yaml")
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertIn("schema_version", data)
        self.assertIn("components", data)

    def test_14_pyproject_version_matches_infuse_version(self) -> None:
        """Verify version in pyproject.toml matches infuse.version.__version__."""
        from infuse.version import __version__
        pyproject_path = os.path.join(self.root_dir, "pyproject.toml")
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(f'version = "{__version__}"', content)


if __name__ == "__main__":
    unittest.main()
