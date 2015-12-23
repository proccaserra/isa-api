from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("source schema requires json to be installed")

source_schema = json.load(open(join(dirname(__file__), 'source_schema.json')))
