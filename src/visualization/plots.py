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

from src.models.evaluate import seasonal_naive_forecast


def plot_forecast_vs_actual(location: str, train_df: pd.DataFrame, test_df: pd.DataFrame,
                            forecast: pd.DataFrame, output_dir: str = 'models',
                            show: bool = False) -> str:
    """
    Create visualization comparing forecast to actual data.
    
    Generates two plots:
    1. Full view: Historical data + test period + future forecast
    2. Zoomed view: Test period comparison (actual vs predicted)
    
    Args:
        location: Location identifier
        train_df: Training data with 'ds' and 'y' columns
        test_df: Test holdout data with 'ds' and 'y' columns
        forecast: Prophet forecast DataFrame with predictions
        output_dir: Directory to save plots
        show: Whether to display the plot (for notebooks)
        
    Returns:
        Path to saved plot file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Colors
    hist_color = '#2E86AB'
    test_actual_color = '#E94F37'
    forecast_color = '#28A745'
    ci_color = '#28A745'
    baseline_color = '#8E44AD'
    
    # Compute baseline forecast for test + future period
    horizon = len(test_df) + len(forecast[forecast['ds'] > test_df['ds'].max()])
    baseline_pred, baseline_lower, baseline_upper = seasonal_naive_forecast(
        train_df, horizon, return_intervals=True
    )
    
    # Split baseline into test and future periods
    baseline_test_pred = baseline_pred[:len(test_df)]
    baseline_test_lower = baseline_lower[:len(test_df)]
    baseline_test_upper = baseline_upper[:len(test_df)]
    baseline_future_pred = baseline_pred[len(test_df):]
    baseline_future_lower = baseline_lower[len(test_df):]
    baseline_future_upper = baseline_upper[len(test_df):]
    
    # --- Plot 1: Full View ---
    ax1 = axes[0]
    
    # Historical training data
    ax1.plot(train_df['ds'], train_df['y'], 
             color=hist_color, linewidth=1, label='Historical (Train)', alpha=0.8)
    
    # Test actual data
    ax1.plot(test_df['ds'], test_df['y'], 
             color=test_actual_color, linewidth=2, label='Actual (Test)', alpha=0.9)
    
    # Forecast for test period
    test_forecast = forecast[forecast['ds'].isin(test_df['ds'])]
    ax1.plot(test_forecast['ds'], test_forecast['yhat'], 
             color=forecast_color, linewidth=2, linestyle='--', label='Forecast (Test)')
    
    # Future forecast (beyond test data)
    future_forecast = forecast[forecast['ds'] > test_df['ds'].max()]
    if len(future_forecast) > 0:
        ax1.plot(future_forecast['ds'], future_forecast['yhat'], 
                 color=forecast_color, linewidth=2, label='Future Forecast')
        ax1.fill_between(future_forecast['ds'], 
                        future_forecast['yhat_lower'], 
                        future_forecast['yhat_upper'],
                        color=ci_color, alpha=0.2, label='95% CI')
    
    # Baseline forecast overlay
    ax1.plot(test_df['ds'], baseline_test_pred, 
             color=baseline_color, linewidth=1.5, linestyle=':', 
             marker='^', markersize=3, label='Baseline (Seasonal Naive)', alpha=0.8)
    if len(future_forecast) > 0:
        ax1.plot(future_forecast['ds'], baseline_future_pred, 
                 color=baseline_color, linewidth=1.5, linestyle=':', 
                 marker='^', markersize=3, alpha=0.8)
    
    # Mark test period
    ax1.axvline(x=test_df['ds'].min(), color='gray', linestyle=':', alpha=0.7)
    ax1.axvline(x=test_df['ds'].max(), color='gray', linestyle=':', alpha=0.7)
    
    ax1.set_title(f'Location {location}: Full Forecast View', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Package Volume')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # --- Plot 2: Test Period Zoom ---
    ax2 = axes[1]
    
    # Actual test data
    ax2.plot(test_df['ds'], test_df['y'], 
             color=test_actual_color, linewidth=2, marker='o', markersize=4,
             label='Actual', alpha=0.9)
    
    # Forecast for test period with CI
    ax2.plot(test_forecast['ds'], test_forecast['yhat'], 
             color=forecast_color, linewidth=2, marker='s', markersize=4,
             linestyle='--', label='Forecast')
    ax2.fill_between(test_forecast['ds'], 
                    test_forecast['yhat_lower'], 
                    test_forecast['yhat_upper'],
                    color=ci_color, alpha=0.2, label='95% CI')
    
    # Baseline forecast overlay on test period
    ax2.plot(test_df['ds'], baseline_test_pred, 
             color=baseline_color, linewidth=1.5, linestyle=':', 
             marker='^', markersize=4, label='Baseline', alpha=0.8)
    ax2.fill_between(test_df['ds'], baseline_test_lower, baseline_test_upper,
                    color=baseline_color, alpha=0.1)
    
    # Calculate and display metrics
    y_true = test_df['y'].values
    y_pred = test_forecast['yhat'].values
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    denominator = np.sum(np.abs(y_true))
    wape = (np.sum(np.abs(y_true - y_pred)) / denominator * 100) if denominator != 0 else np.nan
    if {'yhat_lower', 'yhat_upper'}.issubset(test_forecast.columns):
        lower = test_forecast['yhat_lower'].values
        upper = test_forecast['yhat_upper'].values
        coverage = np.mean((y_true >= lower) & (y_true <= upper)) * 100
    else:
        coverage = np.nan
    
    # Calculate baseline metrics
    baseline_rmse = np.sqrt(mean_squared_error(y_true, baseline_test_pred))
    baseline_mae = mean_absolute_error(y_true, baseline_test_pred)
    baseline_wape = (np.sum(np.abs(y_true - baseline_test_pred)) / denominator * 100) if denominator != 0 else np.nan
    baseline_coverage = np.mean((y_true >= baseline_test_lower) & (y_true <= baseline_test_upper)) * 100
    baseline_width = np.mean(baseline_test_upper - baseline_test_lower)

    metrics_text = (
        f'Prophet:\n'
        f'  RMSE: {rmse:.2f}\n'
        f'  MAE: {mae:.2f}\n'
        f'  WAPE: {wape:.2f}%\n'
        f'  Coverage: {coverage:.1f}%\n\n'
        f'Baseline:\n'
        f'  RMSE: {baseline_rmse:.2f}\n'
        f'  MAE: {baseline_mae:.2f}\n'
        f'  WAPE: {baseline_wape:.2f}%\n'
        f'  Coverage: {baseline_coverage:.1f}%'
    )
    ax2.text(0.02, 0.98, metrics_text, transform=ax2.transAxes, fontsize=11,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax2.set_title(f'Location {location}: Test Period (Last 30 Days) - Actual vs Forecast', 
                  fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Package Volume')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=5))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save plot
    plot_file = output_path / f'location_{location}_forecast_plot.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    else:
        plt.close()
    
    print(f"  Plot saved: {plot_file}")
    return str(plot_file)


def plot_cv_results(cv_results: dict, location: str, output_dir: str = 'models',
                    show: bool = False) -> str:
    """
    Visualize cross-validation results across folds.
    
    Args:
        cv_results: Dictionary with CV fold results
        location: Location identifier
        output_dir: Directory to save plots
        show: Whether to display the plot
        
    Returns:
        Path to saved plot file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    folds = cv_results['folds']
    fold_nums = [f['fold'] for f in folds]
    rmse_values = [f['metrics']['rmse'] for f in folds]
    mae_values = [f['metrics']['mae'] for f in folds]
    wape_values = [f['metrics']['wape'] for f in folds]
    coverage_values = [f['metrics']['interval_coverage'] for f in folds]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    # RMSE by fold
    ax1 = axes[0]
    bars1 = ax1.bar(fold_nums, rmse_values, color='#2E86AB', alpha=0.8)
    ax1.axhline(y=cv_results['avg_rmse'], color='red', linestyle='--', 
                label=f"Mean: {cv_results['avg_rmse']:.2f}")
    ax1.fill_between([0.5, len(fold_nums) + 0.5], 
                     cv_results['avg_rmse'] - cv_results['std_rmse'],
                     cv_results['avg_rmse'] + cv_results['std_rmse'],
                     color='red', alpha=0.1, label=f"±1 Std: {cv_results['std_rmse']:.2f}")
    ax1.set_xlabel('Fold')
    ax1.set_ylabel('RMSE')
    ax1.set_title(f'Location {location}: RMSE by CV Fold')
    ax1.legend()
    ax1.set_xticks(fold_nums)
    
    # MAE by fold
    ax2 = axes[1]
    bars2 = ax2.bar(fold_nums, mae_values, color='#28A745', alpha=0.8)
    ax2.axhline(
        y=cv_results['avg_mae'],
        color='red',
        linestyle='--',
        label=f"Mean: {cv_results['avg_mae']:.2f}"
    )
    ax2.fill_between(
        [0.5, len(fold_nums) + 0.5],
        cv_results['avg_mae'] - cv_results['std_mae'],
        cv_results['avg_mae'] + cv_results['std_mae'],
        color='red',
        alpha=0.1,
        label=f"±1 Std: {cv_results['std_mae']:.2f}"
    )
    ax2.set_xlabel('Fold')
    ax2.set_ylabel('MAE')
    ax2.set_title(f'Location {location}: MAE by CV Fold')
    ax2.legend()
    ax2.set_xticks(fold_nums)

    # WAPE by fold with coverage overlay
    ax3 = axes[2]
    bars3 = ax3.bar(fold_nums, wape_values, color='#1ABC9C', alpha=0.8, label='WAPE')
    ax3.axhline(
        y=cv_results['avg_wape'],
        color='red',
        linestyle='--',
        label=f"Mean: {cv_results['avg_wape']:.2f}%"
    )
    ax3.fill_between(
        [0.5, len(fold_nums) + 0.5],
        cv_results['avg_wape'] - cv_results['std_wape'],
        cv_results['avg_wape'] + cv_results['std_wape'],
        color='red',
        alpha=0.1,
        label=f"±1 Std: {cv_results['std_wape']:.2f}%"
    )
    ax3.set_xlabel('Fold')
    ax3.set_ylabel('WAPE (%)')
    ax3.set_title(f'Location {location}: WAPE & Coverage by CV Fold')
    ax3.set_xticks(fold_nums)
    ax3.legend(loc='upper left')

    ax3b = ax3.twinx()
    ax3b.plot(
        fold_nums,
        coverage_values,
        color='#E67E22',
        marker='o',
        linewidth=2,
        label='Coverage (%)'
    )
    ax3b.set_ylabel('Coverage (%)')
    ax3b.set_ylim(0, 100)
    ax3b.legend(loc='upper right')
    
    plt.tight_layout()
    
    plot_file = output_path / f'location_{location}_cv_results.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return str(plot_file)


