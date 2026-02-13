"""
Model evaluation metrics and cross-validation utilities.

This module provides functions for evaluating forecast model performance
and running time series cross-validation.
"""
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_squared_error, mean_absolute_error

from src.models.prophet_model import create_prophet_model


# Metric keys used throughout the module
METRIC_KEYS = ['rmse', 'mae', 'wape', 'interval_coverage']


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                      lower: Optional[np.ndarray] = None,
                      upper: Optional[np.ndarray] = None) -> Dict[str, float]:
    """
    Calculate forecast evaluation metrics.
    
    Args:
        y_true: Actual values
        y_pred: Predicted values
        lower: Lower bounds of prediction intervals (optional)
        upper: Upper bounds of prediction intervals (optional)
        
    Returns:
        Dictionary with RMSE, MAE, WAPE, and interval coverage
    """
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    denominator = np.sum(np.abs(y_true))
    wape = (np.sum(np.abs(y_true - y_pred)) / denominator * 100) if denominator != 0 else np.nan
    
    # Calculate interval metrics if bounds are provided
    if lower is not None and upper is not None:
        valid_mask = ~np.isnan(lower) & ~np.isnan(upper)
        if np.any(valid_mask):
            coverage = np.mean((y_true[valid_mask] >= lower[valid_mask]) & 
                              (y_true[valid_mask] <= upper[valid_mask])) * 100
        else:
            coverage = float('nan')
    else:
        coverage = float('nan')
    
    return {
        'rmse': float(rmse),
        'mae': float(mae),
        'wape': float(wape),
        'interval_coverage': float(coverage)
    }


def seasonal_naive_forecast(train_df: pd.DataFrame, horizon: int,
                            seasonal_period: int = 7,
                            return_intervals: bool = False,
                            alpha: float = 0.05) -> Tuple[np.ndarray, ...]:
    """Generate a seasonal naive forecast for a given horizon."""
    if horizon <= 0:
        empty = np.array([], dtype=float)
        return (empty, empty, empty) if return_intervals else empty

    history = train_df['y'].values
    if history.size == 0:
        raise ValueError("Training data must contain at least one observation for baseline forecast.")

    if history.size >= seasonal_period and seasonal_period > 0:
        pattern = history[-seasonal_period:]
    else:
        pattern = history[-1:]

    reps = int(np.ceil(horizon / pattern.size))
    forecast_values = np.tile(pattern, reps)[:horizon].astype(float)

    if not return_intervals:
        return forecast_values

    if history.size > seasonal_period:
        residuals = history[seasonal_period:] - history[:-seasonal_period]
    else:
        residuals = np.array([], dtype=float)

    if residuals.size >= 2:
        lower_adj = np.percentile(residuals, (alpha / 2) * 100)
        upper_adj = np.percentile(residuals, (1 - alpha / 2) * 100)
        lower = forecast_values + lower_adj
        upper = forecast_values + upper_adj
    else:
        lower = np.full(forecast_values.shape, np.nan, dtype=float)
        upper = np.full(forecast_values.shape, np.nan, dtype=float)

    return forecast_values, lower.astype(float), upper.astype(float)


def evaluate_model(model: Prophet, test_df: pd.DataFrame) -> Dict[str, float]:
    """
    Evaluate Prophet model performance on test data.
    
    Args:
        model: Fitted Prophet model
        test_df: Test dataframe with 'ds' and 'y' columns
        
    Returns:
        Dictionary with evaluation metrics
    """
    forecast = model.predict(test_df)
    y_true = test_df['y'].values
    y_pred = forecast['yhat'].values
    
    lower = forecast['yhat_lower'].values if 'yhat_lower' in forecast.columns else None
    upper = forecast['yhat_upper'].values if 'yhat_upper' in forecast.columns else None
    
    return calculate_metrics(y_true, y_pred, lower, upper)


def evaluate_naive_baseline(train_df: pd.DataFrame, test_df: pd.DataFrame,
                            seasonal_period: int = 7) -> Dict[str, float]:
    """Evaluate a seasonal naive baseline on the test split."""
    if test_df.empty:
        return {key: float('nan') for key in METRIC_KEYS}

    y_true = test_df['y'].values
    y_pred, lower, upper = seasonal_naive_forecast(
        train_df, len(test_df), seasonal_period=seasonal_period, return_intervals=True
    )
    return calculate_metrics(y_true, y_pred, lower, upper)


