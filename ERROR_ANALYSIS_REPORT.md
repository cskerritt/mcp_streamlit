# Projection Years Error Analysis Report

## Executive Summary

**Issue**: Using 39.0 years instead of the correct 39.4 years in life care plan projections results in systematic underestimation of total costs.

**Key Findings**:
- **Overall Error Rate**: 1.866% underestimation when using 39.0 vs 39.4 years
- **Dollar Impact**: $226,295 underestimation across test scenarios ($12.1M baseline)
- **Error varies by service type**: Higher inflation rates = larger errors

## Detailed Analysis Results

### Per-Service Error Rates (39.0 vs 39.4 years)

| Service Type | Base Cost | Inflation Rate | Error Rate | Dollar Impact |
|--------------|-----------|----------------|------------|---------------|
| Physician Evaluation | $444.33 | 3.2% | +1.810% | $607 |
| Diagnostics (MRI) | $1,852.03 | 3.0% | +1.754% | $2,346 |
| Physical Therapy | $17,908.88 | 2.8% | +1.699% | $21,031 |
| Medications | $277.40 | 1.6% | +1.387% | $2,473 |
| Surgery | $130,600.45 | 3.5% | +1.896% | $199,838 |

### Comparative Totals

| Projection Period | Total Cost | Difference from Baseline | Error Rate |
|-------------------|------------|-------------------------|------------|
| 39.0 years | $12,126,536 | — (baseline) | — |
| 39.4 years | $12,352,832 | +$226,295 | +1.866% |
| 40.0 years | $12,692,275 | +$565,738 | +4.665% |

## Key Insights

### 1. Error Magnitude
- The 0.4-year difference represents **1.02%** of the total projection period
- This seemingly small difference compounds due to inflation over the entire projection period
- **Higher inflation services show larger errors** (Surgery: 1.896% vs Medications: 1.387%)

### 2. Financial Impact
- For every **$1 million** in projected costs, using 39.0 instead of 39.4 years results in approximately **$18,660** underestimation
- The fractional year cost represents the **inflated cost in year 40** prorated for 0.4 years

### 3. Compounding Effect
- The error is not simply 0.4/39.4 = 1.02% because costs in the fractional year are inflated by 39+ years of compound growth
- Services with higher inflation rates show disproportionately larger errors

## Risk Assessment

### Low Risk Services (< 1.5% error)
- **Medications** with low inflation rates (1.6%): 1.387% error

### Medium Risk Services (1.5% - 1.7% error)
- **Diagnostics** (3.0% inflation): 1.754% error
- **Physical Therapy** (2.8% inflation): 1.699% error

### High Risk Services (> 1.7% error)
- **Physician Evaluations** (3.2% inflation): 1.810% error
- **Surgeries** (3.5% inflation): 1.896% error

## Recommendations

### 1. Immediate Action Required
- **Update all projection calculations** to use 39.4 years instead of 39.0 years
- **Review existing reports** that may have used the incorrect 39.0-year assumption

### 2. Quality Assurance
- Implement validation checks to ensure fractional years are properly handled
- Add automated testing to prevent regression to whole-year calculations

### 3. Documentation
- Update all documentation to specify that projection periods can and should include decimal values
- Train users on the importance of precise projection period specification

## Technical Implementation

The error analysis revealed that the calculation system was:
1. ✅ **Fixed**: Now properly handles fractional projection years (39.4)
2. ✅ **Updated**: Input forms now accept decimal values with 0.1-year precision
3. ✅ **Validated**: Column headers correctly show "39.4 yrs @ X%" instead of "39 yrs @ X%"

## Conclusion

Using 39.0 years instead of 39.4 years results in a **1.866% systematic underestimation** of total life care costs. While this may seem small, it represents:

- **$226,295 underestimation** in the test scenario
- **Approximately $18,660 error per $1M** in projected costs
- **Higher errors for services with higher inflation rates**

The fix has been implemented to ensure accurate decimal-year projections going forward.

---
*Analysis Date: 2025-06-18*  
*Total Test Scenarios: 5 service types*  
*Baseline Projection Value: $12,126,536*