"""
Visualization utilities for forecast analysis.

This module provides plotting functions for comparing forecasts
with actual data and visualizing model performance.
"""

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error


def plot_test_period_zoom(
    location: str,
    test_df: pd.DataFrame,
    forecast: pd.DataFrame,
    output_dir: str = "models",
    show: bool = False,
) -> str:
    """
    Create visualization showing test period comparison and future forecast.

    Args:
        location: Location identifier
        test_df: Test holdout data with 'ds' and 'y' columns
        forecast: Prophet forecast DataFrame with predictions
        output_dir: Directory to save plots
        show: Whether to display the plot (for notebooks)

    Returns:
        Path to saved plot file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    # Colors
    test_actual_color = "#E94F37"
    forecast_color = "#28A745"
    future_forecast_color = "#0066CC"
    ci_color = "#28A745"
    future_ci_color = "#0066CC"
    baseline_color = "#8E44AD"

    # Filter forecast to test period and future period
    test_forecast = forecast[forecast["ds"].isin(test_df["ds"])]
    future_forecast = forecast[forecast["ds"] > test_df["ds"].max()]

    # Actual test data
    ax.plot(
        test_df["ds"],
        test_df["y"],
        color=test_actual_color,
        linewidth=2,
        marker="o",
        markersize=4,
        label="Actual (Test)",
        alpha=0.9,
    )

    # Forecast for test period with CI
    ax.plot(
        test_forecast["ds"],
        test_forecast["yhat"],
        color=forecast_color,
        linewidth=2,
        marker="s",
        markersize=4,
        linestyle="--",
        label="Forecast (Test)",
    )
    ax.fill_between(
        test_forecast["ds"],
        test_forecast["yhat_lower"],
        test_forecast["yhat_upper"],
        color=ci_color,
        alpha=0.2,
    )

    # Future forecast period with CI
    if len(future_forecast) > 0:
        ax.plot(
            future_forecast["ds"],
            future_forecast["yhat"],
            color=future_forecast_color,
            linewidth=2,
            marker="s",
            markersize=4,
            label="Future Forecast",
        )
        ax.fill_between(
            future_forecast["ds"],
            future_forecast["yhat_lower"],
            future_forecast["yhat_upper"],
            color=future_ci_color,
            alpha=0.2,
            label="95% CI",
        )

    # Calculate and display metrics
    y_true = test_df["y"].values
    y_pred = test_forecast["yhat"].values
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    denominator = np.sum(np.abs(y_true))
    wape = (
        (np.sum(np.abs(y_true - y_pred)) / denominator * 100)
        if denominator != 0
        else np.nan
    )
    if {"yhat_lower", "yhat_upper"}.issubset(test_forecast.columns):
        lower = test_forecast["yhat_lower"].values
        upper = test_forecast["yhat_upper"].values
        coverage = np.mean((y_true >= lower) & (y_true <= upper)) * 100
    else:
        coverage = np.nan

    metrics_text = (
        f"Test Period Metrics:\n"
        f"  RMSE: {rmse:.2f}\n"
        f"  MAE: {mae:.2f}\n"
        f"  WAPE: {wape:.2f}%\n"
        f"  Coverage: {coverage:.1f}%"
    )
    ax.text(
        0.02,
        0.98,
        metrics_text,
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    ax.set_title(
        f"Location {location}: Test Period + Future Forecast",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Package Volume")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    # Adjust the interval based on total days shown
    total_days = (
        (future_forecast["ds"].max() - test_df["ds"].min()).days
        if len(future_forecast) > 0
        else len(test_df)
    )
    interval = max(5, total_days // 10)

    ax.text(
        0.02,
        0.98,
        metrics_text,
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    ax.set_title(
        f"Location {location}: Test Period - Actual vs Forecast",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Package Volume")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

    plt.tight_layout()

    # Save plot
    plot_file = output_path / f"location_{location}_forecast_plot.png"
    plt.savefig(plot_file, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close()

    print(f"  Plot saved: {plot_file}")
    return str(plot_file)
