from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("process parameter value schema requires json to be installed")

process_parameter_value_schema = json.load(open(join(dirname(__file__), 'process_parameter_value_schema.json')))
