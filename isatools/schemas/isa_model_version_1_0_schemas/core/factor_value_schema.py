from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("factor value schema requires json to be installed")

factor_value_schema = json.load(open(join(dirname(__file__), 'factor_value_schema.json')))
