"""
Prophet model creation and configuration.

This module handles the creation of Prophet models with
location-specific configurations based on data availability.
"""
from prophet import Prophet


def create_prophet_model(location: str, n_days: int, verbose: bool = True) -> Prophet:
    """
    Create a Prophet model with location-specific configuration.
    
    Args:
        location: Location identifier ('A', 'B', or 'C')
        n_days: Number of days of historical data available
        verbose: Whether to print configuration info
        
    Returns:
        Configured Prophet model (not yet fitted)
    """
    # Base configuration
    model = Prophet(
        daily_seasonality=False,  # We're dealing with daily aggregates
        weekly_seasonality=True,
        interval_width=0.95  # 95% confidence intervals
    )
    
    # For locations with <2 years of data, disable yearly seasonality
    # to avoid overfitting. Location C only has data from Sep 2024.
    if n_days < 730:  # Less than 2 years
        model.yearly_seasonality = False
        if verbose:
            print(f"Location {location}: Disabled yearly seasonality (only {n_days} days)")
    else:
        model.yearly_seasonality = True
        if verbose:
            print(f"Location {location}: Enabled yearly seasonality ({n_days} days)")
    
    return model
