import os

import yaml

basedir = os.getcwd()
local_path = os.path.abspath(
    os.path.join(basedir, "stacks", "secret_provider_class_test.yaml")
)

with open(local_path, "r") as yaml_in:
    yaml_file = yaml.safe_load(yaml_in)

print(yaml_file)
