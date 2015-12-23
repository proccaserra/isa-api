from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("investigation schema requires json to be installed")

investigation_schema = json.load(open(join(dirname(__file__), 'investigation_schema.json')))
