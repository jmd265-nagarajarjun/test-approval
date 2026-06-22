# Databricks notebook source
# MAGIC %md
# MAGIC # Type Casting Functions
# MAGIC
# MAGIC This section contains all type casting functions used for raw-to-staging.
# MAGIC
# MAGIC - cast_numeric
# MAGIC - transform_to_string 
# MAGIC - transform_to_timestamp
# MAGIC - transform_to_date

# COMMAND ----------

# DBTITLE 1,numeric_type_casting
# Mapping of supported numeric datatypes
# Key   -> Accepted datatype from configuration/metadata
# Value -> Spark SQL datatype used for casting
NUMERIC_TYPES = {
    "integer": "int",
    "int": "int",
    "bigint": "bigint",
    "float": "float",
    "double": "double"
}

def cast_numeric(df, column_name, target_type, default_value=None):
    """
    Optimized integer transformation.
    Removes regex checks and reduces to single projection.
    """
    cleaned_col = F.regexp_replace(
        F.trim(F.col(column_name).cast("string")),
        r"[,\s]",
        ""
    )

    casted_col = cleaned_col.cast(target_type)

    if default_value is not None:
        casted_col = F.coalesce(
            casted_col,
            F.lit(default_value).cast(target_type)
        )

    return df.withColumn(column_name, casted_col)

# COMMAND ----------

# DBTITLE 1,string_type_casting
def transform_to_string(table_df, column_name, default_value):
    """
    Transform column to string with proper cleaning.
    """
    return table_df.withColumn(
        column_name,
        F.when(
            F.col(f"`{column_name}`").isNotNull(),
            F.trim(F.col(f"`{column_name}`"))
        ).otherwise(F.lit(default_value) if default_value is not None else None)
    )

# COMMAND ----------

# DBTITLE 1,timestamp_type_casting
def transform_to_timestamp(table_df, column_name, default_value):
    """
    Transform column to timestamp with multiple format attempts.
    """
    ## Check if the column exists in the DataFrame
    if column_name not in table_df.columns:
        logger.info(f"Column {column_name} does not exist in the DataFrame.")
        return table_df
    
    timestamp_formats = [
        "yyyy-MM-dd'T'HH:mm:ss.SSSX",
        "yyyy-MM-dd'T'HH:mm:ssX",
        "yyyy-MM-dd HH:mm:ss",
        "MM-dd-yyyy HH:mm:ss a",
        "MM/dd/yyyy hh:mm:ss a",
        "MM/dd/yyyy HH:mm:ss"
    ]
    
    ## Try each format in sequence
    timestamp_conversion = F.lit(None)
    for fmt in timestamp_formats:
        timestamp_conversion = F.coalesce(
            timestamp_conversion,
            F.to_timestamp(F.col(column_name), fmt)
        )
    
    ## If the timestamp conversion fails, use the default value
    table_df = table_df.withColumn(
        column_name,
        F.coalesce(
            timestamp_conversion,
            F.lit(default_value) if default_value is not None else F.lit(None)
        )
    )
    
    ## Ensure that the column is correctly converted and no null values remain
    table_df = table_df.withColumn(
        column_name,
        F.when(F.col(column_name).isNull(), F.lit(default_value)).otherwise(F.col(column_name))
    )
    
    return table_df

# COMMAND ----------

# DBTITLE 1,date_type_casting
def transform_to_date(table_df, column_name, dest_date_format, default_value):
    """
    Optimized date transformation.
    Removes duplicate loops and Python UDF.
    """

    col_str = F.col(column_name).cast("string")

    master_formats = [
        "MM-dd-yy",
        "MM-dd-yyyy",
        "dd MMM yyyy",
        "yyyy-MM-dd",
        "MM/dd/yyyy",
        "dd/MM/yyyy",
        "yyyy/MM/dd",
        "dd-MM-yyyy",
        "MM/d/yyyy",
        "M/dd/yyyy",
        "M/d/yyyy",
        "yyyyMMdd"
    ]

    user_formats = (
        [fmt.strip() for fmt in dest_date_format.split(",") if fmt.strip()]
        if dest_date_format else []
    )

    ## Combine formats (user first, then missing master formats)
    all_formats = user_formats + [f for f in master_formats if f not in user_formats]

    ## Julian (5 digit) — native Spark logic (NO UDF)
    julian_col = F.when(
        col_str.rlike(r"^\d{5}$"),
        F.expr(
            f"date_add(to_date(concat('19', substring(`{column_name}`, 1, 2), '-01-01')), "
            f"cast(substring(`{column_name}`, 3, 3) as int) - 1)"
        )
    )

    ## yyyyMM → append 01
    yyyymm_col = F.when(
        col_str.rlike(r"^\d{6}$"),
        F.to_date(F.concat(col_str, F.lit("01")), "yyyyMMdd")
    )

    ## Try all formats using coalesce chain
    date_expr = None
    for fmt in all_formats:
        parsed = F.to_date(col_str, fmt)
        date_expr = parsed if date_expr is None else F.coalesce(date_expr, parsed)

    ## Final coalesce
    final_date = F.coalesce(
        julian_col,
        yyyymm_col,
        date_expr,
        F.lit(default_value).cast("date") if default_value else F.lit(None).cast("date")
    )

    return table_df.withColumn(column_name, final_date)