def time_series_cv_split(df: pd.DataFrame, n_folds: int = 5, 
                         test_size: int = 30, gap: int = 0) -> List[Dict]:
    """
    Create time series cross-validation splits.
    
    Unlike regular k-fold CV, time series CV respects temporal ordering:
    - Training data is always before validation data
    - Each fold expands the training window
    
    Args:
        df: DataFrame with time series data (must have 'ds' column)
        n_folds: Number of CV folds
        test_size: Number of days in each validation fold
        gap: Number of days between train and validation (to prevent leakage)
        
    Returns:
        List of dicts containing train/val indices and date ranges
    """
    n_samples = len(df)
    cv_end_idx = n_samples - test_size
    min_train_size = test_size * 2
    available_for_cv = cv_end_idx - min_train_size - gap
    fold_step = available_for_cv // n_folds
    
    splits = []
    for fold in range(n_folds):
        train_end_idx = min_train_size + (fold * fold_step)
        val_start_idx = train_end_idx + gap
        val_end_idx = min(val_start_idx + test_size, cv_end_idx)
        
        if val_end_idx - val_start_idx < test_size // 2:
            continue
            
        splits.append({
            'fold': fold + 1,
            'train_idx': (0, train_end_idx),
            'val_idx': (val_start_idx, val_end_idx),
            'train_dates': (df.iloc[0]['ds'].strftime('%Y-%m-%d'), 
                          df.iloc[train_end_idx - 1]['ds'].strftime('%Y-%m-%d')),
            'val_dates': (df.iloc[val_start_idx]['ds'].strftime('%Y-%m-%d'),
                         df.iloc[val_end_idx - 1]['ds'].strftime('%Y-%m-%d')),
            'train_size': train_end_idx,
            'val_size': val_end_idx - val_start_idx
        })
    
    return splits


def _aggregate_metrics(metrics_list: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Aggregate a list of metrics dictionaries into avg and std.
    
    Args:
        metrics_list: List of metric dictionaries
        
    Returns:
        Dictionary with avg_* and std_* for each metric
    """
    result = {}
    for key in METRIC_KEYS:
        values = [m[key] for m in metrics_list]
        result[f'avg_{key}'] = float(np.nanmean(values))
        result[f'std_{key}'] = float(np.nanstd(values))
    return result


def run_time_series_cv(location: str, df: pd.DataFrame, 
                       n_folds: int = 5, test_size: int = 30,
                       verbose: bool = True) -> Dict:
    """
    Run time series cross-validation for a location.
    
    Args:
        location: Location identifier
        df: Full location dataframe (without final test holdout)
        n_folds: Number of CV folds
        test_size: Size of each validation fold
        verbose: Whether to print progress
        
    Returns:
        Dictionary with CV results and metrics per fold
    """
    splits = time_series_cv_split(df, n_folds=n_folds, test_size=test_size)
    
    if verbose:
        print(f"\n  Running {len(splits)}-fold Time Series Cross-Validation...")
    
    folds = []
    prophet_metrics_list = []
    baseline_metrics_list = []
    
    for split in splits:
        train_start, train_end = split['train_idx']
        val_start, val_end = split['val_idx']
        
        train_df = df.iloc[train_start:train_end].copy()
        val_df = df.iloc[val_start:val_end].copy()
        
        # Train and evaluate Prophet model
        model = create_prophet_model(location, len(train_df), verbose=False)
        model.fit(train_df)
        prophet_metrics = evaluate_model(model, val_df)
        
        # Evaluate baseline model
        baseline_metrics = evaluate_naive_baseline(train_df, val_df)
        
        folds.append({
            **split,
            'metrics': prophet_metrics,
            'baseline_metrics': baseline_metrics
        })
        
        prophet_metrics_list.append(prophet_metrics)
        baseline_metrics_list.append(baseline_metrics)
    
    # Aggregate metrics for both models
    prophet_agg = _aggregate_metrics(prophet_metrics_list)
    baseline_agg = _aggregate_metrics(baseline_metrics_list)
    
    # Build result with prefixed baseline metrics
    cv_results = {
        'n_folds': len(splits),
        'folds': folds,
        **prophet_agg,
        **{f'baseline_{k}': v for k, v in baseline_agg.items()}
    }
    
    return cv_results
