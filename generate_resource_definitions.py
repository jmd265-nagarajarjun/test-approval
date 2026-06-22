import yaml
from jinja2 import Template
import os
# import shutil

print(os.getcwd())

paths = {
    "sql_wh": "compute/sql_warehouse/",
    "transformation_sql_wh": "compute/sql_warehouse/",
    "all_purpose_cluster": "compute/all_purpose/",
    "secrets": "secrets/",
}

# load variables
with open("resource_configuration_variables.yml") as f:
    vars_data = yaml.safe_load(f)

folder_paths = [
    "./data_platform/03_orchestration/resources/compute/",
    "./data_platform/03_orchestration/resources/secrets/",
]

for folder_path in folder_paths:
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".yml"):
                file_path = os.path.join(root, file)
                try:
                    print(f"Deleting: {file_path}")
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

print("printing the keyss...")
print(vars_data.keys())

for key, value in vars_data.items():
    # Load template
    print()
    with open(
        os.getcwd()
        + f"/data_platform/03_orchestration/resources/configs/{key}_config.yml"
    ) as f:
        template = Template(f.read())

    for item in value:
        rendered_yaml = template.render(item)
        result = yaml.safe_load(rendered_yaml)

        output_path = f"data_platform/03_orchestration/resources/{paths[key]}{item.get('name')}.yml"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w") as f:
            yaml.dump(result, f, sort_keys=False)

        print(f"Created: {output_path}")
