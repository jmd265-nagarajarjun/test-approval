# Databricks Resource Provisioning Runbook

This guide walks you through how to create and configure Databricks resources - SQL Warehouses, All Purpose Clusters, and Secret Scopes - using the resource generation framework.

---

## How It Works

Instead of manually writing YAML resource definitions, this framework lets you define what you need in a single variables file. A script then reads that file and generates the correct YAML definitions automatically.

```
You fill in the variables file
        ↓
Run the generation script
        ↓
YAML resource definitions are created
        ↓
Run Databricks Bundle commands to deploy
```

**You should only ever need to edit one file: `resource_configuration_variables.yml`**

Do not edit the template files directly. They are managed centrally and shared across the team.

---

## File Structure

```
├── resource_configuration_variables.yml        # ← You work here
├── generate_resource_definitions.py            # ← Script that generates the YAML definitions
│
└── data_platform/
    └── 03_orchestration/
        └── resources/
            ├── configs/                        # Template files (do not edit)
            │   ├── sql_wh_config.yml
            │   ├── all_purpose_cluster_config.yml
            │   └── secrets_config.yml
            │
            └── compute/
            │   ├── sql_warehouse/              # Generated SQL Warehouse definitions (auto-created)
            │   └── all_purpose/                # Generated All Purpose Cluster definitions (auto-created)
            └── secrets/                        # Generated Secret Scope definitions (auto-created)
```

> Files inside `compute/sql_warehouse/`, `compute/all_purpose/`, and `secrets/` are auto-generated every time the script runs. Do not edit these files manually - any changes will be overwritten.

---

## Naming Your Resources

When defining a resource, provide a short name that describes its **purpose only** - nothing else.

The framework automatically handles the rest:

| Resource Type | What You Provide | What Gets Created in Dev | What Gets Created in Prod |
|---|---|---|---|
| SQL Warehouse | `transformation` | `dev_transformation_wh` | `prod_transformation_wh` |
| SQL Warehouse | `bi_reporting` | `dev_bi_reporting_wh` | `prod_bi_reporting_wh` |
| All Purpose Cluster | `development` | `dev_development` | `prod_development` |
| Secret Scope | `dbkit` | `dev-dbkit-kv-secret-scope` | `prod-dbkit-kv-secret-scope` |

- The **environment prefix** (`dev_`, `uat_`, `prod_`) is added automatically based on the deployment target
- The **`_wh` suffix** is added automatically for SQL Warehouses
- The **`-kv-secret-scope` suffix** is added automatically for Secret Scopes
- Do not include the environment name or any suffix in the name you provide - this will result in duplication such as `dev_dev_transformation_wh_wh`

---

## Step 1 - Define Your Resources

Open `resource_configuration_variables.yml` and add your resource under the relevant section.

There are three sections in the file:

- `sql_wh` - for SQL Warehouses
- `all_purpose_cluster` - for All Purpose Clusters
- `secrets` - for Azure Key Vault-backed Secret Scopes

Each section accepts a list, so you can define multiple resources of the same type.

---

### Creating a SQL Warehouse

Add an entry under `sql_wh`:

```yaml
sql_wh:
  - name: "transformation"
    cluster_size: "Small"
    min_num_clusters: 1
    max_num_clusters: 2
    auto_stop_mins: 25
    warehouse_type: "PRO"
    enable_serverless_compute: false
    permissions:
      groups:
        - group_name: your_group_name
          level: CAN_USE
```

**Field Reference:**

| Field | Description | Example |
|---|---|---|
| `name` | Purpose-based name for the warehouse. Do not include environment or `_wh` - these are added automatically | `"transformation"`, `"bi_reporting"` |
| `cluster_size` | Size of the warehouse. See sizing guide for recommendations | `"X-Small"`, `"Small"`, `"Medium"` |
| `min_num_clusters` | Minimum clusters kept running at all times | `1` |
| `max_num_clusters` | Maximum clusters Databricks can scale up to | `2` |
| `auto_stop_mins` | Minutes of inactivity before the warehouse shuts down | `25` |
| `warehouse_type` | Compute tier. Use `PRO` for Serverless or Analytics; `CLASSIC` for Standard | `"PRO"` |
| `enable_serverless_compute` | Set to `true` for Serverless, `false` for Classic or Pro | `true` / `false` |

