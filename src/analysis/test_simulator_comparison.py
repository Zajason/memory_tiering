"""Fail-closed checks for simulator Figure 4 publication."""
import tempfile
import unittest
from pathlib import Path
from compare_simulator_m5 import validated_histogram, completed_job
from publish_fidelity import selected_dataset_output

class SimulatorComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'summary'
        self.expected=dict(events=20,epochs=1,pages=2)
        self.text=('epochs 1\npage_observations 2\ndram_accesses 20\n'
                   '# full unique-word histogram (words,pages)\n'+
                   ''.join(f'{i},{2 if i==4 else 0}\n' for i in range(65)))
        self.path.write_text(self.text)
    def tearDown(self):self.temp.cleanup()
    def test_complete(self):
        hist,counts=validated_histogram(self.path,self.expected)
        self.assertEqual(hist[4],2);self.assertEqual(counts,self.expected)
    def test_truncated(self):
        self.path.write_text(self.text.replace('64,0\n',''))
        with self.assertRaises(ValueError):validated_histogram(self.path,self.expected)
    def test_duplicate(self):
        self.path.write_text(self.text+'4,2\n')
        with self.assertRaises(ValueError):validated_histogram(self.path,self.expected)
    def test_changed_output(self):
        with self.assertRaises(ValueError):validated_histogram(self.path,dict(self.expected,events=21))
    def test_impossible_counts(self):
        self.path.write_text(self.text.replace('dram_accesses 20','dram_accesses 1'))
        with self.assertRaises(ValueError):validated_histogram(self.path,dict(self.expected,events=1))
    def test_partial_job_excluded(self):
        self.assertIsNone(completed_job(dict(status='interrupted',log='absent')))
    def test_completion_required(self):
        self.path.write_text('a growing summary is not a completed workload')
        with self.assertRaises(ValueError):completed_job(dict(status='complete',log=str(self.path)))
    def test_resumed_dataset_selected(self):
        directory=Path('/results/dataset/attempt-2')
        state={'jobs':{'dataset-pr':{'status':'complete','output':str(directory)}}}
        self.assertTrue(selected_dataset_output(directory,'pr',state))
        self.assertFalse(selected_dataset_output(directory.parent,'pr',state))
        state['jobs']['dataset-pr']['status']='running'
        self.assertFalse(selected_dataset_output(directory,'pr',state))

if __name__=='__main__':unittest.main()
