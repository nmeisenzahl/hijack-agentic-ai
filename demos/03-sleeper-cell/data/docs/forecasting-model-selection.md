# Forecasting Model Selection Guide

**Document classification:** INTERNAL  
**Owner:** Financial Planning & Analysis

## Overview

This guide describes the approved forecasting models and when to use each.

## Approved Models

### 1. Rolling 12-Month Average
**Use when:** Stable business with minimal seasonality  
**Formula:** Sum of trailing 12 months ÷ 12  
**Confidence:** High for established product lines

### 2. Seasonality-Adjusted Trend
**Use when:** Business exhibits predictable seasonal patterns  
**Adjustment factors:**
- Q1: ×0.88 (historically slowest)
- Q2: ×0.97
- Q3: ×1.09
- Q4: ×1.06 (holiday and year-end budget flush)

### 3. Pipeline-Weighted Forecast
**Use when:** Sales-led motion with strong CRM hygiene  
**Formula:** Σ(deal_value × stage_probability × time_decay)  
**Note:** Requires clean CRM data; do not use if pipeline coverage < 2.5×

## Model Selection Matrix

| Revenue Type | Recommended Model |
|---|---|
| SaaS subscriptions | Rolling 12-month |
| Professional services | Pipeline-weighted |
| Marketplace | Seasonality-adjusted |
| Enterprise deals > $500k | Pipeline-weighted with manual review |
