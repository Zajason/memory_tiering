"""Exercise full-process and kernel scope on a tiny real instrumented benchmark."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/analysis'))
import hotskew as H

class ScopeTests(unittest.TestCase):
    def test_scope_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);graph=root/'tiny.sg'
            subprocess.run([str(ROOT/'workloads/gapbs/converter'),'-g','10','-s','-b',str(graph)],
                           check=True,capture_output=True)
            manifests=[];references=[]
            for scope in ['kernel','process']:
                directory=root/scope
                result=subprocess.run([sys.executable,str(ROOT/'experiments/run_paired.py'),'bfs',
                    '--graph-prefix',str(graph.with_suffix('')),'--graph-family','scope smoke test',
                    '--epoch-traffic','1','--scope',scope,'--out',str(directory)],capture_output=True,text=True)
                if result.returncode:
                    log=directory/'gapbs-bfs.run.log'
                    self.fail(result.stdout+result.stderr+(log.read_text() if log.exists() else ''))
                meta=json.loads((directory/'gapbs-bfs.manifest.json').read_text())
                self.assertEqual(meta['status'],'complete');self.assertEqual(meta['scope'],scope)
                if scope=='kernel':
                    self.assertEqual(meta['command'][meta['command'].index('-roi_begin')+1],'hotskew_roi_begin')
                else:self.assertNotIn('-roi_begin',meta['command'])
                manifests.append(meta)
                summary=H.load_summary(directory/'gapbs-bfs.summary.txt')
                references.append(int(summary['mem_refs_profiled'].split()[0]))
            self.assertNotEqual(manifests[0]['roi'],manifests[1]['roi'])
            self.assertGreater(references[1],references[0])

if __name__=='__main__':unittest.main()
