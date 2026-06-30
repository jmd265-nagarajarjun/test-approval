# CI/CD Guide

This guide covers the CI/CD pipeline setup, how each pipeline works, and how to deploy resources across environments.

---

## Branching Strategy

This pipeline is built around **GitHub Flow** - a simple, lightweight branching strategy where `main` is always deployable and all work happens on short-lived feature branches.

```
main branch
    │
    ├── feature/my-change ──── PR ──── Validation (no deployment)
    │                               ↓
    │                          Merge to main ──── Deploy to Dev → UAT
    │                               ↓
    │                          git tag v1.0.0 ──── Deploy to Production
```

**Core principles:**

- `main` is always in a deployable state
- All changes go through a pull request - no direct commits to `main`
- Merges to `main` trigger automated deployments through the CI/CD pipeline
- Production deployments are intentional and triggered through version tags

> GitHub Flow is intentionally simple and works well for most data platform teams. We recommend sticking with this strategy - it reduces overhead, keeps the pipeline straightforward, and ensures `main` is always in a releasable state.

---

## Overview

The pipeline flow is designed around three stages - validation, deployment to Dev and UAT, and finally Production. Production deployments are intentional and require a tag to be created manually.

```
Pull Request raised
        ↓
pr-validate.yml - Validates bundle against Dev (no deployment)
        ↓
Merged to main
        ↓
ci.yml - Deploys to Dev, then UAT sequentially (UAT only runs if Dev succeeds)
        ↓
Production release created using a tag (e.g. v1.0.0)
        ↓
cd.yml - Deploys to Production
```

---

## Pipelines

Both GitHub Actions (`.github/workflows/`) and Azure DevOps (`azure_pipelines/`) pipelines are available and follow the same flow.

### `pr-validate.yml` - PR Validation

**Trigger:** Pull request targeting `main` with changes in `data_platform/03_orchestration/**`

Validates the bundle configuration against the Dev environment before any merge is allowed. This catches syntax errors, missing variables, and invalid resource definitions early - before they reach shared environments.

It does **not** deploy anything.

### `ci.yml` - Dev & UAT Deployment

**Trigger:** Merge to `main` with changes in `data_platform/03_orchestration/**`

Deploys the bundle sequentially:

1. Validates and deploys to **Dev**
2. If Dev succeeds, validates and deploys to **UAT**
3. If Dev fails, UAT deployment is skipped

### `cd.yml` - Production Deployment

**Trigger:** New tag pushed matching `v*` (e.g. `v1.0.0`, `v2.1.0`)

Deploys the bundle to **Production**. This is intentionally decoupled from the CI pipeline - a tag must be created and pushed manually to trigger a Production deployment.

To deploy to Production:

```bash
git tag v1.0.0
git push origin v1.0.0
```

### `dabs_template.yml` - Reusable Workflow

**Trigger:** Called by other pipelines (`workflow_call`)

A reusable workflow that handles bundle validation, plan, and deployment. All other pipelines call this template and pass the target environment and deploy flag as inputs.

| Input | Description |
|---|---|
| `environment` | Target environment (`dev`, `uat`, `prod`) |
| `deploy` | `true` to validate and deploy, `false` to validate only |

---

## Approval Gates

Deployments to UAT and Production require manual approval before they proceed.

### GitHub Actions

Approvals are configured using GitHub Environments with required reviewers.

Three environments must be created before running the pipelines:

**Navigate to:** Repository → Settings → Environments → New environment

| Environment | Used By | Approval Required |
|---|---|---|
| `dev` | CI pipeline (Dev stage), PR validation | No |
| `uat-approval` | CI pipeline (UAT stage) | Yes |
| `prod-approval` | CD pipeline (Production stage) | Yes |

To configure approvals on `uat` and `prod`:

1. Go to **Settings → Environments** and select the environment
2. Under **Protection rules**, enable **Required reviewers**
3. Add the required approvers (users or groups)
4. Click **Save protection rules**

### Azure DevOps

Approvals are configured using Azure DevOps Environments with approval rules.

Three environments must be created before running the pipelines:

**Navigate to:** Pipelines → Environments → New environment → Resource: None

| Environment | Used By | Approval Required |
|---|---|---|
| `dev` | CI pipeline (Dev stage), PR validation | No |
| `uat-approval` | CI pipeline (UAT stage) | Yes |
| `prod-approval` | CD pipeline (Production stage) | Yes |

> The `dev` environment has no approval rules - Dev deployments run automatically. It must still be created manually to avoid pipeline failures, as Azure DevOps does not reliably auto-create environments when pipelines are triggered from external code editors.

To configure approvals on `uat-approval` and `prod-approval`:

1. Go to **Pipelines → Environments** and select the environment
2. Click **...** (top right) → **Approvals and checks** → **+**
3. Select **Approvals** → **Next**
4. Add the required approvers (users or groups)
5. Set a timeout (recommended: 24 hours)
6. Click **Create**

### How It Works

When a pipeline run reaches a UAT or Production stage, it pauses and notifies the approvers. The deployment only proceeds once an approver reviews and approves the run.

---

## Authentication

