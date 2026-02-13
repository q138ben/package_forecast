"""
Data cleaning and preprocessing utilities.

This module handles loading raw data from CSV and determining the valid
date range for each location. Location C has a "cold start" problem where
data only begins appearing around September 2024.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Tuple


def load_raw_data(filepath: str) -> pd.DataFrame:
    """
    Load the raw CSV data and perform basic cleaning.

    Args:
        filepath: Path to the CSV file

    Returns:
        DataFrame with parsed dates and numeric columns
    """
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])

    # Convert location columns to numeric, handling empty strings
    for col in ["location_A", "location_B", "location_C"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def find_valid_start_date(
    df: pd.DataFrame, location_col: str, min_consecutive_days: int = 7
) -> datetime:
    """
    Find the first date where a location starts having consistent data.

    For locations with sparse early history (like Location C), we want to
    identify when the data actually becomes reliable rather than training
    on years of mostly-null values.

    Args:
        df: DataFrame with date column
        location_col: Name of the location column
        min_consecutive_days: Minimum number of consecutive non-null days

    Returns:
        First valid date for this location
    """
    # Create a boolean series of non-null values
    non_null = df[location_col].notna()

    # Find the first index where we have min_consecutive_days in a row
    for i in range(len(df) - min_consecutive_days):
        if non_null.iloc[i : i + min_consecutive_days].all():
            return df["date"].iloc[i]

    # If no valid start found, return the first non-null date
    first_valid_idx = df[location_col].first_valid_index()
    if first_valid_idx is not None:
        return df["date"].iloc[first_valid_idx]

    # Fallback to first date if location has no data at all
    return df["date"].iloc[0]


def prepare_location_data(df: pd.DataFrame, location: str) -> Tuple[pd.DataFrame, Dict]:
    """
    Prepare data for a specific location, filtering to valid date range.

    Args:
        df: Raw dataframe
        location: Location identifier (e.g., 'A', 'B', 'C')

    Returns:
        Tuple of (filtered_df, metadata_dict)
    """
    location_col = f"location_{location}"

    # Find valid start date
    start_date = find_valid_start_date(df, location_col)

    # Filter to valid date range
    filtered = df[df["date"] >= start_date].copy()

    # Sort by date and interpolate any remaining gaps (if any)
    filtered = filtered.sort_values("date")
    filtered[location_col] = filtered[location_col].interpolate(method="linear")

    # Prepare Prophet format (requires 'ds' and 'y' columns)
    prophet_df = pd.DataFrame({"ds": filtered["date"], "y": filtered[location_col]})

    # Remove any remaining nulls
    prophet_df = prophet_df.dropna()

    metadata = {
        "location": location,
        "start_date": start_date,
        "end_date": filtered["date"].max(),
        "n_days": len(prophet_df),
        "mean_packages": prophet_df["y"].mean(),
        "std_packages": prophet_df["y"].std(),
    }

    return prophet_df, metadata
