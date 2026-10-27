import io
import unittest
from prepare_gplus import select_edges


class SnapshotTests(unittest.TestCase):
    def test_temporal_filter_not_prefix(self):
        source = io.BytesIO(b'4 2 3\n2 1 0\n8 3 2\n9 7 0\n')
        target = io.StringIO()
        result = select_edges(source, target, 1)
        self.assertEqual(target.getvalue(), '2\t1\n9\t7\n')
        self.assertEqual(result, dict(input_edges=4, selected_edges=2, max_node_id=9))

    def test_reject_invalid_format(self):
        for line in (b'1 2\n', b'1 2 4\n', b'-1 2 0\n', b'1 2 0 9\n'):
            with self.assertRaises(ValueError):
                select_edges(io.BytesIO(line), io.StringIO(), 1)


if __name__ == '__main__':
    unittest.main()
