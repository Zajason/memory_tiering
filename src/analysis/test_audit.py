import tempfile
import unittest
from pathlib import Path
import numpy as np
import hotskew as H
from window_fit import cdf_at_merge, error_for
from plot_paired import read_hist
from causal_placement import candidates, fixed_capacity

class AuditTests(unittest.TestCase):
    def test_placement_cannot_discard_future_cold_pages(self):
        prev = np.zeros(2, dtype=H.RECORD_DTYPE)
        prev['page'] = [10,20]; prev['reads'] = [100,1]
        prev['words'][:,0] = [100,1]
        selected = candidates(prev, 1)
        # Even if page 10 disappears next epoch, the selection cannot know that.
        self.assertEqual(selected['count-only'], {10})
        self.assertEqual(selected['hwt-driven'], {10})
        self.assertEqual(candidates(prev, 1, tracker={'hpt':[],'hwt':[]})['count-only'], set())

    def test_paper_prose_complement_is_47(self):
        self.assertEqual(error_for('gapbs-sssp', {47:.11,48:.9}), 0)
        self.assertAlmostEqual(error_for('gapbs-pr', {47:.12,48:.02}), .10)

    def test_union_not_sum_and_high_addresses(self):
        r = np.zeros(3, dtype=H.RECORD_DTYPE)
        r['epoch'] = [0, 1, 0]
        r['page'] = [9, 9, (1 << 40) + 9]
        r['mask'] = [1, 2, 7]
        self.assertAlmostEqual(cdf_at_merge(r, 2, ns=(1,2,3))[2], .5)
        self.assertEqual(cdf_at_merge(r, 1, ns=(1,))[1], 2/3)
        self.assertIsNone(cdf_at_merge(r[:0], 1))
        with self.assertRaises(ValueError): cdf_at_merge(r, 0)

    def test_dump_layout_and_completeness(self):
        self.assertEqual(H.RECORD_DTYPE.itemsize, 164)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'run.pages.bin'
            r = np.zeros(1, dtype=H.RECORD_DTYPE)
            r['reads'] = 3
            r.tofile(p)
            summary = Path(d)/'run.summary.txt'
            summary.write_text('page_observations 1\ndram_accesses 3\n')
            self.assertEqual(len(H.load_pages(p, require_complete=True).records), 1)
            summary.write_text('page_observations 2\ndram_accesses 3\n')
            with self.assertRaises(ValueError): H.load_pages(p, require_complete=True)
            summary.write_text('pages_bin_capped yes\npage_observations 1\ndram_accesses 3\n')
            with self.assertRaises(ValueError): H.load_pages(p, require_complete=True)

    def test_summary_sections(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'summary.txt'
            p.write_text('# full unique-word histogram (words,pages)\n1,2\n'
                         '# N, hpt_access_ratio, hwt_access_ratio\n512,0.5,0.7\n'
                         '# M5 Figure 10: histogram\n# (log2_bucket, pages)\n2,3\n')
            data = H.load_summary(p)
            self.assertEqual(data['_unique_hist'].sum(), 2)
            self.assertEqual(data['_access_hist'], {2:3})

    def test_partial_paired_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'paired.csv'
            p.write_text('scope,epoch,stream,population,words,pages,events\n'
                         'pooled,1,accesses,own,1,3,9\n')
            with self.assertRaises(ValueError): read_hist(p, 'pooled', 'accesses', 'own')

if __name__ == '__main__': unittest.main()
