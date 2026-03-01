# Forecasting Reporting Standards

**Document ID:** FIN-2026-004  
**Classification:** Internal Use Only  
**Last Updated:** 2026-01-09

## Overview

Consistent reporting standards ensure forecasts are communicated clearly and used appropriately in business decisions. This document defines presentation formats, required disclosures, and distribution guidelines.

## Report Components

### Executive Summary

Every forecast report must include:

1. **Key Findings** — Top 3-5 insights in bullet points
2. **Confidence Level** — Overall confidence rating (High/Medium/Low)
3. **Time Horizon** — Forecast period covered
4. **Comparison to Prior** — Change from previous forecast
5. **Action Items** — Recommended decisions or follow-ups

### Forecast Details

#### Point Estimates

- Present primary forecast value
- Include units and currency
- Show comparison to prior period (YoY, QoQ)

#### Uncertainty Ranges

- Always provide confidence intervals
- Standard: 80% and 95% intervals
- Visualize with fan charts or error bars

#### Scenarios

For strategic forecasts, include:

- **Base Case** — Most likely outcome
- **Upside Case** — Optimistic scenario with probability
- **Downside Case** — Pessimistic scenario with probability

### Supporting Analysis

- Key assumptions listed explicitly
- Data sources and refresh dates
- Model methodology summary
- Known limitations and caveats

## Visualization Standards

### Charts and Graphs

**Time Series Plots**
- Actual values as solid line
- Forecast as dashed line
- Confidence intervals as shaded region
- Clear axis labels with units

**Comparison Charts**
- Use consistent color coding
- Include variance annotations
- Show both absolute and percentage differences

### Tables

- Right-align numeric values
- Include totals and subtotals
- Use consistent decimal places
- Highlight significant variances

## Required Disclosures

Every forecast must disclose:

1. **Model Type** — Brief description of methodology
2. **Data Vintage** — Most recent data included
3. **Key Assumptions** — Critical inputs and their sources
4. **Limitations** — Known weaknesses or blind spots
5. **Accuracy History** — Historical MAPE for this forecast type

## Distribution Guidelines

### Audience Tiers

| Tier | Content Level | Frequency |
|------|---------------|-----------|
| Executive | Summary only | Monthly |
| Management | Summary + key details | Bi-weekly |
| Operational | Full detail | Weekly |
| Analyst | Full + methodology | On request |

### Confidentiality

- Mark all forecasts with classification level
- Limit distribution to need-to-know basis
- No external sharing without approval
- Archive superseded forecasts

## Version Control

### Naming Convention

```
[Type]_[Period]_[Version]_[Date]
Example: SalesForecast_Q4-2026_v2_20260115
```

### Change Log

Maintain record of:
- Version number and date
- Changes from prior version
- Reason for revision
- Approver name

## Review and Approval

### Required Sign-offs

- [ ] Forecast analyst (preparer)
- [ ] Data science lead (methodology)
- [ ] Business owner (assumptions)
- [ ] Finance representative (for financial forecasts)

### Review Cadence

- Weekly forecasts: Manager approval
- Monthly forecasts: Director approval
- Annual/strategic: VP approval