**Warehouse Type Combinations:**

| What You Want | `warehouse_type` | `enable_serverless_compute` |
|---|---|---|
| Classic Warehouse | `CLASSIC` | `false` |
| Pro / Analytics Warehouse | `PRO` | `false` |
| Serverless Warehouse | `PRO` | `true` |

> Refer to the [Compute Selection & Sizing Guide](./compute-selection-guide.md) for recommendations on size, cluster counts, and when to use Classic vs Serverless.

---

### Creating an All Purpose Cluster

Add an entry under `all_purpose_cluster`:

```yaml
all_purpose_cluster:
  - name: "development"
    spark_version: "16.4.x-scala2.12"
    runtime_engine: "PHOTON"
    node_type_id: "Standard_D4s_v5"
    driver_node_type_id: "Standard_D4s_v5"
    min_workers: 1
    max_workers: 4
    autotermination_minutes: 25
    permissions:
      groups:
        - group_name: your_group_name
          level: CAN_ATTACH_TO
```

**Field Reference:**

| Field | Description | Example |
|---|---|---|
| `name` | Purpose-based name for the cluster. Do not include the environment - it is added automatically | `"development"`, `"ingestion"` |
| `spark_version` | Databricks Runtime version to use | `"16.4.x-scala2.12"` |
| `runtime_engine` | Set to `PHOTON` to enable Photon acceleration (recommended) | `"PHOTON"` |
| `node_type_id` | Azure VM type for worker nodes. See VM selection guide below | `"Standard_D4s_v5"` |
| `driver_node_type_id` | Azure VM type for the driver node. Typically matches worker | `"Standard_D4s_v5"` |
| `min_workers` | Minimum number of worker nodes | `1` |
| `max_workers` | Maximum number of worker nodes Databricks can scale to | `4` |
| `autotermination_minutes` | Minutes of inactivity before the cluster shuts down | `25` |

**VM Type Quick Reference:**

| VM Family | Use When |
|---|---|
| `Standard_D4s_v5` (General Purpose) | Default for most workloads - ETL, dbt, Delta Lake, standard Spark |
| `Standard_E4s_v5` (Memory Optimised) | Large joins, complex aggregations, or when hitting out-of-memory errors |
| `Standard_F4s_v2` (Compute Optimised) | CPU-intensive workloads requiring high throughput |

> Always enable Photon by setting `runtime_engine: "PHOTON"`. It accelerates Spark workloads and reduces overall compute cost, particularly for data engineering workloads.

---

### Creating a Secret Scope

Secret Scopes are backed by **Azure Key Vault**. The Key Vault connection details (`resource_id` and `dns_name`) are managed per environment in `databricks.yml` - so you only need to provide the project abbreviation here. The correct Key Vault is resolved automatically at deploy time based on the target environment.

Add an entry under `secrets`:

```yaml
secrets:
  - name: "dbkit"
    permissions:
      groups:
        - group_name: your_group_name
          level: MANAGE
```

**Field Reference:**

| Field | Description | Example |
|---|---|---|
| `name` | Project abbreviation only. Do not include environment or `-kv-secret-scope` - these are added automatically | `"dbkit"` |

> The Key Vault `resource_id` and `dns_name` are configured in `databricks.yml` under each target. If you need to connect to a new Key Vault or update an existing one, update the `keyvault_resource_id` and `keyvault_dns_name` variables there. These values can be found in the Azure Portal under the Key Vault resource → **Properties**.

---

### Configuring Permissions

