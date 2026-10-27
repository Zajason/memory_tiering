"""Manifest-level checks: no mixed or partial campaign may become a full figure."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from plot_latest_fig4 import NAMES, preflight, check_reference


class UniformCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root/'results/matched-family/kron-traffic10'
        self.directory.mkdir(parents=True)
        self.base = dict(status='complete', returncode=0,
                         graph_family='synthetic Kronecker', graph_scale=23,
                         epoch_refs=0, epoch_traffic=10000000, threads=1,
                         trials=1, warm_setup=False, tool_sha256='same-binary',
                         command=['pin', '-l3_kb', '40960', '-l3_assoc', '10',
                                  '-paired', '1', '-epoch_refs', '0', '-epoch', '10',
                                  '-max_epochs', '0', '-warm_outside_roi', '0',
                                  '-roi_begin', 'hotskew_roi_begin',
                                  '-roi_end', 'hotskew_roi_end', '--', 'benchmark'])
        for name in NAMES:
            self.write(name, self.base)

    def write(self, name, meta):
        (self.directory/f'gapbs-{name}.manifest.json').write_text(json.dumps(meta))

    def test_accepts_complete_uniform_campaign(self):
        self.assertEqual(tuple(preflight(self.root, True)), NAMES)

    def test_rejects_manifest_mismatches(self):
        for key, value in [('status', 'running'), ('returncode', 1),
                           ('epoch_refs', 10000000), ('epoch_traffic', 0),
                           ('threads', 20), ('trials', 2), ('graph_scale', 21),
                           ('warm_setup', True), ('tool_sha256', 'different')]:
            with self.subTest(key=key):
                meta = dict(self.base, **{key: value})
                self.write('tc', meta)
                with self.assertRaises(ValueError):
                    preflight(self.root, True)
                self.write('tc', self.base)

    def test_rejects_command_manifest_disagreement(self):
        for knob, value in [('-l3_assoc', '9'), ('-l3_kb', '36864'),
                            ('-epoch_refs', '10000000'), ('-epoch', '0'),
                            ('-max_epochs', '1'), ('-warm_outside_roi', '1')]:
            with self.subTest(knob=knob):
                meta = copy.deepcopy(self.base)
                meta['command'][meta['command'].index(knob)+1] = value
                self.write('tc', meta)
                with self.assertRaises(ValueError):
                    preflight(self.root, True)
                self.write('tc', self.base)

    def test_rejects_duplicate_knob(self):
        meta = copy.deepcopy(self.base)
        meta['command'][1:1] = ['-epoch', '20']
        self.write('tc', meta)
        with self.assertRaises(ValueError):
            preflight(self.root, True)

    def test_baseline_provenance_is_not_backfilled(self):
        current = dict(self.base, input='/input.sg', input_bytes=100,
                       input_sha256='hash', executable_sha256='binary', roi='timed kernel')
        before = dict(current, epoch_refs=10000000, epoch_traffic=0)
        self.assertEqual(check_reference(before, current), 'sha256 matched')
        before['input_sha256'] = 'wrong'
        with self.assertRaises(ValueError):
            check_reference(before, current)
        del before['input_sha256']
        self.assertIn('not recorded', check_reference(before, current))
        changed = copy.deepcopy(before)
        changed['command'][changed['command'].index('-l3_assoc')+1] = '9'
        with self.assertRaises(ValueError):
            check_reference(changed, current)
        before['input_bytes'] = 99
        with self.assertRaises(ValueError):
            check_reference(before, current)


if __name__ == '__main__':
    unittest.main()
