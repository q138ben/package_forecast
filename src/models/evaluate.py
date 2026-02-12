"""
Model evaluation metrics and cross-validation utilities.

This module provides functions for evaluating forecast model performance
and running time series cross-validation.
"""
from typing import Dict, List

import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error

from src.models.prophet_model import create_prophet_model


def evaluate_model(model: Prophet, test_df: pd.DataFrame) -> Dict[str, float]:
    """
    Evaluate model performance on test data.
    
    Args:
        model: Fitted Prophet model
        test_df: Test dataframe with 'ds' and 'y' columns
        
    Returns:
        Dictionary with RMSE and MAPE metrics
    """
    # Generate predictions for test period
    forecast = model.predict(test_df[['ds']])
    
    # Calculate metrics
    rmse = np.sqrt(mean_squared_error(test_df['y'], forecast['yhat']))
    mape = mean_absolute_percentage_error(test_df['y'], forecast['yhat']) * 100
    
    return {
        'rmse': float(rmse),
        'mape': float(mape)
    }


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculate forecast evaluation metrics.
    
    Args:
        y_true: Actual values
        y_pred: Predicted values
        
    Returns:
        Dictionary with RMSE and MAPE metrics
    """
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = mean_absolute_percentage_error(y_true, y_pred) * 100
    
    return {
        'rmse': float(rmse),
        'mape': float(mape)
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
        'avg_mape': 0.0,
        'std_rmse': 0.0,
        'std_mape': 0.0
    }
    
    all_rmse = []
    all_mape = []
    
    if verbose:
        print(f"\n  Running {len(splits)}-fold Time Series Cross-Validation...")
    
    for split in splits:
        fold = split['fold']
        train_start, train_end = split['train_idx']
        val_start, val_end = split['val_idx']
        
        train_df = df.iloc[train_start:train_end].copy()
        val_df = df.iloc[val_start:val_end].copy()
        
        # Train model on this fold
        model = create_prophet_model(location, len(train_df), verbose=False)
        model.fit(train_df)
        
        # Evaluate
        metrics = evaluate_model(model, val_df)
        
        fold_result = {
            **split,
            'metrics': metrics
        }
        cv_results['folds'].append(fold_result)
        
        all_rmse.append(metrics['rmse'])
        all_mape.append(metrics['mape'])
        
        if verbose:
            print(f"    Fold {fold}: Train {split['train_dates'][0]} to {split['train_dates'][1]} "
                  f"| Val {split['val_dates'][0]} to {split['val_dates'][1]} "
                  f"| RMSE: {metrics['rmse']:.2f} | MAPE: {metrics['mape']:.2f}%")
    
    # Calculate aggregate metrics
    cv_results['avg_rmse'] = float(np.mean(all_rmse))
    cv_results['avg_mape'] = float(np.mean(all_mape))
    cv_results['std_rmse'] = float(np.std(all_rmse))
    cv_results['std_mape'] = float(np.std(all_mape))
    
    if verbose:
        print(f"\n  CV Summary: RMSE = {cv_results['avg_rmse']:.2f} ± {cv_results['std_rmse']:.2f} | "
              f"MAPE = {cv_results['avg_mape']:.2f}% ± {cv_results['std_mape']:.2f}%")
    
    return cv_results
