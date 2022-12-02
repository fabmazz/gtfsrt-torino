import json
import gzip

import io

def save_json_gzip(fpath, obj):
    with gzip.open(fpath, "wt") as f:
        json.dump(obj, f, indent=2)

def save_json_zstd(fpath, obj, level=10):
    import zstandard
    cctx = zstandard.ZstdCompressor(threads=-1,level=level)
    with open(fpath, "wb") as f:
        with cctx.stream_writer(f) as compressor:
            wr = io.TextIOWrapper(compressor, encoding='utf-8')
            json.dump(obj, wr)
            wr.flush()
            wr.close()