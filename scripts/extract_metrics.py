"""
Extract training metrics from artifacts for reporting.
"""

import argparse
import json
from pathlib import Path


def extract_metrics(artifacts_dir: str, output_path: str):
    """Extract metrics from all location results."""
    artifacts_path = Path(artifacts_dir)

    metrics = {}

    for location in ["A", "B", "C"]:
        results_file = artifacts_path / f"location_{location}_results.json"

        if results_file.exists():
            with open(results_file, "r") as f:
                data = json.load(f)

            # Extract key metrics
            test_metrics = data.get("test_metrics", {})
            cv_metrics = data.get("cv_metrics", {})

            metrics[f"location_{location}"] = {
                "rmse": test_metrics.get("rmse", 0),
                "mae": test_metrics.get("mae", 0),
                "wape": test_metrics.get("wape", 0),
                "interval_coverage": test_metrics.get("interval_coverage", 0),
                "cv_avg_rmse": cv_metrics.get("avg_rmse", 0),
                "cv_avg_mae": cv_metrics.get("avg_mae", 0),
                "training_days": data.get("metadata", {}).get("training_days", 0),
                "test_days": data.get("metadata", {}).get("test_days", 0),
            }

    # Calculate average metrics across locations
    if metrics:
        avg_metrics = {
            "average_rmse": sum(m["rmse"] for m in metrics.values()) / len(metrics),
            "average_mae": sum(m["mae"] for m in metrics.values()) / len(metrics),
            "average_wape": sum(m["wape"] for m in metrics.values()) / len(metrics),
        }
        metrics["summary"] = avg_metrics

    # Save metrics
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Extracted metrics for {len(metrics) - 1} locations")
    print(f"Metrics saved to {output_path}")

    # Print summary
    if "summary" in metrics:
        print("\nSummary Metrics:")
        print(f"  Average RMSE: {avg_metrics['average_rmse']:.2f}")
        print(f"  Average MAE: {avg_metrics['average_mae']:.2f}")
        print(f"  Average WAPE: {avg_metrics['average_wape']:.2f}%")


def main():
    parser = argparse.ArgumentParser(description="Extract training metrics")
    parser.add_argument("--artifacts-dir", required=True, help="Artifacts directory")
    parser.add_argument("--output", default="metrics-summary.json", help="Output file")
    args = parser.parse_args()

    extract_metrics(args.artifacts_dir, args.output)


if __name__ == "__main__":
    main()
