# DABs Deployment Guide

## What is DABs

Declarative Automation Bundles (DABs) lets you define Databricks resources - clusters, warehouses, secret scopes - as YAML files and deploy them using the Databricks CLI. Resources are versioned alongside your code, so changes are tracked, reviewable, and deployed consistently across environments.

---

## Repository Structure

```
src/
├── databricks.yml                              # Root config - environments, variables, permissions
└── 00_infra/
    └── resources/
        ├── compute/
        │   ├── clusters.yml                    # All-purpose cluster definitions
        │   └── warehouses.yml                  # SQL warehouse definitions
        └── secrets/
            └── secret_scopes.yml               # Azure Key Vault-backed secret scopes
```

---

## Step 1 - Configure databricks.yml

This is the first file you need to update. It holds the environment targets and all variables that flow into the resource definitions.

For each environment (`dev-local`, `dev`, `uat`, `prod`), update the following:

**Workspace host**

```yaml
workspace:
  host: "https://<your-workspace>.azuredatabricks.net/"
```

**Azure Key Vault details** - find these in Azure Portal → Key Vault → Overview

```yaml
variables:
  keyvault_resource_id: "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kv-name>"
  keyvault_dns_name: "https://<kv-name>.vault.azure.net/"
```

**Permissions** - set who can access clusters, warehouses, and secret scopes per environment

```yaml
  cluster_permissions:
    - group_name: your_group
      level: CAN_ATTACH_TO

  warehouse_permissions:
    - group_name: your_group
      level: CAN_USE

  secret_scope_permissions:
    - group_name: your_group
      level: READ
```

Supported principal types: `group_name`, `user_name`, `service_principal_name`

Permission levels:

| Resource | Levels |
|---|---|
| Cluster | `CAN_ATTACH_TO` · `CAN_RESTART` · `CAN_MANAGE` |
| Warehouse | `CAN_USE` · `CAN_MONITOR` · `CAN_MANAGE` |
| Secret Scope | `READ` · `WRITE` · `MANAGE` |

---

## Step 2 - Define Resources

### Clusters (`clusters.yml`)

All clusters inherit from a single template. The only required field is `cluster_name`. Override other fields only if you need something different from the defaults.

To add a new cluster:

```yaml
resources:
  clusters:
    my_cluster:
      <<: *cluster
      cluster_name: my_cluster
```

To override node size or worker count:

```yaml
    my_cluster:
      <<: *cluster
      cluster_name: my_cluster
      node_type_id: Standard_D8s_v5
      driver_node_type_id: Standard_D8s_v5
      autoscale:
        min_workers: 2
        max_workers: 8
```

Default template values: `Standard_D4s_v5` nodes · 1–3 workers · 25 min autotermination · Photon · User Isolation

---

### Warehouses (`warehouses.yml`)

Two templates are available depending on the warehouse type. The only required field is `name`.

| Template | Use when |
|---|---|
| `<<: *wh_serverless` | Serverless warehouse (spins up in seconds) |
| `<<: *wh_standard` | Classic or non-serverless PRO warehouse |

To add a new warehouse:

```yaml
resources:
  sql_warehouses:
    my_warehouse:
      <<: *wh_serverless
      name: my_warehouse
```

To override size or scale-out:

```yaml
    my_warehouse:
      <<: *wh_serverless
      name: my_warehouse
      cluster_size: Medium
      max_num_clusters: 6
```

Default template values: `Small` size · max 3 clusters · Photon enabled · Cost optimized

---

### Secret Scopes (`secret_scopes.yml`)

One Azure Key Vault-backed secret scope is created per environment. The scope name is automatically prefixed with the environment name:

```
dev_kv_secret_scope | uat_kv_secret_scope | prod_kv_secret_scope
```

No changes are needed here - the Key Vault details and permissions flow in automatically from `databricks.yml`.

---

## Step 3 - Authentication

**Local development** uses your personal Azure CLI login:

```bash
az login
```

The `dev-local` target is configured with `auth_type: azure-cli` so it picks up your credentials automatically.

**CI/CD environments** (`dev`, `uat`, `prod`) authenticate using a Service Principal. The pipeline injects credentials via the `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, and `ARM_TENANT_ID` secrets - no manual setup needed for those environments.

---

## Step 4 - Deploy

**Validate** - check for errors before deploying:

```bash
databricks bundle validate
```

**Deploy** - provision resources in your local target:

```bash
databricks bundle deploy
```

> In `development` mode, Databricks automatically prefixes all resource names with
> `[dev your_username]` - for example, `[dev abhishek] development` for a cluster.
> This lets you provision and test resources in your own isolated space without
> affecting others. Once everything looks good, raise a pull request and let the
> CI/CD pipeline handle deployment to the shared environments.

**Destroy** - tear down your local resources when done testing:

```bash
databricks bundle destroy
```

For `dev`, `uat`, and `prod` - raise a pull request and let CI/CD handle deployment. Do not deploy to shared environments manually.
