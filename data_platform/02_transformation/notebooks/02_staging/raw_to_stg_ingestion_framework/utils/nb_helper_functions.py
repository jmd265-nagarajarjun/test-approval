# Databricks notebook source
# MAGIC %md
# MAGIC # Helper Functions
# MAGIC
# MAGIC This section contains all helper functions used for raw-to-staging data processing, cleansing, standardization, and transformations.
# MAGIC
# MAGIC - parse_column_configs
# MAGIC - get_col_mappings
# MAGIC - fill_column_with_default_value
# MAGIC - process_tags
# MAGIC - read_table
# MAGIC - write_table
# MAGIC - merge_upsert
# MAGIC - sanitize_column_name
# MAGIC - sanitize_all_columns
# MAGIC - rename_table_cols
# MAGIC - create_metadata_tables
# MAGIC - extract_run_config
# MAGIC - get_pipeline_config

# COMMAND ----------

# DBTITLE 1,parse_column_configs
def parse_column_configs(column_configs):
    """
    Parse column configurations, handling both dict and Row objects.
    """
    column_config_dict = {}
    for config in column_configs:
        if hasattr(config, "__fields__"):  # If it's a Row object
            config_dict = {field: getattr(config, field) for field in config.__fields__}
        else:
            config_dict = config
        column_config_dict[config_dict["column_name"].lower()] = config_dict
    return column_config_dict

# COMMAND ----------

# DBTITLE 1,get_col_mappings
def get_col_mappings(fully_qualified_src_table_name, table_config):
    """
    Returns a dictionary of column mappings for the given table.
    """
    mappings = {}
    tbl = spark.read.table(fully_qualified_src_table_name)
    mappings= sanitize_all_columns(tbl)
    
    if table_config is None or len(table_config) == 0 :
        return mappings
    
    col_mapping = {
        col_config["column_name"]: col_config["destination_column_name"]
        for col_config in table_config[0]["columns"]
        if col_config["destination_column_name"]
    }
    
    for key, value in col_mapping.items():
        if key in mappings:
            mappings[key] = col_mapping[key]

    return mappings

# COMMAND ----------

# DBTITLE 1,fill_default_values
def fill_column_with_default_value(sdf, column_name, default_value):
    """
    Replace null values in a column with a specified default value.
    """

    return sdf.withColumn(
        column_name,
        when(col(column_name).isNull(), lit(default_value))
        .otherwise(col(column_name))
    )

# COMMAND ----------

# DBTITLE 1,process_tags
def process_tags(tags_string):
    ## {key_1:val_1, key_2:val_2}
    tags_dict = dict(

        tag.split("=", 1)

        for tag in tags_string.split("|")

    )

    ## 'key_1' = 'val_1', 'key_2 = 'val_2'
    tag_pairs = ", ".join(

        [

            f"'{k.strip()}' = '{v.strip()}'"

            for k, v in tags_dict.items()

        ]

    )

    return tag_pairs

# COMMAND ----------

def read_table(fully_qualified_table_name):
    """
    Read a table from the metastore/catalog into a Spark DataFrame.
    fully_qualified_table_name = <catalog_name>.<schema_name>.<table_name>
    """
    return spark.read.table(f"{fully_qualified_table_name}")

def write_table(
    sdf,
    fully_qualified_table_name,
    mode="overwrite",
    schema_mode="overwrite"
):
    try:
        (
            sdf.write
            .format("delta")
            .mode(mode)
            .option("mergeSchema", "true" if schema_mode == "merge" else "false")
            .saveAsTable(fully_qualified_table_name)
        )

    except Exception as e:
        raise Exception(f"Error writing table {fully_qualified_table_name}. Error: {str(e)}") from e


