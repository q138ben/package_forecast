"""
Model evaluation metrics and cross-validation utilities.

This module provides functions for evaluating forecast model performance
and running time series cross-validation.
"""
from typing import Dict, List

import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_squared_error, mean_absolute_error

from src.models.prophet_model import create_prophet_model


def _add_is_weekend(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['ds'] = pd.to_datetime(df['ds'])
    weekday = df['ds'].dt.weekday
    df['is_weekend'] = (weekday >= 5).astype(int)
    df['is_saturday'] = (weekday == 5).astype(int)
    df['is_sunday'] = (weekday == 6).astype(int)
    return df


def _prepare_prophet_predict_df(model: Prophet, df: pd.DataFrame) -> pd.DataFrame:
    """Prepare a dataframe for Prophet predict() including required regressors."""
    predict_df = df.copy()
    predict_df['ds'] = pd.to_datetime(predict_df['ds'])

    extra_regressors = getattr(model, 'extra_regressors', {}) or {}
    required = list(extra_regressors.keys())
    for regressor_name in required:
        if regressor_name in predict_df.columns:
            continue
        if regressor_name in {'is_weekend', 'is_saturday', 'is_sunday'}:
            predict_df = _add_is_weekend(predict_df)
            continue
        raise ValueError(
            f"Missing required regressor column '{regressor_name}' for Prophet predict()."
        )

    cols = ['ds'] + required
    return predict_df[cols]


def evaluate_model(model: Prophet, test_df: pd.DataFrame) -> Dict[str, float]:
    """
    Evaluate model performance on test data.
    
    Args:
        model: Fitted Prophet model
        test_df: Test dataframe with 'ds' and 'y' columns
        
    Returns:
        Dictionary with RMSE, MAE, WAPE, and interval coverage metrics
    """
    # Generate predictions for test period
    predict_df = _prepare_prophet_predict_df(model, test_df)
    forecast = model.predict(predict_df)
    
    # Calculate metrics
    y_true = test_df['y'].values
    y_pred = forecast['yhat'].values
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    denominator = np.sum(np.abs(y_true))
    wape = (np.sum(np.abs(y_true - y_pred)) / denominator * 100) if denominator != 0 else np.nan

    if {'yhat_lower', 'yhat_upper'}.issubset(forecast.columns):
        lower = forecast['yhat_lower'].values
        upper = forecast['yhat_upper'].values
        coverage = np.mean((y_true >= lower) & (y_true <= upper)) * 100
        avg_interval_width = float(np.mean(upper - lower))
    else:
        coverage = np.nan
        avg_interval_width = np.nan
    
    return {
        'rmse': float(rmse),
        'mae': float(mae),
        'wape': float(wape),
        'interval_coverage': float(coverage),
        'avg_interval_width': float(avg_interval_width)
    }


def seasonal_naive_forecast(train_df: pd.DataFrame, horizon: int,
                            seasonal_period: int = 7,
                            return_intervals: bool = False,
                            alpha: float = 0.05):
    """Generate a seasonal naive forecast for a given horizon."""
    if horizon <= 0:
        if return_intervals:
            empty = np.array([], dtype=float)
            return empty, empty, empty
        return np.array([], dtype=float)

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


def evaluate_naive_baseline(train_df: pd.DataFrame, test_df: pd.DataFrame,
                            seasonal_period: int = 7) -> Dict[str, float]:
    """Evaluate a seasonal naive baseline on the test split."""
    if test_df.empty:
        return {
            'rmse': float('nan'),
            'mae': float('nan'),
            'wape': float('nan'),
            'interval_coverage': float('nan'),
            'avg_interval_width': float('nan')
        }

    y_true = test_df['y'].values
    y_pred, lower, upper = seasonal_naive_forecast(
        train_df,
        len(test_df),
        seasonal_period=seasonal_period,
        return_intervals=True
    )
    metrics = calculate_metrics(y_true, y_pred)
    valid_mask = ~np.isnan(lower) & ~np.isnan(upper)
    if np.any(valid_mask):
        coverage = np.mean((y_true[valid_mask] >= lower[valid_mask]) & (y_true[valid_mask] <= upper[valid_mask])) * 100
        interval_width = np.mean(upper[valid_mask] - lower[valid_mask])
        metrics['interval_coverage'] = float(coverage)
        metrics['avg_interval_width'] = float(interval_width)
    else:
        metrics['interval_coverage'] = float('nan')
        metrics['avg_interval_width'] = float('nan')
    return metrics


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculate forecast evaluation metrics.
    
    Args:
        y_true: Actual values
        y_pred: Predicted values
        
    Returns:
        Dictionary with RMSE, MAE, and WAPE metrics
    """
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    denominator = np.sum(np.abs(y_true))
    wape = (np.sum(np.abs(y_true - y_pred)) / denominator * 100) if denominator != 0 else np.nan
    
    return {
        'rmse': float(rmse),
        'mae': float(mae),
        'wape': float(wape)
    }


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
    
    # Reserve last test_size days for final holdout test
    # CV is done on the remaining data
    cv_end_idx = n_samples - test_size
    
    # Calculate minimum training size (at least 2x test_size)
    min_train_size = test_size * 2
    
    # Calculate the step size between folds
    available_for_cv = cv_end_idx - min_train_size - gap
    fold_step = available_for_cv // n_folds
    
    splits = []
    
    for fold in range(n_folds):
        # Training end index grows with each fold
        train_end_idx = min_train_size + (fold * fold_step)
        
        # Validation starts after the gap
        val_start_idx = train_end_idx + gap
        val_end_idx = min(val_start_idx + test_size, cv_end_idx)
        
        # Ensure we have enough validation data
        if val_end_idx - val_start_idx < test_size // 2:
            continue
            
        split_info = {
            'fold': fold + 1,
            'train_idx': (0, train_end_idx),
            'val_idx': (val_start_idx, val_end_idx),
            'train_dates': (df.iloc[0]['ds'].strftime('%Y-%m-%d'), 
                          df.iloc[train_end_idx - 1]['ds'].strftime('%Y-%m-%d')),
            'val_dates': (df.iloc[val_start_idx]['ds'].strftime('%Y-%m-%d'),
                         df.iloc[val_end_idx - 1]['ds'].strftime('%Y-%m-%d')),
            'train_size': train_end_idx,
            'val_size': val_end_idx - val_start_idx
        }
        splits.append(split_info)
    
    return splits


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
    
    cv_results = {
        'n_folds': len(splits),
        'folds': [],
        'avg_rmse': 0.0,
        'avg_mae': 0.0,
        'avg_wape': 0.0,
        'avg_interval_coverage': 0.0,
        'avg_interval_width': 0.0,
        'std_rmse': 0.0,
        'std_mae': 0.0,
        'std_wape': 0.0,
        'std_interval_coverage': 0.0,
        'std_interval_width': 0.0,
        'baseline_avg_rmse': 0.0,
        'baseline_avg_mae': 0.0,
        'baseline_avg_wape': 0.0,
        'baseline_avg_interval_coverage': 0.0,
        'baseline_avg_interval_width': 0.0,
        'baseline_std_rmse': 0.0,
        'baseline_std_mae': 0.0,
        'baseline_std_wape': 0.0,
        'baseline_std_interval_coverage': 0.0,
        'baseline_std_interval_width': 0.0
    }
    
    all_rmse = []
    all_mae = []
    all_wape = []
    all_cov = []
    all_width = []
    baseline_rmse = []
    baseline_mae = []
    baseline_wape = []
    baseline_cov = []
    baseline_width = []
    
    if verbose:
        print(f"\n  Running {len(splits)}-fold Time Series Cross-Validation...")
    
    for split in splits:
        fold = split['fold']
        train_start, train_end = split['train_idx']
        val_start, val_end = split['val_idx']
        
        train_df = df.iloc[train_start:train_end].copy()
        val_df = df.iloc[val_start:val_end].copy()

        # Add derived regressors used by the model
        train_df = _add_is_weekend(train_df)
        val_df = _add_is_weekend(val_df)
        
        # Train model on this fold
        model = create_prophet_model(location, len(train_df), verbose=False)
        model.fit(train_df)
        
        # Evaluate
        metrics = evaluate_model(model, val_df)
        baseline_metrics = evaluate_naive_baseline(train_df, val_df)
        
        fold_result = {
            **split,
            'metrics': metrics,
            'baseline_metrics': baseline_metrics
        }
        cv_results['folds'].append(fold_result)
        
        all_rmse.append(metrics['rmse'])
        all_mae.append(metrics['mae'])
        all_wape.append(metrics['wape'])
        all_cov.append(metrics['interval_coverage'])
        all_width.append(metrics['avg_interval_width'])
        baseline_rmse.append(baseline_metrics['rmse'])
        baseline_mae.append(baseline_metrics['mae'])
        baseline_wape.append(baseline_metrics['wape'])
        baseline_cov.append(baseline_metrics['interval_coverage'])
        baseline_width.append(baseline_metrics['avg_interval_width'])
        
        if verbose:
            print(f"    Fold {fold}: Train {split['train_dates'][0]} to {split['train_dates'][1]} "
                  f"| Val {split['val_dates'][0]} to {split['val_dates'][1]} "
                  f"| RMSE: {metrics['rmse']:.2f} | MAE: {metrics['mae']:.2f} "
                  f"| WAPE: {metrics['wape']:.2f}% | Coverage: {metrics['interval_coverage']:.1f}% "
                  f"| Baseline RMSE: {baseline_metrics['rmse']:.2f} | Baseline WAPE: {baseline_metrics['wape']:.2f}% "
                  f"| Baseline Coverage: {baseline_metrics['interval_coverage']:.1f}%")
    
    if not all_rmse:
        nan_values = {
            'avg_rmse': float('nan'),
            'avg_mae': float('nan'),
            'avg_wape': float('nan'),
            'avg_interval_coverage': float('nan'),
            'avg_interval_width': float('nan'),
            'std_rmse': float('nan'),
            'std_mae': float('nan'),
            'std_wape': float('nan'),
            'std_interval_coverage': float('nan'),
            'std_interval_width': float('nan'),
            'baseline_avg_rmse': float('nan'),
            'baseline_avg_mae': float('nan'),
            'baseline_avg_wape': float('nan'),
            'baseline_avg_interval_coverage': float('nan'),
            'baseline_avg_interval_width': float('nan'),
            'baseline_std_rmse': float('nan'),
            'baseline_std_mae': float('nan'),
            'baseline_std_wape': float('nan'),
            'baseline_std_interval_coverage': float('nan'),
            'baseline_std_interval_width': float('nan')
        }
        cv_results.update(nan_values)
        return cv_results

    # Calculate aggregate metrics
    cv_results['avg_rmse'] = float(np.mean(all_rmse))
    cv_results['avg_mae'] = float(np.mean(all_mae))
    cv_results['avg_wape'] = float(np.nanmean(all_wape))
    cv_results['avg_interval_coverage'] = float(np.nanmean(all_cov))
    cv_results['avg_interval_width'] = float(np.nanmean(all_width))
    cv_results['std_rmse'] = float(np.std(all_rmse))
    cv_results['std_mae'] = float(np.std(all_mae))
    cv_results['std_wape'] = float(np.nanstd(all_wape))
    cv_results['std_interval_coverage'] = float(np.nanstd(all_cov))
    cv_results['std_interval_width'] = float(np.nanstd(all_width))
    cv_results['baseline_avg_rmse'] = float(np.mean(baseline_rmse))
    cv_results['baseline_avg_mae'] = float(np.mean(baseline_mae))
    cv_results['baseline_avg_wape'] = float(np.nanmean(baseline_wape))
    cv_results['baseline_avg_interval_coverage'] = float(np.nanmean(baseline_cov))
    cv_results['baseline_avg_interval_width'] = float(np.nanmean(baseline_width))
    cv_results['baseline_std_rmse'] = float(np.std(baseline_rmse))
    cv_results['baseline_std_mae'] = float(np.std(baseline_mae))
    cv_results['baseline_std_wape'] = float(np.nanstd(baseline_wape))
    cv_results['baseline_std_interval_coverage'] = float(np.nanstd(baseline_cov))
    cv_results['baseline_std_interval_width'] = float(np.nanstd(baseline_width))
    
    if verbose:
        print(
            f"\n  CV Summary: RMSE = {cv_results['avg_rmse']:.2f} ± {cv_results['std_rmse']:.2f} | "
            f"MAE = {cv_results['avg_mae']:.2f} ± {cv_results['std_mae']:.2f} | "
            f"WAPE = {cv_results['avg_wape']:.2f}% ± {cv_results['std_wape']:.2f}% | "
            f"Coverage = {cv_results['avg_interval_coverage']:.1f}% ± {cv_results['std_interval_coverage']:.1f}% | "
            f"Baseline RMSE = {cv_results['baseline_avg_rmse']:.2f} ± {cv_results['baseline_std_rmse']:.2f} | "
            f"Baseline Coverage = {cv_results['baseline_avg_interval_coverage']:.1f}% ± {cv_results['baseline_std_interval_coverage']:.1f}%"
        )
    
    return cv_results
