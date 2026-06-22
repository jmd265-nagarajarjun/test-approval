```python
# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # Env Config

# COMMAND ----------

"""
Widget Configuration

Purpose:
Capture runtime parameters required for pipeline execution.
"""

dbutils.widgets.dropdown(
    'metadata_catalog',
    'analytics_dev_core',
    ['analytics_dev_core', 'analytics_prod_core']
)

dbutils.widgets.dropdown(
    "run_level",
    "all",
    ["all", "schema", "table"]
)

# -----------------------------------
# Schema Input
# Enter schema names separated by commas.
# If run level is set to "all", no schema names
# are required and all tables will be processed.
# -----------------------------------
dbutils.widgets.text("source_schema_names", "")

# -----------------------------------
# Table Input
# Enter table names as comma-separated values
# in the format:
# schema.table_name
#
# Example:
# prep.customer,finance.invoice
#
# All specified tables will be processed.
# -----------------------------------
dbutils.widgets.text("source_table_names", "")

# COMMAND ----------

"""
Load Shared Functions

Purpose:
Import reusable helper functions used for configuration
extraction, table processing and logging.
"""
# MAGIC %run ./nb_stg_final

# COMMAND ----------

"""
Read Runtime Parameters

Purpose:
Retrieve widget values supplied for the current notebook run.
"""
run_level = dbutils.widgets.get("run_level")
source_schema_names = dbutils.widgets.get("source_schema_names")
source_table_names = dbutils.widgets.get("source_table_names")
metadata_catalog = dbutils.widgets.get("metadata_catalog")

# COMMAND ----------

"""
Extract Run Configuration

Purpose:
Build the execution configuration and determine
the list of tables to be processed.
"""
tables, config_object = extract_run_config(
    run_level,
    source_schema_names,
    source_table_names,
    metadata_catalog
)

# COMMAND ----------

"""
Process Configured Tables

Purpose:
Execute processing for all configured tables and
return execution logs along with processing status.
"""
PIPELINE_LOGS, error_flag = process_configured_tables(
    tables,
    config_object,
    metadata_catalog
)

# COMMAND ----------

"""
Write Logs

Purpose:
Persist pipeline execution logs for auditing,
monitoring and troubleshooting.
"""
if PIPELINE_LOGS:
    write_logs(PIPELINE_LOGS)

"""
Error Handling

Purpose:
Fail notebook execution when one or more table
loads encounter errors.
"""
if error_flag == 1:
    raise Exception(
        "One or more tables failed to load.. please refer to logs for more information"
    )
```
