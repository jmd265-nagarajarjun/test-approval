# Lakester - Databricks Data Platform Starter Kit

Lakester accelerates the setup of Azure Databricks projects by providing a standardized project structure, development environment, resource provisioning framework, code quality tooling, and CI/CD templates.

---

## Why Lakester?

Setting up a new Databricks project usually means redoing the same groundwork every time:

* Wiring up a consistent dev environment for every engineer
* Re-establishing linting and formatting standards
* Hand-writing compute and secret-scope definitions
* Building CI/CD pipelines from scratch

Lakester ships all of this preconfigured, so teams start with consistent practices and deliver faster.

---

## Prerequisites

You only need two things on your machine - everything else lives inside the dev container.

| You Need | What It's For |
|---|---|
| **VS Code** with the Dev Containers extension | Opens the project in its ready-made environment |
| **Docker** | Runs the dev container. On Windows this runs through **WSL**, which is all you need to set up |

You do **not** need to install Python, dbt, or the Databricks CLI yourself - the container brings all of them. See [What's Installed for Development](#whats-installed-for-development).

---

## Getting Started

Open the project in VS Code and choose **Reopen in Container**.

That's it. The container builds itself and, on first start, installs every tool, VS Code extension, and pre-commit hook automatically. When it finishes you have a complete, consistent Databricks development environment - the same one everyone else on the team gets.

---

## What's Installed for Development

The dev container installs and configures everything below for you, so every developer works with an identical setup.

| Category | What's Installed |
|---|---|
| **Language** | Python 3.11 |
| **dbt** | `dbt-core`, `dbt-databricks` (with profiles and project dirs pre-wired) |
| **Databricks CLI** | Installed in the container - you only need to authenticate it (see below) |
| **SQL tooling** | SQLFluff + the dbt templater |
| **Code quality** | Ruff, pre-commit, Commitizen |
| **Cloud / Git CLIs** | Azure CLI, GitHub CLI, Git |
| **VS Code extensions** | Databricks, dbt Power User, SQLFluff, Python/Pylance, Jinja, GitLens, Conventional Commits, Docker, Spell Checker |

Pre-commit hooks are installed automatically when the container starts, so code-quality checks run from your very first commit.

**Authenticating for Local Development** - the required CLIs are already installed in the dev container, but you must authenticate with Azure before deploying resources locally.

```bash
az login
```

Lakester uses Azure authentication when provisioning Databricks resources, including Azure Key Vault-backed Secret Scopes. Once authenticated, the Databricks CLI can use your Azure credentials automatically.

---

## The dbt Project

A ready-to-use dbt project lives at `data_platform/02_transformation/dbt/databricks_starter_kit`. It comes set up with:

* **A Databricks connection** using OAuth (in `.dbt/profiles.yml`) - you just fill in your workspace host.
* **A layered model structure** that mirrors a medallion-style flow: `02_staging` -> `03_core` -> `04_mart` -> `05_curated`.
* **User-based schema isolation.** When you run dbt locally, your schemas are automatically prefixed with your username, so your work never clashes with a teammate's. Within a layer like staging, each schema corresponds to a source system - so your `salesforce` staging models land in a schema named `kiran_salesforce`, while a teammate's land in `prem_salesforce`. This is handled by the `generate_schema_name` macro, driven by the `DBT_USER` variable the container sets for you. When running as a service principal in UAT or Production, plain schema names are used with no prefix (e.g. just `salesforce`).


---

## Compute & Secret Scope Creation

### Development Mode (`dev-local`)

Lakester includes a `dev-local` target configured with Databricks Asset Bundles development mode. Resources deployed through this target are automatically isolated per developer, allowing multiple engineers to work in the same workspace without conflicts.

`dev-local` is intended for personal development and testing only. Deployments to shared environments (`dev`, `uat`, and `prod`) should be performed through the CI/CD pipeline.

For details on deployment targets and environment promotion, see the [CI/CD Guide](./docs/ci_cd_guide.md).

---

**One-time setup - configure your targets.** Before deploying anything, open `data_platform/03_orchestration/databricks.yml` and fill in the per-environment values for each target (`dev`, `uat`, `prod`):

| Setting | What to put |
|---|---|
| `host` | Your workspace URL, e.g. `https://adb-<workspace-id>.azuredatabricks.net` |
| `keyvault_resource_id` / `keyvault_dns_name` | Azure Key Vault details for that environment, used by secret scopes |

> **Important - set your host.** Fill in the `host` for every target you plan to deploy to. The `dev` target ships with an example URL, so replace it with your own workspace. A deployment will fail against any target whose `host` is left blank.

**Then define and deploy your resources.** You define your compute - SQL Warehouses, All Purpose Clusters, and Secret Scopes - in **one** file, and a script turns it into the YAML that **Declarative Automation Bundles** (formerly Databricks Asset Bundles) deploy.

The following _databricks bundle commands_ should be run from the bundle directory:

```bash
cd data_platform/03_orchestration
```

```bash
# 1. Define your resources
#    Edit resource_configuration_variables.yml

# 2. Generate the YAML definitions
python generate_resource_definitions.py

# 3. Validate the bundle
databricks bundle validate

# 4. Preview the changes
databricks bundle plan --target dev

# 5. Deploy
databricks bundle deploy --target dev
```

You only ever edit `resource_configuration_variables.yml`. The files under `resources/configs/` are templates, and the files under `resources/compute/` and `resources/secrets/` are generated for you - don't edit those by hand.

For the full details, see:

* [Compute Selection & Sizing Guide](docs/compute_selection_sizing_guide.md) - which compute type to use and how to size it
* [Resource Provisioning Runbook](docs/databricks_resource_provisioning_runbook.md) - step-by-step guide to creating SQL Warehouses, All Purpose Clusters, and Secret Scopes

---

## Pre-Commit Checks & Linting

Pre-commit hooks run automatically before every commit (and are installed for you when the container starts), so problems get caught early without anyone having to remember to run anything.

**Linting** is the core of it:

* **SQLFluff** lints the **dbt SQL models**, using the dbt templater so Jinja is rendered correctly first. It can also auto-fix issues.
* **Ruff** lints and formats the **Python** code.

Alongside linting, the hooks also fix trailing whitespace and line endings, validate YAML, block large files and merge-conflict markers, and check that commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (via Commitizen).

To run all checks yourself at any time:

```bash
pre-commit run --all-files
```

**Linting notebooks inside Databricks:** Ruff runs against `.py` files through pre-commit, but to lint notebooks directly in Databricks, open `linter.py` in a Databricks notebook, point `root_dir` at your notebook folder, and run the cells. It shows a diff of suggested changes without altering anything unless you opt in.

---

## CI/CD Pipelines

Pipelines are available for both GitHub Actions (`.github/workflows/`) and Azure DevOps (`azure_pipelines/`).

| Pipeline | Trigger | Purpose |
|---|---|---|
| `pr-validate.yml` | Pull request targeting `main` | Validates the bundle configuration for the Dev environment - checks syntax, variable resolution, and resource definitions before merge |
| `ci.yml` | Merge to `main` | Deploys the bundle to Dev, then automatically promotes to UAT if Dev succeeds |
| `cd.yml` | New tag pushed (e.g. `v1.0.0`) | Deploys the bundle to Production |
| `dabs_template.yml` | Called by other pipelines | Reusable workflow that handles bundle validation, plan, and deployment - behaviour controlled by input parameters |

You can find the full release flow here: [CI/CD Guide](./docs/ci_cd_guide.md)

---

## Repository Structure

```
├── .devcontainer/                          # Dev container configuration
├── .github/workflows/                      # GitHub Actions CI/CD pipelines
├── azure_pipelines/                        # Azure DevOps CI/CD pipelines
├── data_platform/
│   ├── 01_ingestion/                       # Raw ingestion notebooks and batch jobs
│   ├── 02_transformation/
│   │   ├── dbt/databricks_starter_kit/     # dbt project
│   │   └── notebooks/                      # PySpark transformation notebooks
│   └── 03_orchestration/
│       ├── resources/
│       │   ├── compute/                    # Generated compute definitions
│       │   ├── configs/                    # Resource templates (do not edit)
│       │   └── secrets/                    # Generated secret scope definitions
│       └── databricks.yml                  # Bundle configuration
├── docs/
│   ├── compute_selection_sizing_guide.md            # Compute sizing and selection reference
│   └── databricks_resource_provisioning_runbook.md  # Step-by-step resource provisioning guide
├── .pre-commit-config.yaml                 # Pre-commit hook definitions
├── .sqlfluff                               # SQLFluff configuration
├── generate_resource_definitions.py        # Generates YAML resource definitions
├── linter.py                               # Notebook linting script (run in Databricks)
├── resource_configuration_variables.yml    # Define compute resources here
└── ruff.toml                               # Ruff linting configuration
```

---

## Documentation

- [Compute Selection & Sizing Guide](./docs/compute_selection_sizing_guide.md) - which compute type to use and how to size it
- [Resource Provisioning Runbook](./docs/databricks_resource_provisioning_runbook.md) - step-by-step resource provisioning

**External references**

- [Declarative Automation Bundles](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/bundles/)
- [dbt on Databricks](https://docs.getdbt.com/guides/databricks)
- [Ruff](https://docs.astral.sh/ruff/) · [SQLFluff](https://docs.sqlfluff.com/) · [Conventional Commits](https://www.conventionalcommits.org/)
