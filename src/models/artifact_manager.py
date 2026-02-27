"""
Artifact versioning and management utilities.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


class ArtifactManager:
    """Manage model artifacts with versioning."""

    def __init__(
        self, base_dir: str = "artifacts", registry_dir: str = ".model-registry"
    ):
        self.base_dir = Path(base_dir)
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def save_versioned_artifacts(self, version: str, artifacts: Dict[str, any]):
        """Save artifacts with version."""
        version_dir = self.base_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)

        for name, artifact in artifacts.items():
            artifact_path = version_dir / name

            if isinstance(artifact, pd.DataFrame):
                artifact.to_csv(artifact_path, index=False)
            elif isinstance(artifact, dict):
                with open(artifact_path, "w") as f:
                    json.dump(artifact, f, indent=2)
            else:
                # For pickle files, etc.
                with open(artifact_path, "wb") as f:
                    f.write(artifact)

        return version_dir

    def load_versioned_artifacts(self, version: str) -> Dict:
        """Load artifacts for a specific version."""
        version_dir = self.base_dir / version

        if not version_dir.exists():
            raise ValueError(f"Version {version} not found")

        artifacts = {}

        for file_path in version_dir.glob("*"):
            if file_path.suffix == ".csv":
                artifacts[file_path.name] = pd.read_csv(file_path)
            elif file_path.suffix == ".json":
                with open(file_path, "r") as f:
                    artifacts[file_path.name] = json.load(f)

        return artifacts

    def list_versions(self) -> List[str]:
        """List all available versions."""
        if not self.base_dir.exists():
            return []

        versions = [d.name for d in self.base_dir.iterdir() if d.is_dir()]
        return sorted(versions, reverse=True)

    def get_latest_version(self) -> Optional[str]:
        """Get the latest version."""
        versions = self.list_versions()
        return versions[0] if versions else None

    def get_production_version(self) -> Optional[str]:
        """Get the current production version."""
        prod_file = self.registry_dir / "production.txt"

        if prod_file.exists():
            return prod_file.read_text().strip()

        return None

    def set_production_version(self, version: str):
        """Set a version as production."""
        prod_file = self.registry_dir / "production.txt"
        prod_file.write_text(version)

        # Also update registry
        self._update_registry(version, status="production")

    def _update_registry(self, version: str, status: str):
        """Update registry with version status."""
        registry_file = self.registry_dir / f"{version}.json"

        if registry_file.exists():
            with open(registry_file, "r") as f:
                entry = json.load(f)
        else:
            entry = {"version": version, "created_at": datetime.utcnow().isoformat()}

        entry["status"] = status
        entry["status_updated_at"] = datetime.utcnow().isoformat()

        with open(registry_file, "w") as f:
            json.dump(entry, f, indent=2)

    def compare_versions(self, version1: str, version2: str) -> Dict:
        """Compare metrics between two versions."""

        def load_metrics(version):
            metrics_file = self.base_dir / version / "metrics-summary.json"
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    return json.load(f)
            return {}

        metrics1 = load_metrics(version1)
        metrics2 = load_metrics(version2)

        comparison = {"version1": version1, "version2": version2, "metrics": {}}

        # Compare summary metrics
        if "summary" in metrics1 and "summary" in metrics2:
            for metric in ["average_rmse", "average_mae", "average_wape"]:
                val1 = metrics1["summary"].get(metric, 0)
                val2 = metrics2["summary"].get(metric, 0)

                comparison["metrics"][metric] = {
                    "version1": val1,
                    "version2": val2,
                    "difference": val2 - val1,
                    "improvement_pct": ((val1 - val2) / val1 * 100) if val1 != 0 else 0,
                }

        return comparison


def create_version_tag(prefix: str = "v") -> str:
    """Create a version tag with timestamp and random suffix."""
    import hashlib
    import time

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    # Create a short hash from timestamp
    hash_obj = hashlib.md5(str(time.time()).encode())
    short_hash = hash_obj.hexdigest()[:6]

    return f"{prefix}{timestamp}-{short_hash}"


if __name__ == "__main__":
    # Example usage
    manager = ArtifactManager()

    print("Available versions:")
    for version in manager.list_versions():
        print(f"  - {version}")

    latest = manager.get_latest_version()
    if latest:
        print(f"\nLatest version: {latest}")

    production = manager.get_production_version()
    if production:
        print(f"Production version: {production}")
