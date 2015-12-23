from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("assay schema requires json to be installed")

assay_schema = json.load(open(join(dirname(__file__), 'assay_schema.json')))