def merge_upsert(sdf, fully_qualified_table_name, primary_keys):
    try:
        # -----------------------------------
        # Create table if not exists
        # -----------------------------------
        if not spark.catalog.tableExists(fully_qualified_table_name):

            (
                sdf.write
                .format("delta")
                .mode("overwrite")
                .saveAsTable(fully_qualified_table_name)
            )

            return

        # -----------------------------------
        # Create merge condition
        #
        # Example:
        # customer_id|country_code
        #
        # becomes:
        # t.customer_id = s.customer_id
        # AND
        # t.country_code = s.country_code
        # -----------------------------------
        merge_condition = " AND ".join(
            [
                f"t.{key.strip()} = s.{key.strip()}"
                for key in primary_keys.split("|")
            ]
        )

        # -----------------------------------
        # Load Delta Table
        # -----------------------------------
        delta_table = DeltaTable.forName(
            spark,
            fully_qualified_table_name
        )

        # -----------------------------------
        # Merge / Upsert
        # -----------------------------------
        (
            delta_table.alias("t")
            .merge(
                sdf.alias("s"),
                merge_condition
            )
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )

    except Exception as e:
        raise Exception(f"Error upserting table {fully_qualified_table_name}. Error: {str(e)}") from e

# COMMAND ----------

# DBTITLE 1,sanitize_and_rename_cols
def sanitize_column_name(col_name):
    """
    Convert a given string to snake_case.

    Steps:
    1. Replace all non-word characters (anything except a-z, A-Z, 0-9, _) with underscores.
    2. Add an underscore before any uppercase letter that follows a lowercase letter or digit.
       This helps convert camelCase to snake_case.
    3. Replace multiple consecutive underscores with a single underscore.
    4. Trim leading/trailing underscores.
    5. Convert the result to lowercase.

    Parameters:
        name (str): The input string to convert.

    Returns:
        str: The snake_case formatted string.
    """

    if col_name is None:
        return None
        
    prefix = ''
    if col_name.startswith('__'):
        prefix = '__'
        col_name = col_name[2:]

    col_name = re.sub(r'[^\w]', '_', col_name)
    col_name = re.sub(r'(?<=[a-z0-9])([A-Z])', r'_\1', col_name)
    col_name = re.sub(r'_+', '_', col_name)
    col_name = col_name.strip('_')
    col_name = col_name.lower()

    return prefix + col_name


def sanitize_all_columns(table_df):
    """
    Sanitizes column names by removing special characters, converting to lowercase,
    and replacing spaces with underscores.
    """
    return {col: sanitize_column_name(col) for col in table_df.columns}


def rename_table_cols(table_df, col_rename_mappings):
    """
    Finalizes the table by renaming columns.
    Parameters:
    - table_df: input DataFrame.
    - col_rename_mappings: dict of {source_column: destination_column or ""}
    """

    # Step 1: Rename columns
    for src_col, dest_col in col_rename_mappings.items():
        if not dest_col:
            dest_col = sanitize_column_name(src_col)
            col_rename_mappings[src_col] = dest_col
        try:
            if src_col != dest_col:
                table_df = table_df.withColumnRenamed(src_col, dest_col)
        except Exception as e:
            raise RuntimeError(
                f"Error renaming column {src_col} to {dest_col}"
            ) from e
    
    # Step 2: Select only valid columns
    return table_df.select([col for col in table_df.columns if len(col) > 1])

# COMMAND ----------

