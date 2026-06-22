# Databricks notebook source
# Assumes pyspark.sql.types has been imported
# by the calling notebook

# COMMAND ----------

# ----------------------------------------------------------
# Dependency Notice
#
# This notebook is intended to be loaded by the ingestion framework and is not
# designed to be executed independently.
#
# Assumes the calling notebook has already imported:
#
# from pyspark.sql.types import *
#
# ----------------------------------------------------------

# ----------------------------------------------------------
# Logger Schema Definition
# ----------------------------------------------------------
log_schema = StructType([
    StructField("notebook_run_id", StringType(), True),
    StructField("notebook_start_time", TimestampType(), True),
    StructField("pipeline_run_id", StringType(), True),
    # StructField("pipeline_start_time", StringType(), True),
    # StructField("Table_name", StringType(), True),
    StructField("status", StringType(), True),
    StructField("raw_table", StringType(), True),
    StructField("stg_table", StringType(), True),
    StructField("is_scd_enabled", BooleanType(), True),
    StructField("primary_key", StringType(), True),
    StructField("incremental_column", StringType(), True),
    StructField(
        "data",
        MapType(
            StringType(),
            MapType(StringType(), StringType())
        ),
        True
    ),
    StructField("table_processed_at", TimestampType(), True),
])

# COMMAND ----------

# DBTITLE 1,get_logger
# ----------------------------------------------------------
# Logger Configuration
# ----------------------------------------------------------

def get_logger():
    """
    Returns the shared ingestion logger.

    The logger is configured only once, even if this
    function is called multiple times.
    """

    logger = logging.getLogger("raw_to_staging")

    if not logger.handlers:

        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        logger.addHandler(handler)
    
    return logger

# COMMAND ----------

# DBTITLE 1,write_logs
# ----------------------------------------------------------
# Write Logs Function
# ----------------------------------------------------------

def write_logs(PIPELINE_LOGS,metadata_catalog):
    # ----------------------------------------------------------
    # Log Table
    # ----------------------------------------------------------
    ## Create log table where needed
    LOG_TABLE = f"{metadata_catalog}.reference.logs"

    if isinstance(PIPELINE_LOGS, list):
        log_df = spark.createDataFrame(
            data=PIPELINE_LOGS,
            schema=log_schema
        )

        (
            log_df.write
            .format("delta")
            .mode("append")
            .saveAsTable(LOG_TABLE)
        )

        logger.info(f"Logs written successfully to: {LOG_TABLE}")
    else:
        raise ValueError("PIPELINE_LOGS must be a list of dictionaries.")
