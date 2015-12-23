from os.path import dirname, join

try:
    import json
except ImportError as e:
    raise RuntimeError("comment schema requires json to be installed")

comment_schema = json.load(open(join(dirname(__file__), 'comment_schema.json')))
