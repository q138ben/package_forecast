"""
Data splitting utilities for time series forecasting.

This module handles train/test splitting and saving split information
for reproducibility.
"""

import json
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd


def split_train_test(
    df: pd.DataFrame, test_size: int = 30
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split time series data into train and test sets.

    Args:
        df: Full dataframe with time series data
        test_size: Number of days to hold out for testing

    Returns:
        Tuple of (train_df, test_df)
    """
    train_df = df.iloc[:-test_size].copy()
    test_df = df.iloc[-test_size:].copy()
    return train_df, test_df


def save_data_splits(
    location: str,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    cv_results: Dict,
    artifacts_dir: str = "artifacts",
) -> str:
    """
    Save train/test split and CV fold information for reproducibility.

    Args:
        location: Location identifier
        train_df: Training dataframe (excluding final test)
        test_df: Final test holdout dataframe
        cv_results: Cross-validation results with fold information
        output_dir: Directory to save splits

    Returns:
        Path to saved splits file
    """
    output_path = Path(artifacts_dir)
    output_path.mkdir(exist_ok=True)

    splits_info = {
        "location": location,
        "created_at": pd.Timestamp.now().isoformat(),
        "final_split": {
            "train": {
                "start_date": train_df.iloc[0]["ds"].strftime("%Y-%m-%d"),
                "end_date": train_df.iloc[-1]["ds"].strftime("%Y-%m-%d"),
                "n_samples": len(train_df),
            },
            "test": {
                "start_date": test_df.iloc[0]["ds"].strftime("%Y-%m-%d"),
                "end_date": test_df.iloc[-1]["ds"].strftime("%Y-%m-%d"),
                "n_samples": len(test_df),
            },
        },
        "cv_folds": cv_results["folds"],
    }

    # Save as JSON
    splits_file = output_path / f"location_{location}_splits.json"
    with open(splits_file, "w") as f:
        json.dump(splits_info, f, indent=2)

    # Also save train/test data as CSV for easy access
    train_file = output_path / f"location_{location}_train_data.csv"
    test_file = output_path / f"location_{location}_test_data.csv"

    train_df.to_csv(train_file, index=False)
    test_df.to_csv(test_file, index=False)

    return str(splits_file)


def load_data_splits(location: str, artifacts_dir: str = "artifacts") -> Dict:
    """
    Load saved data split information.

    Args:
        location: Location identifier
        output_dir: Directory where splits are saved

    Returns:
        Dictionary with split information
    """
    splits_file = Path(artifacts_dir) / f"location_{location}_splits.json"

    with open(splits_file, "r") as f:
        splits_info = json.load(f)

    return splits_info
