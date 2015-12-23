from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("ontology source reference schema requires json to be installed")

ontology_source_reference_schema = json.load(open(join(dirname(__file__), 'ontology_source_reference_schema.json')))