Permissions can be granted to **groups**, **individual users**, or **service principals**. Where possible, prefer group-based access - it is easier to manage as the team grows.

**Permission Levels:**

| Level | Applies To | What It Allows |
|---|---|---|
| `CAN_USE` | SQL Warehouse | Run queries on the warehouse |
| `CAN_MONITOR` | SQL Warehouse | View query history and warehouse metrics without running queries |
| `CAN_MANAGE` | SQL Warehouse, All Purpose Cluster | Full control - edit, delete, manage permissions |
| `CAN_ATTACH_TO` | All Purpose Cluster | Attach notebooks or jobs to the cluster |
| `CAN_RESTART` | All Purpose Cluster | Restart the cluster |
| `MANAGE` | Secret Scope | Full control over the secret scope |
| `READ` | Secret Scope | Read secrets from the scope |

**Groups** - grant access to an entire Databricks group:

```yaml
permissions:
  groups:
    - group_name: data_engineers
      level: CAN_MANAGE
    - group_name: data_analysts
      level: CAN_USE
```

**Individual Users** - grant access to a specific user by their email:

```yaml
permissions:
  users:
    - user_name: user@company.com
      level: CAN_ATTACH_TO
```

**Service Principals** - grant access to a service principal by name:

```yaml
permissions:
  service_principals:
    - service_principal_name: my-service-principal
      level: CAN_MANAGE
```

You can combine all three in the same permissions block:

```yaml
permissions:
  groups:
    - group_name: data_engineers
      level: CAN_MANAGE
  users:
    - user_name: user@company.com
      level: CAN_ATTACH_TO
  service_principals:
    - service_principal_name: my-service-principal
      level: CAN_MANAGE
```

---

## Step 2 - Generate the Resource Definitions

Once you have updated the variables file, run the generation script from the root of the repository:

```bash
python generate_resource_definitions.py
```

The script will:
1. Read your entries from `resource_configuration_variables.yml`
2. Render the appropriate template for each resource
3. Output a YAML definition file for each resource into the relevant folder

You will see output like:

```
Created: data_platform/03_orchestration/resources/compute/sql_warehouse/transformation.yml
Created: data_platform/03_orchestration/resources/compute/all_purpose/development.yml
Created: data_platform/03_orchestration/resources/secrets/dbkit.yml
```

> The script deletes and regenerates all files in the output folders on every run. This ensures the generated files always reflect the current state of the variables file.

> Environment-specific values such as Key Vault details are resolved at deploy time by the Databricks Bundle - not by this script. You only need to run this script once regardless of how many environments you are deploying to.

---

## Step 3 - Deploy the Resources

Once the YAML definitions are generated, deploy them using Databricks Asset Bundle commands.

**To validate the bundle configuration before deploying:**

```bash
databricks bundle validate
```

**To preview changes without deploying:**

```bash
databricks bundle plan
```


**To deploy to a specific environment:**

```bash
databricks bundle deploy --target dev
databricks bundle deploy --target uat
databricks bundle deploy --target prod
```

These commands can be run locally or triggered from your CI/CD pipeline (Recommended to do from your CI/CD pipeline).

---

## Quick Reference - End to End

```
1. Open resource_configuration_variables.yml
2. Add your resource entry under sql_wh, all_purpose_cluster, or secrets
3. Run: python generate_resource_definitions.py
4. Run: databricks bundle validate
5. Run: databricks bundle deploy --target <environment>
```

---

## Need Help?

- **Sizing and compute type guidance** → [Compute Selection & Sizing Guide](./docs/compute_selection_sizing_guide.md)
- **Databricks Bundle documentation** → [Databricks Asset Bundles - Microsoft Learn](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/bundles/)
- **Azure VM sizes** → [Azure VM Sizes - Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes)
- **Azure Key Vault** → [Azure Key Vault - Microsoft Learn](https://learn.microsoft.com/en-us/azure/key-vault/general/overview)