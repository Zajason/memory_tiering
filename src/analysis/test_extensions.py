import unittest
import gzip
import tempfile
from pathlib import Path
import numpy as np
import hotskew as H
from granularity_sweep import sweep_records, coarsen_popcount
from hotset_turnover import top_k_of_epoch
from causal_placement import candidates
from revalidate_extensions import epochs


class ExtensionTests(unittest.TestCase):
    def test_streaming_raw_and_gzip(self):
        r = np.zeros(32770, dtype=H.RECORD_DTYPE)
        r['epoch'][32769:] = 1
        with tempfile.TemporaryDirectory() as tmp:
            for suffix,opener in [('.bin',open),('.bin.gz',gzip.open)]:
                p=Path(tmp)/('records'+suffix)
                with opener(p,'wb') as f:f.write(r.tobytes())
                got=list(epochs(p))
                self.assertEqual([len(x) for x in got],[32769,1])
                np.testing.assert_equal(np.concatenate(got),r)

    def test_stream_rejects_truncation_and_epoch_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'records.bin'
            p.write_bytes(b'x')
            with self.assertRaises(ValueError):list(epochs(p))
            r=np.zeros(2,dtype=H.RECORD_DTYPE);r['epoch']=[0,2]
            p.write_bytes(r.tobytes())
            with self.assertRaises(ValueError):list(epochs(p))

    def test_grouping_high_addresses_and_epochs(self):
        r = np.zeros(3, dtype=H.RECORD_DTYPE)
        r['epoch'] = [0, 2**32-1, 2**32-1]
        r['page'] = [2**40, 2**40, 2**40+1]
        r['mask'] = [1, 1, 3]
        out = sweep_records(r)
        self.assertEqual(out[4096, 64]['pages'], 3)
        self.assertEqual(out[8192, 64]['pages'], 2)
        self.assertAlmostEqual(out[8192, 64]['mean_frac'], 2/128)

    def test_coarsening_known_bits(self):
        mask = np.array([0, 1, 3, 5, 2**64-1], dtype=np.uint64)
        np.testing.assert_equal(coarsen_popcount(mask, 128), [0,1,1,2,32])
        np.testing.assert_equal(coarsen_popcount(mask, 4096), [0,1,1,1,1])

    def test_turnover_ties_do_not_depend_on_record_order(self):
        r = np.zeros(4, dtype=H.RECORD_DTYPE)
        r['page'] = [40,10,30,20]
        r['reads'] = 10
        np.testing.assert_equal(top_k_of_epoch(r, 2), [10,20])
        np.testing.assert_equal(top_k_of_epoch(r[::-1], 2), [10,20])
        with self.assertRaises(ValueError): top_k_of_epoch(r, 0)

    def test_word_budget_ties_and_no_future_candidates(self):
        r = np.zeros(3, dtype=H.RECORD_DTYPE)
        r['page'] = [30,20,10]
        r['words'][:,0] = 2
        r['reads'] = [2,2,2]
        c = candidates(r, 1, words_per_page=1)
        self.assertEqual(c['count-only'], {10})
        self.assertEqual(c['hwt-driven'], {10})


if __name__ == '__main__': unittest.main()
