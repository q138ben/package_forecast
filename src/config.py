"""
Load environment variables from .env file.
"""

import os
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[str] = None) -> dict:
    """
    Load environment variables from .env file.

    Args:
        env_path: Path to .env file. If None, looks for .env in project root.

    Returns:
        Dictionary of environment variables
    """
    if env_path is None:
        # Look for .env in project root (parent of src/)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        env_path = project_root / ".env"
    else:
        env_path = Path(env_path)

    env_vars = {}

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse key=value pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    env_vars[key] = value
                    # Also set in os.environ if not already set
                    if key not in os.environ:
                        os.environ[key] = value

    return env_vars


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable with fallback to .env file.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Environment variable value or default
    """
    # First check os.environ
    value = os.environ.get(key)

    if value is None:
        # Try loading from .env
        env_vars = load_env_file()
        value = env_vars.get(key, default)

    return value


def get_project_config() -> dict:
    """
    Get GCP project configuration from environment.

    Returns:
        Dictionary with project configuration
    """
    return {
        "project_id": get_env("GCP_PROJECT_ID"),
        "region": get_env("GCP_REGION", "us-central1"),
        "service_name": get_env("CLOUD_RUN_SERVICE_NAME", "package-forecast"),
        "artifacts_bucket": get_env(
            "ARTIFACTS_BUCKET", "gs://package-forecast-artifacts"
        ),
    }


# Auto-load .env file when module is imported
try:
    load_env_file()
except Exception:
    pass  # Silently fail if .env doesn't exist
