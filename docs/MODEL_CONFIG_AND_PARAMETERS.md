# Forecast Model Parameters & Configuration (Prophet)

This document explains the parameters and configuration used for the forecasting models in this project (Prophet), and outlines additional options that can be added to improve performance.

---

## Summary of approach

- **One Prophet model per location (A, B, C)**  
  The EDA showed that locations have different volume scales and potentially different trend dynamics. Training separate models keeps the behavior interpretable and avoids forcing one shared parameterization across series with different levels.

- **Daily forecasts for the next 30 days**  
  The model generates daily predictions and exports both point forecasts and uncertainty bounds.

---

## Parameters and configuration used (Prophet)

Prophet decomposes a time series into:

- **Trend** (piecewise linear by default)
- **Seasonality** (weekly/yearly/custom seasonal patterns)
- **Holiday effects** (optional)
- **Extra regressors** (optional)

Below are the core configuration choices and what they control. (Adjust the exact values here to match `src/models/prophet_model.py`.)

### 1) Trend configuration

Prophet models trend as a piecewise function with automatic **changepoints**.

Common parameters:
- `growth="linear"` (default)  
  Uses linear trend. Works well when there’s no hard upper bound (capacity).

- `n_changepoints`  
  The number of potential changepoints. Higher values allow more potential places where trend can shift.

- `changepoint_range`  
  The proportion of the history in which Prophet will place changepoints (e.g., 0.8 means changepoints are only placed in the first 80% of the series, leaving the tail to extrapolate more smoothly).

- `changepoint_prior_scale`  
  The primary knob controlling trend flexibility:
  - higher → trend adapts quickly (risk: overfit)
  - lower → smoother trend (risk: underfit)

**Practical note:** Location C has a shorter history, so it generally benefits from **more regularization** (smaller priors) than A/B.

---

### 2) Seasonality configuration

The EDA showed clear **weekly seasonality** (weekday/weekend differences), which is why weekly seasonality is enabled.

Typical configuration:
- `weekly_seasonality=True`  
  Captures weekday pattern.

- `daily_seasonality=False`  
  Usually unnecessary for daily aggregated data.

- `yearly_seasonality`  
  Depends on available history:
  - A/B (~3.7 years) can support yearly effects.
  - C (~1 year) has limited support for yearly effects; leaving it off (or strongly regularizing) often improves stability.

- `seasonality_mode`  
  - `additive`: seasonal effect is roughly constant in absolute magnitude.
  - `multiplicative`: seasonal effect scales with the series level (often useful when volumes increase over time and seasonal swings grow proportionally).

---

### 3) Uncertainty intervals

- `interval_width` (e.g., 0.80 or 0.95)  
  Sets the width of the prediction interval returned by Prophet.

The pipeline exports:
- point forecast (`yhat`)
- uncertainty bounds (`yhat_lower`, `yhat_upper`)  
These are exposed in the API as `lower_bound` and `upper_bound`.

---

### 4) Regularization / prior scales (overfitting control)

Key priors:
- `seasonality_prior_scale`  
  Controls how aggressively the model fits seasonal patterns.

- `holidays_prior_scale`  
  Controls how aggressively the model fits holiday effects (when holidays are used).

In general:
- Higher prior scale → more flexible fit (risk: overfit)
- Lower prior scale → smoother fit (risk: underfit)

---

## Potential improvements (what else can be added)

Prophet improvements typically come from adding the right structure (holidays/regressors) and tuning flexibility (priors), rather than increasing complexity blindly.

### 1) Holidays and special events (often high ROI)

If package volume is influenced by known calendar events, Prophet can explicitly model those effects. Examples:
- public holidays
- major local events impacting deliveries
- planned operational changes
- peak shipping periods (e.g., Black Friday → pre-Christmas)

Two common patterns:
- Built-in country holidays: `add_country_holidays(country_name="...")`
- Custom holiday table: supply a `holidays` DataFrame with event names and dates

Tune:
- `holidays_prior_scale` to avoid overfitting to holidays that are not consistently impactful.

Reference: Prophet docs — “Modeling holidays and special events”  
https://facebook.github.io/prophet/docs/seasonality,_holiday_effects,_and_regressors.html#modeling-holidays-and-special-events

---

### 2) Extra regressors (best when you have known drivers)

Prophet supports additional explanatory variables via `add_regressor`. This is often the cleanest path to better accuracy because it explains *why* the series changes.

Candidate regressors:
- promo / campaign indicators
- staffing or capacity indicators
- “open/closed” flags
- weather (if relevant)
- upstream demand or lead indicators

Implementation note:
- Make sure regressors are available for both history and the forecast horizon.
- Apply time-series CV to verify the regressor adds lift.

---

### 3) Custom seasonalities (use only when supported by evidence)

If EDA shows cycles beyond weekly/yearly (e.g., monthly or end-of-month spikes), add custom seasonalities:

- `add_seasonality(name=..., period=..., fourier_order=...)`

Guidance:
- Start simple and validate with walk-forward CV.
- Custom seasonality can overfit if the history is short (especially for Location C).

---

### 4) Tune trend/seasonality flexibility using time-series CV

Use walk-forward CV to tune:
- `changepoint_prior_scale`
- `seasonality_prior_scale`
- `seasonality_mode` (`additive` vs `multiplicative`)
- `yearly_seasonality` on/off (per location)

Selection should consider both:
- point accuracy (RMSE/MAE/WAPE)
- interval quality (coverage and width)

---

### 5) Capacity constraints (logistic growth)

If there is a known maximum throughput (capacity), consider:
- `growth="logistic"` plus `cap` (and optionally `floor`)

This can prevent unrealistic extrapolation during sustained increases.

---

## Suggested way to describe this in the case writeup

- Weekly seasonality was enabled based on EDA.
- Trend flexibility is controlled by changepoint priors and validated with walk-forward CV.
- The last 30 days are held out as a final test to estimate real “next month” performance.
- Next improvement steps (highest expected impact first): **holidays**, **extra regressors**, **custom seasonalities**, then broader hyperparameter tuning.

---