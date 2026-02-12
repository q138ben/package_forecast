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
    # For locations with <2 years of data, disable yearly seasonality
    # to avoid overfitting. Location C only has data from Sep 2024.
    yearly_seasonality = n_days >= 730

    # Base configuration
    # Note: weekly_seasonality is implemented as a custom seasonality below
    # to allow sharper weekend patterns.
    model = Prophet(
        daily_seasonality=False,  # We're dealing with daily aggregates
        weekly_seasonality=False,
        yearly_seasonality=yearly_seasonality,
        seasonality_mode='multiplicative',
        interval_width=0.95  # 95% confidence intervals
    )

    # Add Swedish holidays to capture holiday effects on package volume.
    model.add_country_holidays(country_name='SE')

    # More flexible weekly seasonality to better capture near-zero weekends.
    model.add_seasonality(
        name='weekly',
        period=7,
        fourier_order=10
    )

    # Explicit weekend regressor to allow strong weekend effects.
    model.add_regressor(
        name='is_weekend',
        prior_scale=100.0,
        mode='multiplicative',
        standardize=False
    )

    # Separate Saturday/Sunday effects (useful when only Saturdays are near-zero).
    model.add_regressor(
        name='is_saturday',
        prior_scale=100.0,
        mode='multiplicative',
        standardize=False
    )
    model.add_regressor(
        name='is_sunday',
        prior_scale=100.0,
        mode='multiplicative',
        standardize=False
    )

    if verbose:
        if yearly_seasonality:
            print(f"Location {location}: Enabled yearly seasonality ({n_days} days)")
        else:
            print(f"Location {location}: Disabled yearly seasonality (only {n_days} days)")
        print(f"Location {location}: Added Swedish holidays")
        print(f"Location {location}: Added weekend regressors (multiplicative) + flexible weekly seasonality")

    return model
