from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("ontology annotation schema requires json to be installed")

ontology_annotation_schema = json.load(open(join(dirname(__file__), 'ontology_annotation_schema.json')))
