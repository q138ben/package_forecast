"""
Evaluate trained models comprehensively.
"""

import argparse
import json
from pathlib import Path

import pandas as pd


def evaluate_models(artifacts_dir: str, output_path: str):
    """Run comprehensive model evaluation."""
    artifacts_path = Path(artifacts_dir)

    evaluation = {"timestamp": pd.Timestamp.now().isoformat(), "locations": {}}

    for location in ["A", "B", "C"]:
        results_file = artifacts_path / f"location_{location}_results.json"
        forecast_file = artifacts_path / f"location_{location}_forecast.csv"
        test_file = artifacts_path / f"location_{location}_test_data.csv"

        if not all([results_file.exists(), forecast_file.exists(), test_file.exists()]):
            print(f"Skipping location {location} - missing files")
            continue

        # Load data
        with open(results_file, "r") as f:
            results = json.load(f)

        forecast_df = pd.read_csv(forecast_file)
        test_df = pd.read_csv(test_file)

        # Calculate additional metrics
        location_eval = {
            "basic_metrics": results.get("test_metrics", {}),
            "cv_metrics": results.get("cv_metrics", {}),
            "forecast_coverage": {
                "forecast_days": len(forecast_df),
                "expected_days": 30,
                "coverage_pct": (len(forecast_df) / 30) * 100,
            },
            "forecast_characteristics": {
                "mean_forecast": float(forecast_df["forecast"].mean()),
                "std_forecast": float(forecast_df["forecast"].std()),
                "min_forecast": float(forecast_df["forecast"].min()),
                "max_forecast": float(forecast_df["forecast"].max()),
            },
            "test_characteristics": {
                "test_days": len(test_df),
                "mean_actual": float(test_df["y"].mean()),
                "std_actual": float(test_df["y"].std()),
            },
        }

        # Check for anomalies in forecast
        forecast_values = forecast_df["forecast"].values
        location_eval["quality_checks"] = {
            "has_negatives": bool((forecast_values < 0).any()),
            "has_nans": bool(pd.isna(forecast_values).any()),
            "reasonable_range": bool(
                (forecast_values >= 0).all() and (forecast_values < 10000).all()
            ),
        }

        evaluation["locations"][f"location_{location}"] = location_eval

    # Calculate overall evaluation score
    overall_score = 0
    total_locations = len(evaluation["locations"])

    for loc_eval in evaluation["locations"].values():
        # Score based on WAPE (lower is better)
        wape = loc_eval["basic_metrics"].get("wape", 100)
        if wape < 10:
            overall_score += 100
        elif wape < 15:
            overall_score += 80
        elif wape < 20:
            overall_score += 60
        else:
            overall_score += 40

    evaluation["overall_score"] = (
        overall_score / total_locations if total_locations > 0 else 0
    )
    evaluation["evaluation_status"] = (
        "excellent"
        if evaluation["overall_score"] >= 80
        else "good"
        if evaluation["overall_score"] >= 70
        else "acceptable"
        if evaluation["overall_score"] >= 60
        else "poor"
    )

    # Save evaluation
    with open(output_path, "w") as f:
        json.dump(evaluation, f, indent=2)

    print(f"\nEvaluation completed for {total_locations} locations")
    print(f"Overall Score: {evaluation['overall_score']:.1f}/100")
    print(f"Status: {evaluation['evaluation_status'].upper()}")
    print(f"Evaluation saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained models")
    parser.add_argument("--artifacts-dir", required=True, help="Artifacts directory")
    parser.add_argument(
        "--output", default="evaluation-report.json", help="Output file"
    )
    args = parser.parse_args()

    evaluate_models(args.artifacts_dir, args.output)


if __name__ == "__main__":
    main()
