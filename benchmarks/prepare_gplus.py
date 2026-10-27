#!/usr/bin/env python3
"""Extract a published Google+ temporal snapshot, not M5's unavailable reduction.

Source format: from-node, to-node, first-seen TimeID (NOT an edge weight).
Select TimeID < snapshot, preserve vertex IDs and edge direction. No arbitrary
edge-prefix truncation, symmetrization or reference-curve-based selection.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import zipfile

SOURCE = 'https://people.duke.edu/~zg70/gplus.html'
EXPECTED = {1: 47130325, 2: 271915755, 3: 410445770, 4: 462994069}


def select_edges(source, target, snapshot):
    count = kept = 0
    max_node = -1
    for raw in source:
        fields = raw.split()
        if len(fields) != 3:
            raise ValueError(f'Expected three columns at row {count + 1}')
        u, v, timestamp = map(int, fields)
        if not (0 <= u < 2**31 and 0 <= v < 2**31 and 0 <= timestamp <= 3):
            raise ValueError(f'Invalid ID or TimeID at row {count + 1}')
        count += 1
        if timestamp < snapshot:
            target.write(f'{u}\t{v}\n')
            kept += 1
            max_node = max(max_node, u, v)
        if count % 50000000 == 0:
            print(f'Scanned {count:,} edges; retained {kept:,}', flush=True)
    return dict(input_edges=count, selected_edges=kept, max_node_id=max_node)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('archive', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--snapshot', type=int, choices=range(1, 5), default=1)
    args = ap.parse_args()
    manifest = args.output.with_suffix('.source.json')
    partial = args.output.with_suffix('.el.partial')
    if any(p.exists() for p in (args.output, manifest, partial)):
        ap.error('Output exists; use a new path rather than overwrite provenance')
    started = time.time()
    with args.archive.open('rb') as f:
        archive_hash = hashlib.file_digest(f, 'sha256').hexdigest()
    with ExitStack() as stack:
        archive = stack.enter_context(zipfile.ZipFile(args.archive))
        nested = [n for n in archive.namelist()
                  if Path(n).name == 'direct_social_structure.zip']
        nested_name = None
        if nested:
            if len(nested) != 1:
                raise ValueError('Ambiguous nested social-edge archive')
            nested_name = nested[0]
            temporary = stack.enter_context(tempfile.TemporaryFile(dir=args.output.parent))
            with archive.open(nested_name) as source:
                shutil.copyfileobj(source, temporary, length=1024*1024)
            temporary.seek(0)
            archive = stack.enter_context(zipfile.ZipFile(temporary))
        members = [n for n in archive.namelist()
                   if Path(n).name == 'direct_social_structure.txt']
        if len(members) != 1:
            raise ValueError(f'Expected one social-edge member; found {members}; '
                             f'archive members: {archive.namelist()}')
        member = members[0]
        with archive.open(member) as source, partial.open('x') as target:
            stats = select_edges(source, target, args.snapshot)
    if stats['selected_edges'] != EXPECTED[args.snapshot]:
        raise ValueError(f'Published snapshot edge count differs: {stats}')
    partial.replace(args.output)
    with args.output.open('rb') as f:
        output_hash = hashlib.file_digest(f, 'sha256').hexdigest()
    metadata = dict(source_url=SOURCE, archive_sha256=archive_hash,
                    member=member, nested_member=nested_name,
                    snapshot=args.snapshot, rule=f'TimeID < {args.snapshot}',
                    output_sha256=output_hash, directed=True, relabelled=False,
                    weights='none; TimeID removed, never treated as distance',
                    m5_exact_input=False, elapsed_s=time.time()-started, **stats)
    manifest.write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
