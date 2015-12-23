from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("factor schema requires json to be installed")

factor_schema = json.load(open(join(dirname(__file__), 'factor_schema.json')))
