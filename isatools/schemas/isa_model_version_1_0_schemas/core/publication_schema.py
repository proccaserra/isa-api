from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("publication requires json to be installed")

publication_schema = json.load(open(join(dirname(__file__), 'publication_schema.json')))
