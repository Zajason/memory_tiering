import gzip
import json
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest

class TwitterPreparationTest(unittest.TestCase):
    def test_induced_edges_and_ascending_relabelling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binary=root/'prepare'
            subprocess.run(['g++','-std=c++17','-O2',str(Path(__file__).with_name('prepare_twitter.cpp')),
                            '-lz','-o',str(binary)],check=True)
            edges=[(i,(i+1)%10) for i in range(10)]+[(6,9)]
            # Release chunks are concatenated byte streams, not independent lists.
            payload=''.join(f'{u} {v}\n' for u,v in edges)
            cuts=[0,1,7,23,len(payload)]
            for i in range(4):
                with gzip.open(root/f'twitter_rv.net.{i:02d}.gz','wt') as f:
                    f.write(payload[cuts[i]:cuts[i+1]])
            main=root/'main.el';tc=root/'tc.el'
            run=subprocess.run([str(binary),str(root),str(main),str(tc),'10','11'],
                               check=True,capture_output=True,text=True)
            meta=json.loads(run.stdout)
            self.assertEqual((meta['main_nodes'],meta['tc_nodes']),(8,2))
            self.assertEqual(set(main.read_text().splitlines()),
                             {'0 1','1 2','2 3','3 4','4 5','6 7','5 7','7 7'})
            self.assertEqual(tc.read_text(),'0 1\n1 1\n')
            converter=Path(__file__).resolve().parents[1]/'workloads/gapbs/converter'
            if converter.exists():
                subprocess.run([str(converter),'-f',str(main),'-s','-b',str(root/'main.sg')],
                               check=True,capture_output=True)
                with (root/'main.sg').open('rb') as f:header=struct.unpack('<?qq',f.read(17))
                self.assertEqual(header,(False,14,8))
            rejected=subprocess.run([str(binary),str(root),str(root/'bad.el'),str(root/'bad-tc.el')],
                                    capture_output=True)
            self.assertNotEqual(rejected.returncode,0)
            self.assertFalse((root/'bad.el').exists())
            payload='1 0\n6 0\n9 0\n'
            for i in range(4):
                with gzip.open(root/f'twitter_rv.net.{i:02d}.gz','wt') as f:
                    f.write(payload[i*3:(i+1)*3])
            isolated=root/'isolated.el'
            subprocess.run([str(binary),str(root),str(isolated),str(root/'isolated-tc.el'),'4','3'],
                           check=True,capture_output=True)
            self.assertEqual(isolated.read_text(),'2 2\n')
            if converter.exists():
                subprocess.run([str(converter),'-f',str(isolated),'-s','-b',str(root/'isolated.sg')],
                               check=True,capture_output=True)
                with (root/'isolated.sg').open('rb') as f:header=struct.unpack('<?qq',f.read(17))
                self.assertEqual(header,(False,0,3))

if __name__=='__main__':unittest.main()
