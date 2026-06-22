# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # Env Config

# COMMAND ----------

dbutils.widgets.dropdown('metadata_catalog', 'analytics_dev_core', ['analytics_dev_core','analytics_prod_core'])
dbutils.widgets.dropdown('is_config_changed', 'no', ['yes','no']) 

# COMMAND ----------

# MAGIC %run ./reference/helper_functions

# COMMAND ----------

metadata_catalog = dbutils.widgets.get("metadata_catalog")
is_config_changed= dbutils.widgets.get("is_config_changed")

## Recreate the config table if config has changed
if is_config_changed.lower() == 'yes':
    ## Create metadata tables
    create_metadata_tables(metadata_catalog)
