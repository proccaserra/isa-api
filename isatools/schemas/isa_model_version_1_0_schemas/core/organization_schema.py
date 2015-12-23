from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("organization schema requires json to be installed")

organization_schema = json.load(open(join(dirname(__file__), 'organization_schema.json')))
