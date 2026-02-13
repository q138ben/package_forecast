# Model Evaluation Guide

This document explains how to evaluate the performance of the time series forecasting models in this project, including the rationale for the chosen metrics and how to interpret them.

## 1. Evaluation Overview

Model performance is assessed using both a machine learning model (Prophet) and a naive baseline (seasonal naive forecast). Evaluation is performed on:
- **Cross-validation folds** (expanding window, on training data)
- **Final test set** (holdout, last 30 days)

Both approaches are compared to ensure the model provides value beyond simple heuristics.

## 2. Metrics Used

### a. Root Mean Squared Error (RMSE)
- **Definition:** $\sqrt{\frac{1}{n} \sum_{i=1}^n (y_i - \hat{y}_i)^2}$
- **Interpretation:** Penalizes large errors more than small ones. Lower RMSE indicates better fit.

### b. Mean Absolute Error (MAE)
- **Definition:** $\frac{1}{n} \sum_{i=1}^n |y_i - \hat{y}_i|$
- **Interpretation:** Average magnitude of errors. Less sensitive to outliers than RMSE.

### c. Weighted Absolute Percentage Error (WAPE)
- **Definition:** $\frac{\sum_{i=1}^n |y_i - \hat{y}_i|}{\sum_{i=1}^n |y_i|} \times 100$
- **Interpretation:** Expresses error as a percentage of total actuals. Useful for comparing across series of different scales.

### d. Interval Coverage (%)
- **Definition:** Proportion of actual values falling within the model's predicted confidence interval.
- **Interpretation:** Measures the reliability of uncertainty estimates. Ideal coverage matches the nominal interval (e.g., 95%).

### e. Average Interval Width
- **Definition:** Mean width of the model's confidence interval for each prediction.
- **Interpretation:** Indicates the typical uncertainty range. Narrower intervals are better if coverage is adequate.

## 3. Baseline Comparison

A **seasonal naive baseline** is used for reference. It repeats the value from the same day in the previous week (7-day seasonality) and computes confidence intervals from historical residuals. This provides a simple, interpretable benchmark.

**Why compare to a baseline?**
- Ensures the model outperforms trivial strategies
- Highlights the value added by the machine learning approach

## 4. How to Evaluate

- **Run training:** `python main.py train`
- **Review console output:** Metrics for both Prophet and baseline are printed for each location (CV and test set)
- **Check plots:** Visualizations in `models/` show actuals, Prophet forecasts, and baseline overlays with metrics
- **Interpret results:**
    - Lower RMSE/MAE/WAPE = better accuracy
    - Coverage close to 95% (for 95% CI) = well-calibrated uncertainty
    - Prophet should outperform baseline on all metrics for a successful model

## 5. Example Output

```
Final Test Performance (Holdout):
  RMSE: 12.34 packages
  MAE: 9.87 packages
  WAPE: 8.76%
  Interval coverage: 96.7%
  Baseline (seasonal naive): RMSE=18.21, MAE=14.56, WAPE=13.2% Coverage=90.0%
```

## 6. References
- [Prophet documentation](https://facebook.github.io/prophet/docs/diagnostics.html)
- [Forecasting Principles & Practice](https://otexts.com/fpp3/accuracy.html)

---

For further details, see the code in `src/models/evaluate.py` and the visualizations in `src/visualization/plots.py`.
