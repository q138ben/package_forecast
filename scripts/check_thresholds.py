"""
Check if model performance meets thresholds.
"""

import argparse
import json
import sys

import yaml


def check_thresholds(metrics_file: str, thresholds_file: str):
    """Check if metrics meet defined thresholds."""

    # Load metrics
    with open(metrics_file, "r") as f:
        evaluation = json.load(f)

    # Load thresholds
    try:
        with open(thresholds_file, "r") as f:
            thresholds = yaml.safe_load(f)
    except FileNotFoundError:
        # Use default thresholds if file doesn't exist
        thresholds = {
            "overall_score": {"min": 70},
            "per_location": {
                "wape": {"max": 20},
                "rmse": {"max": 100},
                "mae": {"max": 50},
            },
        }

    failures = []

    # Check overall score
    overall_score = evaluation.get("overall_score", 0)
    min_score = thresholds.get("overall_score", {}).get("min", 70)

    if overall_score < min_score:
        failures.append(f"Overall score {overall_score:.1f} below minimum {min_score}")

    # Check per-location metrics
    per_location_thresholds = thresholds.get("per_location", {})

    for location, loc_data in evaluation.get("locations", {}).items():
        basic_metrics = loc_data.get("basic_metrics", {})

        for metric, config in per_location_thresholds.items():
            value = basic_metrics.get(metric, float("inf"))

            if "max" in config and value > config["max"]:
                failures.append(
                    f"{location} {metric.upper()} {value:.2f} exceeds maximum {config['max']}"
                )

            if "min" in config and value < config["min"]:
                failures.append(
                    f"{location} {metric.upper()} {value:.2f} below minimum {config['min']}"
                )

    # Report results
    if failures:
        print("THRESHOLD CHECK FAILED")
        print("=" * 60)
        for failure in failures:
            print(f"  ❌ {failure}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("THRESHOLD CHECK PASSED")
        print("=" * 60)
        print(f"  ✅ Overall score: {overall_score:.1f}")
        print("  ✅ All location metrics within acceptable ranges")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Check model performance thresholds")
    parser.add_argument("--metrics", required=True, help="Evaluation metrics JSON file")
    parser.add_argument("--thresholds", required=True, help="Thresholds YAML file")
    args = parser.parse_args()

    check_thresholds(args.metrics, args.thresholds)


if __name__ == "__main__":
    main()
