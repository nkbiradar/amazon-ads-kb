---
title: "Amazon Ads Reporting Metrics and Measurement"
last_updated: 2026-08-10T18:30:00Z
sources:
  - url: "https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics"
    type: official
    confidence: high
topic_id: ads-reporting-metrics
---

# Amazon Ads Reporting Metrics and Measurement

## Overview

Amazon Ads provides comprehensive reporting metrics to measure campaign performance, optimize strategies, and demonstrate return on advertising investment. Every report in the Ads API is composed of metrics that you specify to include in your report requests. [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

## Metric Categories

### Engagement Metrics
Measure how customers interact with your ads:
- **Impressions**: Number of times ad was displayed
- **Clicks**: Number of times ad was clicked
- **Click-through rate (CTR)**: Percentage of impressions that resulted in clicks
- **Viewable impressions**: Times ad was seen by users
- **View-through rate**: Percentage of viewable impressions [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Sales Metrics
Track revenue and conversion performance:
- **Sales**: Total revenue generated from advertising
- **Orders**: Number of orders placed
- **Units sold**: Total quantity of products sold
- **Conversion rate**: Percentage of clicks that resulted in purchases
- **Add to cart**: Products added to shopping carts [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Cost Metrics
Monitor advertising spend and efficiency:
- **Spend**: Total amount spent on advertising
- **Cost-per-click (CPC)**: Average cost per ad click
- **Cost-per-acquisition (CPA)**: Average cost per order
- **Advertising cost of sales (ACOS)**: Ad spend as percentage of sales
- **Return on ad spend (ROAS)**: Revenue generated per ad dollar spent [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Brand Metrics
Measure brand impact and new customer acquisition:
- **New-to-brand (NTB)**: Orders from first-time customers
- **New-to-brand sales**: Revenue from first-time customers
- **Brand new-to-brand (NTB)**: Customers new to your brand
- **Detail page view rate (DPVR)**: Percentage of views that resulted in product page visits
- **Add-to-list (ATL)**: Products added to shopping lists [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

## Report Types and Levels

### Campaign-Level Reports
Aggregate metrics across entire campaigns:
- Total campaign performance
- Budget utilization
- Overall return on investment
- Cross-campaign comparison [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Ad Group-Level Reports
Metrics for specific ad groups:
- Target audience performance
- Keyword group performance
- Product targeting results
- Creative performance by ad group [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Keyword and Product Targeting Reports
Detailed performance at targeting level:
- Individual keyword metrics
- Product targeting performance
- Search term performance
- Placement performance by target [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Ad-Level Reports
Performance of specific ad creatives:
- Creative performance comparison
- Video vs image ad performance
- Headline and description testing results
- Asset performance analysis [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

## Advanced Metrics

### Reach and Frequency
- **Reach**: Unique users who saw your ads
- **Frequency**: Average times users saw your ads
- **Impression share**: Percentage of available impressions captured
- **Unique reach**: Distinct individuals reached [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Viewability Metrics
- **Viewable impressions**: Ads actually seen by users
- **View-through rate**: Percentage of viewable impressions
- **Video completion rates**: For video ad formats
- **Audio completion rates**: For audio ad formats [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Placement Metrics
Performance by ad placement:
- **Top of search**: Performance on first search result page
- **Product pages**: Performance on product detail pages
- **Rest of search**: Other search result positions
- **Third-party placements**: Off-Amazon performance [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

## Reporting API Structure

### Metric Specification
Every report requires:
- **Report type**: Defines granularity and scope
- **Metrics list**: Specific metrics to include
- **Date range**: Time period for data
- **Filters**: Specific data segmentation
- **Grouping**: How to aggregate results [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Available Report Types
- **Campaign reports**: Overall campaign performance
- **Ad group reports**: Ad group level metrics
- **Keyword reports**: Search term and keyword performance
- **Targeting reports**: Product targeting performance
- **Ad reports**: Creative and asset performance [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

## Performance Analysis

### Trend Analysis
Track metrics over time to identify:
- Seasonal patterns and fluctuations
- Performance improvement trends
- Cost efficiency changes
- Market condition impacts [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Comparative Analysis
Compare performance across:
- Different campaigns and ad groups
- Time periods (week over week, month over month)
- Product categories and segments
- Geographic markets [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Optimization Opportunities
Use metrics to identify:
- High-performing keywords and targets
- Underperforming ad creatives
- Efficient bid strategies
- Budget allocation opportunities
- Audience segment performance [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

## Custom Reporting

### Report Configuration
Customize reports with:
- **Metric selection**: Choose relevant KPIs
- **Date ranges**: Compare specific time periods
- **Segmentation**: Break down by dimensions
- **Filters**: Focus on specific data subsets
- **Formatting**: Structure for analysis needs [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Automated Reporting
Set up:
- **Scheduled reports**: Regular performance updates
- **Alert triggers**: Performance threshold notifications
- **Custom dashboards**: Real-time monitoring
- **Data exports**: External analysis integration [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

## Best Practices

### Key Performance Indicators
Focus on metrics that matter:
- **Business goals**: Sales, revenue, profit
- **Efficiency metrics**: ROAS, ACOS, CPA
- **Growth metrics**: NTB, market share
- **Brand metrics**: Awareness, consideration [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Data Quality
Ensure reliable metrics by:
- Allowing sufficient data collection time
- Understanding metric definitions and calculations
- Considering attribution windows
- Accounting for seasonal variations
- Monitoring for data anomalies [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Regular Review Process
Establish consistent analysis:
- **Daily monitoring**: Campaign health checks
- **Weekly reviews**: Performance trend analysis
- **Monthly deep-dives**: Comprehensive performance analysis
- **Quarterly assessments**: Strategy and planning reviews [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

## Integration with Analytics

### Amazon Marketing Cloud
Combine Amazon Ads metrics with:
- Event-level data analysis
- Cross-channel attribution
- Customer journey mapping
- Advanced analytics and modeling [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

### Third-Party Tools
Integrate with:
- Business intelligence platforms
- Custom dashboards and visualizations
- Automated reporting systems
- Data warehousing solutions [¹](https://advertising.amazon.com/API/docs/en-us/guides/reporting/v2/metrics)

## Related Topics

- [Amazon Attribution](amazon-attribution-measurement.md)
- [Amazon Marketing Cloud](amazon-marketing-cloud.md)
- [Dynamic Bidding Strategies](dynamic-bidding-strategies.md)
