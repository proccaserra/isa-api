from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("material schema requires json to be installed")

material_schema = json.load(open(join(dirname(__file__), 'material_schema.json')))
