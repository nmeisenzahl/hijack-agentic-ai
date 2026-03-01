# Forecasting Validation Methods

**Document ID:** FIN-2026-003  
**Classification:** Internal Use Only  
**Last Updated:** 2026-01-09

## Overview

Forecast validation ensures predictions are accurate, reliable, and suitable for business decision-making. This document outlines standard validation procedures.

## Validation Framework

### Pre-Deployment Validation

#### Statistical Validation

1. **Residual Analysis**
   - Check residuals for normality
   - Verify no autocorrelation in errors
   - Confirm homoscedasticity (constant variance)

2. **Backtesting**
   - Test model on historical periods
   - Compare predictions to actual outcomes
   - Calculate error metrics across multiple periods

3. **Stress Testing**
   - Test model behavior during anomalous periods
   - Verify reasonable outputs for edge cases
   - Document model limitations

#### Business Validation

1. **Subject Matter Expert Review**
   - Present forecasts to domain experts
   - Validate assumptions and methodology
   - Incorporate qualitative adjustments

2. **Reasonableness Checks**
   - Compare to historical ranges
   - Verify alignment with known business events
   - Check for logical consistency

### Post-Deployment Monitoring

#### Accuracy Tracking

- Calculate MAPE weekly/monthly
- Maintain rolling accuracy dashboard
- Set alerting thresholds for degradation

#### Drift Detection

- Monitor feature distributions
- Track prediction distribution changes
- Trigger retraining when drift detected

## Error Metrics

### Standard Metrics

**Mean Absolute Percentage Error (MAPE)**
```
MAPE = (1/n) × Σ|Actual - Forecast| / |Actual| × 100
```
- Target: < 10% for stable products
- Acceptable: 10-20% for variable demand
- Review needed: > 20%

**Root Mean Square Error (RMSE)**
```
RMSE = √[(1/n) × Σ(Actual - Forecast)²]
```
- Useful for comparing models on same scale
- Penalizes large errors more heavily

**Bias (Mean Error)**
```
Bias = (1/n) × Σ(Forecast - Actual)
```
- Should be close to zero
- Positive = systematic over-forecasting
- Negative = systematic under-forecasting

### Segmented Analysis

Calculate metrics by:
- Product category
- Region/geography
- Customer segment
- Time period (month, quarter)

## Validation Checklist

Before deploying any forecast:

- [ ] Residuals pass normality test
- [ ] No significant autocorrelation in errors
- [ ] MAPE within acceptable range
- [ ] Bias is not statistically significant
- [ ] SME review completed
- [ ] Edge cases documented
- [ ] Monitoring dashboards configured
- [ ] Retraining triggers defined

## Escalation Procedures

### When to Escalate

- MAPE exceeds threshold for 3 consecutive periods
- Significant bias detected
- Major business event not captured
- Model producing illogical outputs

### Escalation Path

1. Forecast analyst investigates
2. Data science team review
3. Business stakeholder notification
4. Model retraining or replacement decision
