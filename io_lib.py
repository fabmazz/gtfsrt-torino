import json
import gzip

def save_json_gzip(fpath, obj):
    with gzip.open(fpath, "wt") as f:
        json.dump(obj, f, indent=2)
