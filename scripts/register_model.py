"""
Register trained model in model registry.
"""

import argparse
import json
from datetime import datetime


def register_model(
    version: str,
    metrics_file: str,
    artifacts_dir: str,
    git_commit: str,
    output_path: str,
):
    """Register a trained model version."""

    # Load metrics
    with open(metrics_file, "r") as f:
        metrics = json.load(f)

    # Create registry entry
    registry_entry = {
        "version": version,
        "timestamp": datetime.utcnow().isoformat(),
        "git_commit": git_commit,
        "metrics": metrics,
        "artifacts_location": f"gs://package-forecast-artifacts/{version}",
        "status": "registered",
        "trained_locations": ["A", "B", "C"],
        "model_type": "prophet",
        "metadata": {
            "training_framework": "prophet",
            "horizon_days": 30,
            "cv_folds": 5,
            "test_days": 30,
        },
    }

    # Determine if model should be promoted to production
    # Based on performance thresholds
    summary = metrics.get("summary", {})
    avg_wape = summary.get("average_wape", 100)

    if avg_wape < 15:  # Less than 15% WAPE is good
        registry_entry["status"] = "production_candidate"
        registry_entry["promotion_notes"] = "Model meets production quality thresholds"

    # Save registry entry
    with open(output_path, "w") as f:
        json.dump(registry_entry, f, indent=2)

    print(f"Model {version} registered successfully")
    print(f"Status: {registry_entry['status']}")
    print(f"Registry entry saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Register model in model registry")
    parser.add_argument("--version", required=True, help="Model version")
    parser.add_argument("--metrics", required=True, help="Metrics JSON file")
    parser.add_argument("--artifacts-dir", required=True, help="Artifacts directory")
    parser.add_argument("--git-commit", required=True, help="Git commit SHA")
    parser.add_argument("--output", default="model-registry.json", help="Output file")
    args = parser.parse_args()

    register_model(
        args.version, args.metrics, args.artifacts_dir, args.git_commit, args.output
    )


if __name__ == "__main__":
    main()
