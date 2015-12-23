from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("person schema requires json to be installed")

person_schema = json.load(open(join(dirname(__file__), 'person_schema.json')))