The pipelines authenticate using **Microsoft Entra ID service principal authentication** (`ARM_*` environment variables). The Databricks CLI automatically detects Microsoft Entra ID service principal authentication when the `ARM_*` environment variables are present. The target workspace is defined in `databricks.yml`, so no additional authentication configuration is required.

This approach is used specifically because it supports both:
- Deploying Databricks resources (SQL Warehouses, All Purpose Clusters, Job Clusters)
- Creating **Azure Key Vault-backed Secret Scopes** - which require Azure Entra ID credentials since they interact directly with Azure resources, not just Databricks

The credentials required are:
- `ARM_CLIENT_ID` - the Microsoft Entra ID service principal's application ID
- `ARM_CLIENT_SECRET` - the client secret of the service principal
- `ARM_TENANT_ID` - the Microsoft Entra ID tenant ID

Reference: [Microsoft Entra ID service principal authentication - Microsoft Learn](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/azure-sp)

---

## Secrets Configuration

The following secrets must be configured before the pipelines will work.

### GitHub Actions

**GitHub** → Settings → Secrets and Variables → Actions

Seven secrets are required in total - two per environment for the service principal credentials, and one shared tenant ID:

| Secret Pattern | Description |
|---|---|
| `<ENV>_ARM_CLIENT_ID` | Service principal client ID |
| `<ENV>_ARM_CLIENT_SECRET` | Service principal client secret |
| `ARM_TENANT_ID` | Microsoft Entra ID tenant ID |

Where `<ENV>` is one of:

- `DEV`
- `UAT`
- `PROD`

### Azure DevOps

**Azure DevOps** → Pipelines → Library → Variable groups

Unlike GitHub Actions, Azure DevOps uses per-environment **variable groups** rather than a flat secret list. Four variable groups are required in total:

| Variable Group | Used By | Contains |
|---|---|---|
| `DEV-Databricks-Secrets` | PR validation, CI pipeline (Dev stage) | `DEV_ARM_CLIENT_ID`, `DEV_ARM_CLIENT_SECRET` |
| `UAT-Databricks-Secrets` | CI pipeline (UAT stage) | `UAT_ARM_CLIENT_ID`, `UAT_ARM_CLIENT_SECRET` |
| `PROD-Databricks-Secrets` | CD pipeline (Production stage) | `PROD_ARM_CLIENT_ID`, `PROD_ARM_CLIENT_SECRET` |
| `ARM-Tenant` | All pipelines (shared) | `ARM_TENANT_ID` |


Each pipeline references its environment-specific group plus the shared `ARM-Tenant` group in its `variables` section, e.g.:

```yaml
variables:
- group: DEV-Databricks-Secrets
- group: ARM-Tenant
```

The `ARM_CLIENT_ID` and `ARM_CLIENT_SECRET` values are then passed into the reusable template as explicit parameters (`armClientId`, `armClientSecret`), while `ARM_TENANT_ID` is referenced directly inside the template as `$(ARM_TENANT_ID)`, since it's available to any pipeline that includes the `ARM-Tenant` group.

> The `ARM_CLIENT_SECRET` is generated from the **Azure Portal** under the App Registration for your service principal (Certificates & Secrets → New client secret). The `ARM_CLIENT_ID` is the Application (client) ID shown on the App Registration overview page.

---

## Deployment Targets

There are four targets defined in `databricks.yml`. Each serves a different purpose.

| Target | Mode | Who Uses It | Purpose |
|---|---|---|---|
| `dev-local` | `development` | Developers locally | Personal isolated development and testing |
| `dev` | `production` | CI/CD pipeline | Shared Dev environment |
| `uat` | `production` | CI/CD pipeline | UAT environment for pre-production validation |
| `prod` | `production` | CI/CD pipeline | Production environment |

### Development Mode (`dev-local`)

`dev-local` uses Databricks `mode: development`, which automatically prefixes all resource names with the current user's short name:

```
dev-local deploy by john@company.com → [dev john]transformation_wh
```

This means each developer gets their own isolated copy of all resources in the same workspace - no conflicts, no risk of overwriting a colleague's resources.

This is the **default target**. Running any bundle command without `--target` uses `dev-local`:

```bash
# These are equivalent
databricks bundle deploy
databricks bundle deploy --target dev-local
```

> > `dev-local` is intended for personal development and testing. Shared environment deployments should be performed through the CI/CD pipeline. To avoid leaving unnecessary resources running, it is recommended to destroy `dev-local` resources once testing is complete.
---

## Local Deployment

Use the following commands when deploying from your local machine.

**Validate the bundle:**

```bash
databricks bundle validate
```

**Plan - see what will be created, updated, or deleted:**

```bash
databricks bundle plan
```

**Preview resources and resolved names before deploying:**

```bash
databricks bundle summary
```

**Deploy to your personal dev environment:**

```bash
databricks bundle deploy
```

**Destroy your personal dev resources when no longer needed:**

```bash
databricks bundle destroy
```

> Always run `databricks bundle destroy` when you are done testing to avoid leaving idle resources running in the workspace.

---

## Further Reading

- [Declarative Automation Bundles - Microsoft Learn](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/bundles/)
- [Bundle Development Mode - Databricks Docs](https://docs.databricks.com/en/dev-tools/bundles/deployment-modes.html)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)
