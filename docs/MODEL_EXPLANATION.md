# Model Selection and Evaluation

## Model Choice: Facebook Prophet

### Why Prophet?

After considering several time-series forecasting approaches, I selected **Facebook Prophet** for the following reasons:

1. **Handles Missing Data**: Location C has completely missing data from 2022 to mid-2024. Prophet naturally handles gaps in the time series without requiring extensive imputation strategies.

2. **Seasonality Decomposition**: Prophet explicitly models weekly and yearly seasonality, which is critical for logistics data:
   - **Weekly**: Package volumes typically drop on weekends
   - **Yearly**: Seasonal trends (holidays, peak seasons)

3. **Uncertainty Intervals**: Prophet provides confidence intervals (`yhat_lower`, `yhat_upper`) out of the box, satisfying the bonus requirement for quantifying forecast uncertainty.

4. **Robust to Outliers**: Uses robust error terms that don't get heavily influenced by occasional spikes.

5. **Easy to Interpret**: Trend and seasonality components can be visualized separately, making it easier to explain to stakeholders.

### Alternative Models Considered

| Model | Pros | Cons | Why Not Selected |
|-------|------|------|------------------|
| **ARIMA** | Classic time-series model, good for stable series | Complex to tune (p,d,q parameters), struggles with multiple seasonalities, harder to automate | Difficult to handle Location C's cold start |
| **XGBoost** | Very powerful, flexible | Requires extensive feature engineering (lags, rolling windows), no native uncertainty estimates | Overly complex for the problem scope |
| **LSTM/Neural Networks** | Can capture complex patterns | Requires large amounts of data, hard to interpret, computationally expensive | Location C has <1 year of data |
| **Naive/Moving Average** | Simple baseline | Poor predictive power | Only useful as a benchmark |

## Model Configuration

### Location-Specific Settings

The models are trained **separately** for each location because:

1. **Different Data Availability**: Location C only has data from Sep 2024, while A and B have 3+ years
2. **Different Volumes**: Each location has distinct scales and variance
3. **Different Patterns**: Hub vs spoke locations may have different weekend/holiday patterns

**Configuration by Location:**

```python
# Locations A & B (3+ years of data):
Prophet(
    daily_seasonality=False,      # Already daily aggregates
    weekly_seasonality=True,       # Strong weekend effect
    yearly_seasonality=True,       # Capture annual trends
    interval_width=0.95            # 95% confidence intervals
)

# Location C (<1 year of data):
Prophet(
    daily_seasonality=False,
    weekly_seasonality=True,       
    yearly_seasonality=False,      # Disabled: not enough data
    interval_width=0.95
)
```

## Evaluation Metrics

### RMSE (Root Mean Squared Error)

**Formula**: $\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}$

**Why chosen**:
- Penalizes large errors heavily (squared term)
- In the same units as the target (packages), making it interpretable
- Standard metric for regression problems

**Results**:
- Location A: 5,944.71 packages
- Location B: 3,153.54 packages
- Location C: 1,538.34 packages

**Interpretation**: For Location A with an average of ~13,764 packages/day, an RMSE of ~5,945 represents about 43% relative error, which is reasonable given the high variance in logistics data.

### MAPE (Mean Absolute Percentage Error) - Caveat

**Formula**: $\text{MAPE} = \frac{100}{n}\sum_{i=1}^{n}\left|\frac{y_i - \hat{y}_i}{y_i}\right|$

**Why included**:
- Business-friendly (percentage terms)
- Scale-independent (can compare across locations)

**Issue Encountered**:
The MAPE values in this dataset are extremely high (>100%) because there are days with very low or zero package volumes in the test set. When the actual value approaches zero, MAPE explodes mathematically.

**Note**: In production, I would use **symmetric MAPE (sMAPE)** or **WAPE (Weighted Absolute Percentage Error)** to avoid this zero-division issue.

## Validation Strategy

**Time-Series Split**:
- Training: All data up to T-30 days
- Validation: Last 30 days
- Forecast: Next 30 days into the future

This mimics the real-world forecasting scenario where we want to predict 30 days ahead.

**Final Model**: Retrained on the full dataset (including the validation period) to maximize the use of available data for production forecasts.

## Handling Location C's "Cold Start"

Location C presents a unique challenge:
- Data only starts from September 2024 (~365 days)
- The first 2.5 years are completely empty

**Strategy Implemented**:
1. **Dynamic Start Detection**: The code automatically finds the first date with at least 7 consecutive non-null days
2. **Reduced Seasonality**: Yearly seasonality is disabled (<2 years of data)
3. **Weekly Patterns Only**: Focus on the robust weekly cycle

**Alternative Approach (Not Implemented)**:
Could use Locations A and B as exogenous regressors to "bootstrap" predictions for C. This assumes correlation between locations (e.g., they're in the same region). Would implement if more time available.

## Forecast Uncertainty

The `yhat_lower` and `yhat_upper` bounds represent the **95% prediction interval**. This means:
- We expect the actual value to fall within this range 95% of the time
- The width of the interval indicates model confidence
- Wider intervals = higher uncertainty (common for further-out predictions)

**Use case for stakeholders**:
- Conservative planning: Use `yhat_lower`
- Aggressive planning: Use `yhat_upper`
- Expected value: Use `yhat` (forecast)
