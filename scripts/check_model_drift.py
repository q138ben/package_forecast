"""
Check for model drift by comparing recent predictions with historical performance.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


def check_drift(artifacts_dir: str, output_path: str):
    """Check for potential model drift."""
    artifacts_path = Path(artifacts_dir)

    drift_report = {
        "timestamp": datetime.utcnow().isoformat(),
        "locations": {},
        "overall_drift_detected": False,
    }

    for location in ["A", "B", "C"]:
        results_file = artifacts_path / f"location_{location}_results.json"
        forecast_file = artifacts_path / f"location_{location}_forecast.csv"

        if not results_file.exists() or not forecast_file.exists():
            continue

        # Load data
        with open(results_file, "r") as f:
            results = json.load(f)

        forecast_df = pd.read_csv(forecast_file)

        # Analyze forecast characteristics
        location_drift = {
            "forecast_mean": float(forecast_df["yhat"].mean()),
            "forecast_std": float(forecast_df["yhat"].std()),
            "forecast_min": float(forecast_df["yhat"].min()),
            "forecast_max": float(forecast_df["yhat"].max()),
        }

        # Compare with training statistics
        metadata = results.get("metadata", {})
        training_mean = metadata.get("mean_packages", 0)
        training_std = metadata.get("std_packages", 0)

        # Check for significant deviations
        mean_deviation = (
            abs(location_drift["forecast_mean"] - training_mean) / training_mean
            if training_mean > 0
            else 0
        )
        std_deviation = (
            abs(location_drift["forecast_std"] - training_std) / training_std
            if training_std > 0
            else 0
        )

        location_drift["training_mean"] = training_mean
        location_drift["training_std"] = training_std
        location_drift["mean_deviation_pct"] = mean_deviation * 100
        location_drift["std_deviation_pct"] = std_deviation * 100

        # Drift thresholds
        MEAN_THRESHOLD = 0.30  # 30% deviation
        STD_THRESHOLD = 0.50  # 50% deviation

        drift_detected = (mean_deviation > MEAN_THRESHOLD) or (
            std_deviation > STD_THRESHOLD
        )

        location_drift["drift_detected"] = drift_detected
        location_drift["drift_severity"] = (
            "high"
            if mean_deviation > 0.5
            else "medium"
            if mean_deviation > 0.3
            else "low"
        )

        if drift_detected:
            location_drift["warnings"] = []
            if mean_deviation > MEAN_THRESHOLD:
                location_drift["warnings"].append(
                    f"Mean deviation {mean_deviation * 100:.1f}% exceeds threshold"
                )
            if std_deviation > STD_THRESHOLD:
                location_drift["warnings"].append(
                    f"Std deviation {std_deviation * 100:.1f}% exceeds threshold"
                )

        drift_report["locations"][f"location_{location}"] = location_drift

        if drift_detected:
            drift_report["overall_drift_detected"] = True

    # Save report
    with open(output_path, "w") as f:
        json.dump(drift_report, f, indent=2)

    # Print summary
    print("\nModel Drift Analysis")
    print("=" * 60)

    if drift_report["overall_drift_detected"]:
        print("⚠️  DRIFT DETECTED")
        for location, data in drift_report["locations"].items():
            if data.get("drift_detected"):
                print(f"\n{location}:")
                print(f"  Severity: {data['drift_severity']}")
                for warning in data.get("warnings", []):
                    print(f"  - {warning}")
    else:
        print("✅ No significant drift detected")

    print("=" * 60)
    print(f"\nDrift report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Check for model drift")
    parser.add_argument("--artifacts-dir", required=True, help="Artifacts directory")
    parser.add_argument("--output", default="drift-report.json", help="Output file")
    args = parser.parse_args()

    check_drift(args.artifacts_dir, args.output)


if __name__ == "__main__":
    main()
