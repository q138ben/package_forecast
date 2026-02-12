"""
Data module for loading and splitting time series data.
"""
from src.data.splits import (
    split_train_test,
    save_data_splits,
    load_data_splits
)

__all__ = [
    'split_train_test',
    'save_data_splits',
    'load_data_splits'
]
