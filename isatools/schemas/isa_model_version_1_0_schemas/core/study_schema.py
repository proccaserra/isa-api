from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("study schema requires json to be installed")

study_schema = json.load(open(join(dirname(__file__), 'study_schema.json')))
