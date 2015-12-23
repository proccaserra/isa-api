from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("material attribute schema requires json to be installed")

material_attribute_schema = json.load(open(join(dirname(__file__), 'material_attribute_schema.json')))
