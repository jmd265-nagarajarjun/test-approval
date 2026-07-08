# Compute Selection & Sizing Guide

Use this guide before creating any cluster or warehouse. It answers two questions:

- **Which compute type should I use?**
- **How should I size it?**

> **Compute cost starts the moment a cluster or warehouse turns on and stops when it shuts down.**
>
> - **Serverless** - shuts down automatically when idle; you are **only charged for active query execution time.**
> - **Classic** - runs until it hits the idle timeout you configure, or until you manually stop it. Idle time costs money, so always set a sensible auto-termination timeout.
>
> **Recommended idle timeout for Classic compute: 25 minutes.**
>
> With multiple developers actively using compute throughout the day, idle gaps are typically short. A 25-minute timeout provides a good balance between responsiveness and cost control.
>
> Reference: [Cost Optimisation Best Practices - Microsoft Learn](https://learn.microsoft.com/en-us/azure/databricks/lakehouse-architecture/cost-optimization/best-practices)

---

## 1. Choose Your Compute

### Development

| Workload | Compute Type | Mode |
|---|---|---|
| PySpark | All Purpose Cluster | Classic |
| SQL Transformation | SQL Warehouse | Classic |
| BI & Reporting | SQL Warehouse | Serverless |
| Analysis | SQL Warehouse | Serverless |

### Why Classic for SQL Transformation and Notebooks in Development?

Development environments are typically used throughout the working day by multiple developers. In these scenarios, Classic SQL Warehouses are often the most cost-effective option.

Classic SQL Warehouses are approximately **4x cheaper per DBU than Serverless SQL Warehouses**, making them a strong choice when compute is being actively used throughout the day.

| Compute Type | Cost per DBU-hour |
|---|---|
| SQL Compute (Classic) | £0.164 |
| Serverless SQL | £0.708 |

This cost advantage applies primarily when compute is being used consistently throughout the day. For infrequent or short-lived workloads, Serverless may be equally or more cost-effective despite the higher DBU rate because there is no idle compute cost.

> **Pricing shown is based on Azure Databricks list pricing as of June 2026 and is provided for comparison purposes only.**
>
> Databricks pricing may change over time. Always refer to the latest Azure Databricks pricing documentation before making cost-based decisions.
>
> Reference: [Azure Databricks Pricing - Microsoft Azure](https://azure.microsoft.com/en-us/pricing/details/databricks)

### Why Serverless for BI and Analysis in Development?

These workloads are typically triggered on demand rather than being used continuously throughout the day.

Serverless starts instantly with no warm-up period and only incurs cost while queries are actively running, making it well suited for ad-hoc analysis and report refresh workloads.

---

### UAT & Production

| Workload | Compute Type | Mode |
|---|---|---|
| SQL Transformation (dbt) | SQL Warehouse | Serverless |
| BI & Reporting | SQL Warehouse | Serverless |
| Analysis | SQL Warehouse | Serverless |
| Scheduled Jobs | Job Cluster | Serverless |

### Why Fully Serverless in UAT and Production?

There is no active development in these environments. Workloads are either scheduled or triggered on demand.

Serverless eliminates idle compute cost, starts quickly, scales automatically, and removes the need for cluster management.

> Jobs are developed and tested in Development using manual execution. Scheduled execution is configured only in UAT and Production.

> Serverless Job Clusters are fully managed by Databricks. No configuration is required.

---

## 2. Size Your Compute

### SQL Warehouse Sizing

Applies to **all environments**. Both Classic and Serverless SQL Warehouses require a warehouse size and cluster scaling configuration.

### Understanding Cluster Count

Each cluster within a SQL Warehouse handles queries independently. A single cluster can support up to **10 concurrent queries** - when more queries arrive at the same time, Databricks automatically spins up additional clusters to handle the load, up to the configured maximum.

- **Min Clusters** - minimum number of clusters kept available at all times. Setting this to 1 ensures the warehouse is always ready with no cold start.
- **Max Clusters** - maximum number of clusters Databricks can scale to during periods of increased demand.

You are charged only for clusters that are actively running.

> **Not sure which size to pick?**
>
> Start with the recommended size in the table below. If queries are taking longer than expected, check the **Query Profile** in the Databricks SQL editor. If you see **"bytes spilled to disk"** for a query, it is a sign the warehouse may need more memory. Move up to the next warehouse size and reassess performance.

| Workload | Recommended Size | Min Clusters | Max Clusters | Notes |
|---|---|---|---|---|
| SQL Transformation / dbt | Small | 1 | 3 | Recommended starting configuration for transformation workloads. Applies to Dev (Classic) and UAT & Prod (Serverless). Increase warehouse size only if performance bottlenecks are observed |
| BI & Reporting | Small | 1 | 4 | Suitable for Power BI refresh workloads. Increase Max Clusters if refreshes begin queueing, timing out, or taking longer than expected. |
| Analysis | X-Small | 1 | 1 | Suitable for ad hoc analysis |

Reference: [SQL Warehouse Sizing - Databricks Docs](https://docs.databricks.com/aws/en/compute/sql-warehouse/warehouse-behavior)

---

### All Purpose Cluster Configuration (Development Only)

Used for notebook and interactive development in the Development environment.

> ⚠️ **Avoid Interactive Serverless Notebook compute for day-to-day development.**
>
> Serverless Notebook compute provides near-instant startup times and a great developer experience, but it is generally more expensive than a shared Classic All Purpose cluster when used continuously throughout the day.
>
> For most development teams, a Classic All Purpose cluster provides a better balance between cost and usability.

> ✅ **Enable Photon by default.**
>
> Photon is Databricks' native vectorised query engine that accelerates Apache Spark workloads and can significantly improve performance while reducing overall compute cost. It is particularly effective for data engineering workloads involving Delta Lake, SQL operations, and ETL pipelines.
>
> Reference: [Photon Runtime - Databricks Docs](https://docs.databricks.com/en/runtime/photon.html)

#### Access Mode

Since the All Purpose cluster is shared across multiple developers, set the Access Mode to **Shared**.

Shared mode supports Unity Catalog and ensures proper user isolation. Each developer's permissions and workload execution remain appropriately scoped even when using the same cluster. Avoid **No Isolation Shared** mode as it does not support Unity Catalog and provides no separation between users.

Reference: [Access Modes - Databricks Docs](https://docs.databricks.com/en/compute/configure.html#access-modes)

---

#### Step 1 - Choose a VM Family

Default to **General Purpose (D-Series)** for almost all workloads. Only move to a specialised VM family when there is a clear workload requirement.

| VM Family | When to Use | Azure Reference |
|---|---|---|
| **General Purpose (D-Series)** ← Default | ETL pipelines, dbt workloads, SQL processing, Delta Lake operations, and standard Spark workloads | [Dv5 Series - Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/dv5-series) |
| **Memory Optimised (E-Series)** | Large joins, complex aggregations, memory-intensive Spark workloads, or when encountering out-of-memory errors on D-Series | [Ev5 Series - Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/memory-optimized/ev5-series) |
| **Compute Optimised (F-Series)** | CPU-intensive workloads requiring high compute throughput | [Fsv2 Series - Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/compute-optimized/fsv2-series) |

> If you are unsure, use D-Series.
>
> Move to E-Series only when memory pressure becomes a demonstrated bottleneck.
>
> F-Series is rarely required for standard data engineering workloads.

#### Step 2 - Configure Workers

**Always enable autoscaling.** Databricks automatically scales the cluster up and down based on workload demand, helping to balance performance and cost.

Since the All Purpose cluster is shared across the development team, configure workers as follows:

- Min Workers: 1
- Max Workers: 4

Reference: [All Purpose Compute - Databricks Docs](https://docs.databricks.com/aws/en/jobs/compute)
