#!/usr/bin/env python3
"""Move ignored raw records to the research HDD after SHA256 verification.

Original paths become symlinks, preserving recorded commands. Summaries and
source-controlled analysis files remain in the repository.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
DEST=Path('/mnt/research/memory-tiering/raw-records')

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    mount=json.loads(subprocess.check_output(['findmnt','-J','/mnt/research']))['filesystems'][0]
    if mount['target']!='/mnt/research' or mount['fstype']!='ext4':raise RuntimeError('research HDD is not mounted')
    DEST.mkdir(parents=True,exist_ok=True)
    for source in sorted((ROOT/'results').rglob('*.pages.bin*')):
        if source.is_symlink() or not source.is_file():continue
        if source.suffix not in ['.bin','.gz']:continue
        target=DEST/source.relative_to(ROOT/'results');target.parent.mkdir(parents=True,exist_ok=True)
        source_hash=sha(source)
        if target.exists():
            if sha(target)!=source_hash:raise ValueError(f'existing destination differs: {target}')
        else:
            partial=target.with_suffix(target.suffix+'.partial')
            shutil.copy2(source,partial)
            if sha(partial)!=source_hash:raise ValueError(f'copy verification failed: {source}')
            partial.replace(target)
        link=source.with_name(source.name+'.hdd-link')
        link.symlink_to(target)
        link.replace(source)
        target.with_suffix(target.suffix+'.sha256.json').write_text(json.dumps(
            dict(original=str(source),destination=str(target),sha256=source_hash,bytes=target.stat().st_size),indent=2)+'\n')
        print(f'VERIFIED AND MOVED {source.relative_to(ROOT)}',flush=True)

if __name__=='__main__':main()
