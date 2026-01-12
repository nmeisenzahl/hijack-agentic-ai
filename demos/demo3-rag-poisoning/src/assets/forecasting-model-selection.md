# Forecasting Model Selection Guidelines

**Document ID:** FIN-2026-002  
**Classification:** Internal Use Only  
**Last Updated:** 2026-01-08

## Overview

Selecting the appropriate forecasting model is critical for accuracy and reliability. This guide helps analysts choose the right approach based on data characteristics and business requirements.

## Model Categories

### Time Series Models

**Simple Moving Average (SMA)**
- Best for: Stable demand patterns with minimal trend
- Data requirements: Minimum 12 periods
- Use when: Short-term operational forecasting

**Exponential Smoothing**
- Best for: Data with trend and/or seasonality
- Variants: Simple, Holt's (trend), Holt-Winters (trend + seasonality)
- Use when: Medium-term planning with clear patterns

**ARIMA/SARIMA**
- Best for: Complex time series with autocorrelation
- Data requirements: Minimum 36 periods, stationary or differenced
- Use when: High accuracy needed, sufficient historical data

### Causal Models

**Linear Regression**
- Best for: Forecasts driven by identifiable factors
- Data requirements: Sufficient observations per predictor
- Use when: Clear causal relationships exist

**Multiple Regression**
- Best for: Multiple drivers affecting outcomes
- Considerations: Watch for multicollinearity
- Use when: Several factors influence the forecast

### Machine Learning Models

**Random Forest / Gradient Boosting**
- Best for: Complex non-linear relationships
- Data requirements: Large datasets (1000+ observations)
- Use when: Traditional models underperform

**Neural Networks (LSTM)**
- Best for: Very large datasets with complex patterns
- Data requirements: 10,000+ observations recommended
- Use when: Resources available for model tuning

## Selection Criteria

### Data Characteristics

| Characteristic | Recommended Approach |
|----------------|---------------------|
| < 24 periods | Simple methods (SMA, naive) |
| Strong seasonality | Holt-Winters, SARIMA |
| Multiple drivers | Regression models |
| Non-linear patterns | ML models |
| Intermittent demand | Croston's method |

### Business Requirements

| Requirement | Consideration |
|-------------|---------------|
| Explainability needed | Prefer regression, avoid black-box |
| Automation required | Choose models with auto-tuning |
| Real-time updates | Lightweight models preferred |
| Scenario planning | Models supporting what-if analysis |

## Model Validation

### Holdout Testing

- Reserve 20% of recent data for validation
- Never use test data for model tuning
- Report performance on holdout set

### Cross-Validation

- Use time-series aware CV (rolling origin)
- Minimum 5 folds for robust estimates
- Report mean and standard deviation of errors

### Performance Metrics

- **MAPE** — Mean Absolute Percentage Error (primary metric)
- **RMSE** — Root Mean Square Error (penalizes large errors)
- **Bias** — Check for systematic over/under prediction

## Documentation Requirements

For each model deployed, document:

- Model type and parameters
- Training data period and features
- Validation results and metrics
- Known limitations and edge cases
- Retraining schedule and triggers
