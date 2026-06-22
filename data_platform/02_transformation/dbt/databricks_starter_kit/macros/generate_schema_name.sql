/* Macro to generate custom schema names */
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {% set catalog = node.database %}
    {% set username = env_var('DBT_USER') %}

    {% if  (username == 'service_principal')%}
        {%- if custom_schema_name is none -%}
            {{ default_schema }}
        {%- else -%}
            {{ custom_schema_name | trim }}
        {% endif %}
    {%- else -%}
        {%- if custom_schema_name is none -%}
            {% set schema_list = [username, default_schema] %}
            {% set schema_name = schema_list | join('_') %}
            {{ return(schema_name) }}
        {%- else -%}
            {% set schema_list = [username, custom_schema_name | trim] %}
            {% set schema_name = schema_list | join('_') %}
            {{ return(schema_name) }}
        {%- endif -%}
    {%- endif -%}
{%- endmacro %}
