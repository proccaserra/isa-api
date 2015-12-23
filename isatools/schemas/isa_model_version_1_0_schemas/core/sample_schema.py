from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("sample schema requires json to be installed")

sample_schema = json.load(open(join(dirname(__file__), 'sample_schema.json')))
