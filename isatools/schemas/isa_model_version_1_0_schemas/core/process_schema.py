from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("process schema requires json to be installed")

process_schema = json.load(open(join(dirname(__file__), 'process_schema.json')))
