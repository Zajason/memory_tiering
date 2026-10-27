#!/usr/bin/env python3
"""Download the four official KAIST Twitter chunks, retaining source hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

API = 'https://api.github.com/repos/ANLAB-KAIST/traces/releases/tags/twitter_rv.net'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory',type=Path)
    a=ap.parse_args(); a.directory.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(API) as f: release=json.load(f)
    assets=sorted((x for x in release['assets'] if x['name'].endswith('.gz')),key=lambda x:x['name'])
    if [x['name'] for x in assets] != [f'twitter_rv.net.{i:02d}.gz' for i in range(4)]:
        raise ValueError('unexpected release asset set')
    result={'release':release['html_url'],'release_id':release['id'],'assets':[],'m5_exact_input':False}
    for item in assets:
        dest=a.directory/item['name'];partial=dest.with_suffix('.gz.partial')
        if not dest.exists():
            subprocess.run(['curl','-fL','--retry','5','--continue-at','-',
                            '-o',str(partial),item['browser_download_url']],check=True)
            if partial.stat().st_size != item['size']:raise ValueError('asset size mismatch')
            partial.replace(dest)
        if dest.stat().st_size != item['size']:raise ValueError(f'wrong size: {dest}')
        subprocess.run(['gzip','-t',str(dest)],check=True)
        with dest.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        result['assets'].append(dict(name=item['name'],bytes=item['size'],sha256=digest,
                                     url=item['browser_download_url']))
        print(f"VERIFIED {item['name']}",flush=True)
    (a.directory/'source.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