def plot_all_locations_comparison(results: dict, output_dir: str = 'models',
                                   show: bool = False) -> str:
    """
    Create a comparison plot of metrics across all locations.
    
    Args:
        results: Dictionary with results for all locations
        output_dir: Directory to save plots
        show: Whether to display the plot
        
    Returns:
        Path to saved plot file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    locations = []
    cv_rmse = []
    cv_mae = []
    cv_wape = []
    test_rmse = []
    test_mae = []
    test_wape = []
    test_coverage = []
    
    for loc, res in results.items():
        if 'error' not in res:
            locations.append(loc)
            cv_rmse.append(res['cv_metrics']['avg_rmse'])
            cv_mae.append(res['cv_metrics']['avg_mae'])
            cv_wape.append(res['cv_metrics']['avg_wape'])
            test_rmse.append(res['test_metrics']['rmse'])
            test_mae.append(res['test_metrics']['mae'])
            test_wape.append(res['test_metrics']['wape'])
            test_coverage.append(res['test_metrics']['interval_coverage'])
    
    x = np.arange(len(locations))
    width = 0.35
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    # RMSE comparison
    ax1 = axes[0]
    bars1 = ax1.bar(x - width/2, cv_rmse, width, label='CV (avg)', color='#2E86AB', alpha=0.8)
    bars2 = ax1.bar(x + width/2, test_rmse, width, label='Test', color='#E94F37', alpha=0.8)
    ax1.set_xlabel('Location')
    ax1.set_ylabel('RMSE')
    ax1.set_title('RMSE Comparison: CV vs Test')
    ax1.set_xticks(x)
    ax1.set_xticklabels(locations)
    ax1.legend()
    
    # MAE comparison
    ax2 = axes[1]
    bars3 = ax2.bar(x - width/2, cv_mae, width, label='CV (avg)', color='#2E86AB', alpha=0.8)
    bars4 = ax2.bar(x + width/2, test_mae, width, label='Test', color='#E94F37', alpha=0.8)
    ax2.set_xlabel('Location')
    ax2.set_ylabel('MAE')
    ax2.set_title('MAE Comparison: CV vs Test')
    ax2.set_xticks(x)
    ax2.set_xticklabels(locations)
    ax2.legend()

    # WAPE comparison with coverage overlay
    ax3 = axes[2]
    bars5 = ax3.bar(x - width/2, cv_wape, width, label='CV (avg)', color='#2E86AB', alpha=0.8)
    bars6 = ax3.bar(x + width/2, test_wape, width, label='Test', color='#E94F37', alpha=0.8)
    ax3.set_xlabel('Location')
    ax3.set_ylabel('WAPE (%)')
    ax3.set_title('WAPE Comparison: CV vs Test')
    ax3.set_xticks(x)
    ax3.set_xticklabels(locations)
    ax3.legend(loc='upper left')

    ax3b = ax3.twinx()
    ax3b.plot(x, test_coverage, color='#1ABC9C', marker='o', linewidth=2, label='Test Coverage')
    ax3b.set_ylabel('Coverage (%)')
    ax3b.set_ylim(0, 100)
    ax3b.legend(loc='upper right')
    
    plt.tight_layout()
    
    plot_file = output_path / 'all_locations_comparison.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return str(plot_file)
