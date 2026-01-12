# Forecasting Data Collection Best Practices

**Document ID:** FIN-2026-001  
**Classification:** Internal Use Only  
**Last Updated:** 2026-01-08

## Overview

Accurate forecasting depends on high-quality data collection. This document outlines best practices for gathering, validating, and preparing data for business forecasting.

## Data Sources

### Primary Data Sources

1. **Sales Systems** — Transaction records, order history, customer data
2. **Financial Systems** — Revenue, costs, margins, cash flow
3. **CRM Data** — Pipeline, conversion rates, customer lifecycle
4. **Market Data** — Industry trends, competitor analysis, economic indicators

### Secondary Data Sources

1. **External APIs** — Market indices, economic data feeds
2. **Third-Party Reports** — Analyst forecasts, industry benchmarks
3. **Survey Data** — Customer feedback, market research

## Data Quality Requirements

### Completeness

- Ensure all required fields are populated
- Document missing data and imputation methods
- Maintain minimum 24 months of historical data for trend analysis

### Accuracy

- Cross-validate data against source systems
- Implement automated data quality checks
- Flag and investigate outliers before inclusion

### Timeliness

- Data should be refreshed at least weekly for operational forecasts
- Monthly refresh acceptable for strategic planning
- Document data lag and its impact on forecast accuracy

## Data Preparation Guidelines

### Standardization

- Convert all currencies to a single base currency
- Normalize time periods (fiscal vs. calendar year alignment)
- Standardize product/service categorization

### Cleaning

- Remove duplicate records
- Handle null values consistently
- Correct known data entry errors

### Transformation

- Calculate derived metrics (growth rates, ratios)
- Aggregate data to appropriate granularity
- Create lag features for time-series analysis

## Documentation Requirements

For each data source, maintain:

- Source system name and owner
- Refresh frequency and last update timestamp
- Data dictionary with field definitions
- Known limitations and caveats
- Contact information for data steward

## Compliance Notes

All data collection must comply with:

- Data privacy regulations (GDPR, CCPA)
- Internal data governance policies
- Industry-specific requirements (SOX for financial data)
