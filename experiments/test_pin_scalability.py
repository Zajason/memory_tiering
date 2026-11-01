import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import struct

HERE = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class ScalabilityTests(unittest.TestCase):
    def test_bottleneck_publisher_rejects_unfinished(self):
        path = HERE.parent/'src/analysis/publish_pin_bottleneck.py'
        spec = importlib.util.spec_from_file_location('publish_pin_bottleneck', path)
        publisher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(publisher)
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source/'study.json').write_text('{"status":"running"}')
            with self.assertRaises(ValueError): publisher.derive(source)

    def test_bottleneck_report_and_cutoff(self):
        study=module('profile_pin_bottleneck')
        report=study.parse_report('# header\n60.0%;600;6;hotskew.so;[.] ATOMIC_SpinLock\n'
                                  '30.0%;300;3;hotskew.so;[.] analyzeMemRef\n'
                                  '10.0%;100;1;[unknown];[.] 0x1234\n')
        self.assertEqual(report['total_samples'],10)
        self.assertEqual(report['category_percent']['synchronization symbols'],60)
        self.assertEqual(report['category_percent']['unresolved/JIT'],10)
        for symbol in ('LockInternal', 'UnlockInternal', 'OS_MutexLock', 'PIN_GetLock'):
            self.assertEqual(study.category('hotskew.so', symbol), 'synchronization symbols')
        self.assertEqual(study.category('hotskew.so', 'PIN_GetThreadData'),
                         'other tool-linked code')
        with self.assertRaises(ValueError): study.parse_report('# no samples')
        with tempfile.TemporaryDirectory() as temp:
            result=study.capture([sys.executable,'-c','import time;time.sleep(30)'],Path(temp)/'log',1)
            self.assertTrue(result['profile_cutoff'])

    def test_real_input_induction_and_measurement(self):
        pilot = module('validate_pin_real_input')
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source.sg'
            target = Path(temp)/'subset.sg'
            nodes = 16
            with source.open('wb') as stream:
                stream.write(struct.pack('<?qq', False, nodes*(nodes-1), nodes))
                stream.write(struct.pack('<17q', *[i*(nodes-1) for i in range(nodes+1)]))
                for u in range(nodes):
                    stream.write(struct.pack('<15i', *[v for v in range(nodes) if v != u]))
            meta = pilot.induce(source, target, 2)
            count = len(pilot.selected_nodes(nodes, 2))
            self.assertEqual(meta['directed_entries'], count*(count-1))
            with target.open('rb') as stream:
                self.assertEqual(struct.unpack('<?qq', stream.read(17)), (False, count*(count-1), count))
                self.assertEqual(struct.unpack(f'<{count+1}q', stream.read((count+1)*8)),
                                 tuple(i*(count-1) for i in range(count+1)))
                for u in range(count):
                    self.assertEqual(struct.unpack(f'<{count-1}i', stream.read((count-1)*4)),
                                     tuple(v for v in range(count) if v != u))
            with self.assertRaises(FileExistsError): pilot.induce(source, target, 2)
            result = pilot.measured([sys.executable,'-c','import time; time.sleep(30)'],Path(temp)/'log',1)
            self.assertEqual(result['status'], 'timeout')
            self.assertGreater(result['sampled_peak_process_group_rss_bytes'], 0)

    def test_campaign_hold(self):
        runner = module('run_pin_fidelity_stage2')
        self.assertTrue(runner.held_job({'multithread_hold':True}, ['--threads','20']))
        self.assertFalse(runner.held_job({'multithread_hold':True}, ['--scope','process']))
        self.assertFalse(runner.held_job({'multithread_hold':True}, ['--llc-ways','9']))
        self.assertFalse(runner.held_job({'multithread_hold':True}, ['--threads','1']))
        self.assertFalse(runner.held_job({}, ['--threads','20']))

    def test_bounded_completion_failure_timeout(self):
        validation = module('validate_pin_scalability')
        with tempfile.TemporaryDirectory() as temp:
            log=Path(temp)/'run.log'
            for command, expected in [('pass','complete'),('raise SystemExit(3)','failed'),
                                      ('import time; time.sleep(30)','timeout')]:
                result=validation.bounded([sys.executable,'-c',command],log,1)
                self.assertEqual(result['status'],expected)


if __name__=='__main__':unittest.main()
