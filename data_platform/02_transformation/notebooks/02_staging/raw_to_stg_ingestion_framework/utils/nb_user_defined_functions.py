# Databricks notebook source
"""
Project-Specific Helper Functions
=================================

This section contains helper functions that are specific to individual
project requirements or business logic.

Functions defined here are generally not part of the reusable/common
ingestion framework and may vary across projects.

Important:
    Any new function added to this section must be registered in
    `_USER_DEFINED_TRANSFORMATION_FUNCTIONS_REGISTRY_`.

Typical use cases:
    - Data cleansing rules
    - Parsing logic

Examples:
    - Custom whitespace removal
    - Special extraction logic
"""

# COMMAND ----------

def register_transformation(func):
    """
    Register a transformation function in the
    USER_DEFINED_TRANSFORMATION_FUNCTIONS_REGISTRY.

    The function name is used as the registry key, allowing
    transformations to be referenced dynamically through metadata.

    Example:
        @register_transformation
        def remove_ws(sdf, column_name):
            ...

    Results in:
        USER_DEFINED_TRANSFORMATION_FUNCTIONS_REGISTRY["remove_ws"]
    """
    USER_DEFINED_TRANSFORMATION_FUNCTIONS_REGISTRY[func.__name__] = func
    return func

# COMMAND ----------

## Registry for custom transformation functions.
USER_DEFINED_TRANSFORMATION_FUNCTIONS_REGISTRY = {}

# COMMAND ----------

# DBTITLE 1,project_specific_helper_functions
@register_transformation
def remove_ws(sdf, column_name):
    """
    Clean string column by:
    1. Removing leading/trailing spaces.
    2. Removing special characters and numbers.
    3. Retaining only alphabets and spaces.
    """
    return sdf.withColumn(
        column_name,
        F.regexp_replace(
            F.trim(F.col(column_name)),
            "[^a-zA-Z ]",
            ""
        )
    )

@register_transformation
def extract_cust_details(sdf, column_name, position):
    """
    Extract a value from a semicolon-separated string column.

    Processing steps:
    1. Split column using semicolon (;).
    2. Extract value at specified position.
    3. Convert value to lowercase.
    4. Trim leading/trailing spaces.
    5. Replace empty strings with null.
    """

    # Convert position to integer
    position = int(position)

    return sdf.withColumn(
        column_name,

        # If extracted value is empty after trimming,
        # replace with null
        F.when(
            F.trim(
                F.lower(
                    F.split(F.col(column_name), ";")[position]
                )
            ) == "",
            None
        )

        # Otherwise return cleaned extracted value
        .otherwise(
            F.trim(
                F.lower(
                    F.split(F.col(column_name), ";")[position]
                )
            )
        )
    )
