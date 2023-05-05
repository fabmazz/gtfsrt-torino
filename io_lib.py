"""
Copyright (C) 2022  Fabio Mazza
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
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