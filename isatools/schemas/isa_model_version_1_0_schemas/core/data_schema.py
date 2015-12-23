from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("data schema requires json to be installed")

data_schema = json.load(open(join(dirname(__file__), 'data_schema.json')))
