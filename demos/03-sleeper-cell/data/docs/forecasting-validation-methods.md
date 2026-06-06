# Validation Methods — Forecast Accuracy

**Document classification:** INTERNAL  
**Owner:** Financial Planning & Analysis

## Overview

This document describes the validation processes used to assess and improve forecast accuracy.

## Accuracy Metrics

### Mean Absolute Percentage Error (MAPE)
- Target: < 5% for quarterly forecasts at time of submission
- Calculated as: |Actual − Forecast| ÷ Actual × 100
- Reported monthly in the FP&A dashboard

### Forecast Bias
- Positive bias (consistently over-forecasting) triggers model recalibration
- Threshold: Bias > +3% for two consecutive quarters

## Validation Checkpoints

### Pre-submission
- Cross-check revenue inputs against CRM export from same date
- Validate headcount against HRIS system
- Confirm cost inputs against latest PO log

### Post-close
- Variance analysis within 5 business days of period close
- Root cause documentation for any variance > $1M
- Model adjustment log updated for next cycle

## Historical Accuracy — FY2024

| Quarter | Forecast | Actual | MAPE |
|---|---|---|---|
| Q1 2024 | $128.4M | $124.1M | 3.5% |
| Q2 2024 | $131.7M | $133.2M | 1.1% |
| Q3 2024 | $136.8M | $138.9M | 1.5% |
