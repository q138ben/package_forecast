"""
Generate evaluation plots for model performance.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def generate_plots(artifacts_dir: str, output_dir: str):
    """Generate evaluation visualizations."""
    artifacts_path = Path(artifacts_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    sns.set_style("whitegrid")

    for location in ["A", "B", "C"]:
        forecast_file = artifacts_path / f"location_{location}_forecast.csv"
        test_file = artifacts_path / f"location_{location}_test_data.csv"
        train_file = artifacts_path / f"location_{location}_train_data.csv"

        if not forecast_file.exists():
            continue

        forecast_df = pd.read_csv(forecast_file)
        forecast_df["ds"] = pd.to_datetime(forecast_df["ds"])

        # Create figure with multiple subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f"Location {location} Model Evaluation", fontsize=16)

        # Plot 1: Forecast with confidence intervals
        ax1 = axes[0, 0]
        ax1.plot(
            forecast_df["ds"], forecast_df["yhat"], "b-", label="Forecast", linewidth=2
        )
        ax1.fill_between(
            forecast_df["ds"],
            forecast_df["yhat_lower"],
            forecast_df["yhat_upper"],
            alpha=0.3,
            label="95% Confidence Interval",
        )

        # Add test data if available
        if test_file.exists():
            test_df = pd.read_csv(test_file)
            test_df["ds"] = pd.to_datetime(test_df["ds"])
            ax1.plot(
                test_df["ds"], test_df["y"], "ro-", label="Actual (Test)", markersize=4
            )

        ax1.set_xlabel("Date")
        ax1.set_ylabel("Packages")
        ax1.set_title("30-Day Forecast")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: Forecast distribution
        ax2 = axes[0, 1]
        ax2.hist(forecast_df["yhat"], bins=20, edgecolor="black", alpha=0.7)
        ax2.axvline(
            forecast_df["yhat"].mean(),
            color="r",
            linestyle="--",
            label=f"Mean: {forecast_df['yhat'].mean():.1f}",
        )
        ax2.set_xlabel("Forecast Value")
        ax2.set_ylabel("Frequency")
        ax2.set_title("Forecast Distribution")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Plot 3: Test performance (if test data available)
        if test_file.exists():
            ax3 = axes[1, 0]
            # Use only overlapping dates
            test_df = pd.read_csv(test_file)
            test_df["ds"] = pd.to_datetime(test_df["ds"])

            # Merge on date to get predictions for test period
            merged = test_df.merge(forecast_df[["ds", "yhat"]], on="ds", how="inner")

            if len(merged) > 0:
                ax3.scatter(merged["y"], merged["yhat"], alpha=0.6)
                ax3.plot(
                    [merged["y"].min(), merged["y"].max()],
                    [merged["y"].min(), merged["y"].max()],
                    "r--",
                    label="Perfect Prediction",
                )
                ax3.set_xlabel("Actual")
                ax3.set_ylabel("Predicted")
                ax3.set_title("Test Set: Actual vs Predicted")
                ax3.legend()
                ax3.grid(True, alpha=0.3)
            else:
                ax3.text(
                    0.5,
                    0.5,
                    "No overlapping test data",
                    ha="center",
                    va="center",
                    transform=ax3.transAxes,
                )
        else:
            axes[1, 0].text(
                0.5,
                0.5,
                "Test data not available",
                ha="center",
                va="center",
                transform=axes[1, 0].transAxes,
            )

        # Plot 4: Residuals (if test data available)
        if test_file.exists() and len(merged) > 0:
            ax4 = axes[1, 1]
            residuals = merged["y"] - merged["yhat"]
            ax4.scatter(range(len(residuals)), residuals, alpha=0.6)
            ax4.axhline(0, color="r", linestyle="--")
            ax4.set_xlabel("Observation")
            ax4.set_ylabel("Residual")
            ax4.set_title("Residual Plot")
            ax4.grid(True, alpha=0.3)
        else:
            axes[1, 1].text(
                0.5,
                0.5,
                "Residuals not available",
                ha="center",
                va="center",
                transform=axes[1, 1].transAxes,
            )

        plt.tight_layout()
        plt.savefig(
            output_path / f"location_{location}_evaluation.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

        print(f"Generated evaluation plots for location {location}")

    print(f"\nAll plots saved to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Generate evaluation plots")
    parser.add_argument("--artifacts-dir", required=True, help="Artifacts directory")
    parser.add_argument("--output", default="evaluation-plots", help="Output directory")
    args = parser.parse_args()

    generate_plots(args.artifacts_dir, args.output)


if __name__ == "__main__":
    main()
