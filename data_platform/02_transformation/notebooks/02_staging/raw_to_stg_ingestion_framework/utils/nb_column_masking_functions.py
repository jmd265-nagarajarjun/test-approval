# Databricks notebook source
# MAGIC %md
# MAGIC # Env Config

# COMMAND ----------

dbutils.widgets.dropdown('env', 'dev', ['dev','prod'])
env = dbutils.widgets.get("env")

# COMMAND ----------

## Better to define all the masking funtions within a single catalog (metadata_catalog) and under reference schema
MASKING_CATALOG_NAME = f"analytics_{env}_core"

# COMMAND ----------

# DBTITLE 1,mask_rev
## create function in a single catalog in reference schema, no need to recreate the function in all layers
spark.sql(f"""
    CREATE OR REPLACE FUNCTION {MASKING_CATALOG_NAME}.reference.mask_rev(revenue INTEGER) 
    RETURNS INTEGER
    RETURN 
    CASE 
        WHEN is_member('admins') 
            THEN revenue
        ELSE  
            CAST(ROUND(FLOOR(RAND() * -3),2) AS INTEGER)
    END
""")

# COMMAND ----------

# DBTITLE 1,mask_age
## create function in a single catalog in reference schema, no need to recreate the function in all layers
spark.sql(f"""
    CREATE OR REPLACE FUNCTION {MASKING_CATALOG_NAME}.reference.mask_age(age INTEGER) 
    RETURNS INTEGER
    RETURN 
    CASE 
        -- WHEN is_member('{env}_hr_admin') 
        WHEN is_member('admins') 

            THEN age
        ELSE  
            0
    END
""")