# DBTITLE 1,create_metadata_tables
def create_metadata_tables(metadata_catalog):
    # ----------------------------------------------------------
    # Configuration
    # ----------------------------------------------------------

    ## Target catalog and schema
    target_catalog = metadata_catalog

    # ----------------------------------------------------------
    # Create Schema
    # ----------------------------------------------------------
    # Create schema if it does not exist
    # Stores metadata/control tables and reference datasets
    
    spark.sql(f"""
        CREATE SCHEMA IF NOT EXISTS {target_catalog}.reference
    """)

    ## Volume folder containing CSV metadata files  /Volumes/<catalog_name>/<schema_name>/<volme_name>
    volume_path = f"/Volumes/{target_catalog}/reference/ingestion_configs"

    # ----------------------------------------------------------
    # Read All CSV Files from Volume
    # ----------------------------------------------------------

    csv_files = [
        file.path
        for file in dbutils.fs.ls(volume_path)
        if file.path.endswith(".csv")
    ]

    print("CSV Files Found")
    for file in csv_files:
        print(f"---> {file}")

    # ----------------------------------------------------------
    # Process Each CSV File
    # ----------------------------------------------------------

    for file_path in csv_files:

        # Extract table name from file name
        table_name = (
            file_path.split("/")[-1]
            .replace(".csv", "")
            .lower()
        )

        fully_qualified_table_name = f"{target_catalog}.reference.{table_name}"

        print("\n")
        print("--------------------------------------")
        print(f"Processing File : {file_path}")
        print(f"Creating Table  : {fully_qualified_table_name}")

        ## Read CSV
        df = (
            spark.read
            .option("header", True)
            .option("inferSchema", True)
            .option("multiLine", True)
            .option("escape", '"')
            .csv(file_path)
        )

        ## Write as Delta table
        (
            df.write
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .format("delta")
            .saveAsTable(
                f"{fully_qualified_table_name}"
            )
        )

        print(f"{fully_qualified_table_name} created successfully")
        print("--------------------------------------")

# COMMAND ----------

def extract_run_config(run_level, source_schema_names, source_table_names ,metadata_catalog):
    """
    ================================================================
    Configuration and Metadata Initialization
    ================================================================

    1. metadata_df  
    - Stores metadata definitions for staging tables.
    - Loaded from the metadata_staging table.

    2. config_df
    - Stores ingestion and transformation configuration details.
    - Loaded from the staging_pre_config table. 
    """

    metadata_df = spark.read.table(f"{metadata_catalog}.reference.metadata_staging")
    config_df = spark.read.table(f"{metadata_catalog}.reference.staging_pre_config")


    schema_names = (
    [schema.strip() for schema in source_schema_names.split(",")]
    if source_schema_names
    else []
    )

    # -----------------------------------
    # Widget Input
    # Example:
    # prep.cust, prep.orders
    # -----------------------------------
    table_inputs = (
        [source_table.strip() for source_table in source_table_names.split(",")]
        if source_table_names
        else []
    )

    # -----------------------------------
    # Extract schema and table names
    # -----------------------------------
    table_pairs = [
        tuple(x.split("."))
        for x in table_inputs
    ]

    if  run_level == 'schema':
        metadata_df = metadata_df.filter(
            (col("source_schema").isin(schema_names))
        )

    elif  run_level == 'table':
        filter_condition = None
        for schema_name, table_name in table_pairs:

            condition = (
                (col("source_schema") == schema_name) &
                (col("source_table_name") == table_name)
            )

            if filter_condition is None:
                filter_condition = condition
            else:
                filter_condition = (
                    filter_condition | condition
                )

        metadata_df = metadata_df.filter(
            filter_condition
        )

    ## Get only the active columns config 
    filtered_config_df = config_df.filter(
                (col("is_active") == 1)
            )

    ## Convert metadata DataFrame to list of dictionaries
    tables = [row.asDict() for row in metadata_df.collect() if row.asDict()]

    ## Group all the config defined for the table
    config_grouped = filtered_config_df.groupBy("catalog","schema", "table_name").agg(
            collect_list(struct("column_name","default_value","destination_column_name", "data_type", "date_format", "transformation_function", "transformation_args","column_description","tags","column_masking")).alias("columns")
    )

    return tables, config_grouped

# COMMAND ----------

def get_pipeline_config():

    ## Initialize log collection
    PIPELINE_LOGS = []

    ## Pipeline Run ID
    notebook_run_id = (
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}_"
        f"{uuid.uuid4().hex[:8]}"
    )

    ## Pipeline start time
    notebook_start_time =  datetime.now(ZoneInfo("Asia/Kolkata"))

    job_id = (
        dbutils.notebook.entry_point.getDbutils().notebook().getContext().jobId().get()
        if dbutils.notebook.entry_point.getDbutils().notebook().getContext().jobId().isDefined()
        else None
    )

    return PIPELINE_LOGS, notebook_run_id, notebook_start_time, job_id
