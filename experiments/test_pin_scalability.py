import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class ScalabilityTests(unittest.TestCase):
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
