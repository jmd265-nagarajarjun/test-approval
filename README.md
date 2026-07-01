# Lakester - Databricks Data Platform Starter Kit

Building a data platform on Databricks follows the same journey for every team. You start by provisioning a **Workspace** (your Databricks environment), onboarding your **Users**, and creating a **Catalog** (where your data is organised and governed) - all via Terraform. Once that foundation is in place, you need **Compute** so people can run queries and process data, a way to securely store and access credentials (**Secret Scopes** backed by Azure Key Vault), somewhere to model and transform your data, and pipelines to reliably promote changes from Dev through to Production.

**Lakester picks up from Compute and gets you the rest, ready to go.**

---

## What Lakester Gives You

**A consistent development environment powered by a Dev Container** - Python, dbt Core, the Databricks CLI, Azure CLI, VS Code extensions, and pre-commit checks for code quality. Open the project in VS Code, choose *Reopen in Container*, and your environment is ready. Every engineer on the team gets the same setup.

**Compute and Secret Scopes via Declarative Automation Bundles (DABs)** - DABs is Databricks' native infrastructure-as-code tool that provisions and manages resources declaratively through YAML. Lakester ships with SQL Warehouses, All-Purpose Clusters, and an Azure Key Vault-backed Secret Scope pre-configured with sensible defaults, ready to deploy.

When deploying locally, DABs runs in **development mode** - all resources are created with your username as a prefix, so you can configure, test, and tear down without affecting anyone else. Once you're happy, raise a PR and the CI/CD pipeline takes it from there.

**A dbt Core project with a layered structure** - `staging → core → mart → curated` - pre-wired to your Databricks workspace. When running locally, schemas are automatically prefixed with your username so two engineers never overwrite each other's tables in development. In UAT and Production, plain schema names are used.

**A folder structure ready for ingestion** - since Lakeflow Connect doesn't support all source systems, Lakester provides the structure for custom connectors or third-party services to plug into.

**CI/CD pipelines for GitHub Actions and Azure DevOps** - PR validation, automatic Dev to UAT promotion, and Production release on tag.

---

## Prerequisites

| You Need | What It's For |
|---|---|
| **VS Code** with the Dev Containers extension | Opens the project in its ready-made environment |
| **Docker** | Runs the dev container. On Windows this runs through WSL |

---

## Getting Started

Open the project in VS Code and choose **Reopen in Container**.

### 1. Authenticate

Lakester uses Azure authentication rather than Databricks CLI auth - provisioning Key Vault-backed Secret Scopes requires an active Azure session:

```bash
az login
```

### 2. Configure your environments

Open `src/databricks.yml` and fill in the values for each target (`dev`, `uat`, `prod`):

| Setting | What it is |
|---|---|
| `host` | Your Databricks workspace URL |
| `keyvault_resource_id` | Azure resource ID of the Key Vault for this environment - used to create the Secret Scope |
| `keyvault_dns_name` | URI of the Key Vault (e.g. `https://<kv-name>.vault.azure.net/`) |
| `cluster_permissions` / `warehouse_permissions` / `secret_scope_permissions` | Who can access each resource - groups and users differ per environment, so these are set per target |

### 3. Deploy

```bash
cd src

# Validate your configuration first
databricks bundle validate

# Deploy to your personal dev environment (default target)
databricks bundle deploy
```

This deploys SQL Warehouses, All-Purpose Clusters, and a Secret Scope to the workspace. All resources are prefixed with your username in development mode, so nothing conflicts with a teammate's setup.

Once you've tested your configuration, raise a PR and the CI/CD pipeline handles deployment to `dev`, `uat`, and `prod`.

When you're done testing, clean up your personal resources:

```bash
databricks bundle destroy
```

---

## Documentation

**[Compute Selection & Sizing Guide](./docs/compute_selection_sizing_guide.md)** - not sure which compute type to use or how to size it? This guide tells you when to use SQL Warehouses vs All-Purpose Clusters, Classic vs Serverless, and what worker configuration to start with. Start here before creating any compute.

**[CI/CD Guide](./docs/ci_cd_guide.md)** - covers how the pipelines work, how to set up approval gates for UAT and Production, how to configure service principal authentication, and how to trigger a Production release. Read this before setting up your pipelines.

**External references**
- [Declarative Automation Bundles](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/bundles/)
- [dbt on Databricks](https://docs.getdbt.com/guides/databricks)
- [Ruff](https://docs.astral.sh/ruff/) · [SQLFluff](https://docs.sqlfluff.com/) · [Conventional Commits](https://www.conventionalcommits.org/)
