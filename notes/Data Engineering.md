---
title: Data Engineering
tags:
  - data
  - infrastructure
date: 2026-06-10
---

# Data Engineering Notes

## ETL Pipeline Design

- Extract → Transform → Load
- Real-time vs Batch processing
- Data quality checks at each stage

## Tools & Technologies

- **Apache Spark** - Distributed data processing
- **Apache Kafka** - Stream processing
- **Airflow** - Workflow orchestration (see [[DevOps Guide]])
- **dbt** - Data transformation

## Integration Points

- Feeds into [[Machine Learning]] training pipelines
- Provides analytics data for [[Project Alpha]]
- Managed by the infrastructure described in [[DevOps Guide]]

## Best Practices

1. Always validate schemas
2. Monitor pipeline health
3. Version control your data models