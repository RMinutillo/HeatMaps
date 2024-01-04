import unittest
import time
import numpy as np
from numpy.testing import assert_array_equal
from scipy.sparse import dok_matrix
from soinn import Soinn
from sklearn.utils.estimator_checks import check_clustering


class TestSoinn(unittest.TestCase):
    def setUp(self):
        self.soinn = Soinn()
        self.soinn.nodes = np.array([[0, 0], [1, 0], [1, 1], [0, 1]]
                                    , dtype=np.float64)
        self.soinn.dim = 2
        self.soinn.adjacent_mat = dok_matrix((4, 4))
        self.soinn.winning_times = [1] * 4

    def test_skleran_api(self):
        check_clustering('Soinn', Soinn)

    def test_fit(self):
        pass

    def test_check_signal(self):
        self.soinn = Soinn()
        signal = 'hoge'
        self.assertRaises(TypeError, self.soinn._Soinn__check_signal, signal)
        signal = np.arange(6).reshape(2, 3)
        self.assertRaises(TypeError, self.soinn._Soinn__check_signal, signal)
        d = 6
        signal = np.arange(d)
        self.soinn._Soinn__check_signal(signal)
        self.assertTrue(hasattr(self.soinn, 'dim'))
        self.assertEqual(self.soinn.dim, d)
        signal = np.arange(d + 1)
        self.assertRaises(TypeError, self.soinn._Soinn__check_signal, signal)
        signal = [i for i in range(d)]
        self.soinn._Soinn__check_signal(signal)

    def test_add_node(self):
        self.soinn = Soinn()
        self.soinn.dim = 2  # dim have to be set before calling __add_node()
        signals = np.random.random((4, 2))
        for n in range(signals.shape[0]):
            signal = signals[n, :]
            self.soinn._Soinn__add_node(signal)
            self.assertEqual(len(self.soinn.winning_times), n + 1)
            self.assertEqual(self.soinn.nodes.shape, (n + 1, self.soinn.dim))
            np.testing.assert_array_equal(self.soinn.nodes[n, :], signal)
            self.assertEqual(self.soinn.adjacent_mat.shape, (n + 1, n + 1))
            self.assertEqual(self.soinn.adjacent_mat.nnz, 0)

    def test_add_edge(self):
        s1, s2 = 1, 2
        self.soinn._Soinn__add_edge((s1, s2))
        self.assertEqual(self.soinn.adjacent_mat.nnz, 2)
        self.assertEqual(self.soinn.adjacent_mat[s1, s2], 1)

    def test_increment_edge_ages(self):
        self.soinn.adjacent_mat[0, 1:3] = 1
        self.soinn.adjacent_mat[1:3, 0] = 1
        self.soinn._Soinn__increment_edge_ages(0)
        expected = dok_matrix([[0, 2, 2, 0], [2, 0, 0, 0], [2, 0, 0, 0], [0, 0, 0, 0]])
        np.testing.assert_array_equal(self.soinn.adjacent_mat.toarray(), expected.toarray())
        self.soinn._Soinn__increment_edge_ages(1)
        expected = dok_matrix([[0, 3, 2, 0], [3, 0, 0, 0], [2, 0, 0, 0], [0, 0, 0, 0]])
        np.testing.assert_array_equal(self.soinn.adjacent_mat.toarray(), expected.toarray())

    def test_delete_old_edges(self):
        self.soinn.winning_times = [i for i in range(4)]
        m = self.soinn.max_edge_age
        self.soinn.adjacent_mat[[0, 1], [1, 0]] = m + 2
        self.soinn.adjacent_mat[[0, 2], [2, 0]] = m + 1
        self.soinn._Soinn__delete_old_edges(0)
        actual = self.soinn.adjacent_mat.toarray()
        expected = dok_matrix([[0, m+1, 0], [m+1, 0, 0], [0, 0, 0]]).toarray()
        np.testing.assert_array_equal(actual, expected)
        expected = np.array([[0, 0], [1, 1], [0, 1]], dtype=np.float64)
        np.testing.assert_array_equal(self.soinn.nodes, expected)
        self.assertEqual(self.soinn.winning_times, [0, 2, 3])

    def test_delete_old_edges_with_deleting_no_node(self):
        # No node is deleted by the function
        self.soinn.winning_times = [i for i in range(4)]
        m = self.soinn.max_edge_age
        self.soinn.adjacent_mat[[0, 1], [1, 0]] = m + 2
        self.soinn.adjacent_mat[[1, 2], [2, 1]] = 1
        previous_nodes = self.soinn.nodes
        previous_winning_times = self.soinn.winning_times
        self.soinn._Soinn__delete_old_edges(0)
        actual = self.soinn.adjacent_mat.toarray()
        expected = dok_matrix([[0, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 0]]).toarray()
        np.testing.assert_array_equal(actual, expected)
        np.testing.assert_array_equal(self.soinn.nodes, previous_nodes)
        self.assertEqual(self.soinn.winning_times, previous_winning_times)

    def test_delete_old_edges_with_deleting_several_nodes(self):
        # delete several nodes simultaneously
        self.soinn.winning_times = [i for i in range(4)]
        m = self.soinn.max_edge_age
        self.soinn.adjacent_mat[[0, 1, 0, 3], [1, 0, 3, 0]] = m + 2
        self.soinn.adjacent_mat[[0, 2], [2, 0]] = m + 1
        self.soinn._Soinn__delete_old_edges(0)
        actual = self.soinn.adjacent_mat.toarray()
        expected = dok_matrix([[0, m+1], [m+1, 0]]).toarray()
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(self.soinn.winning_times, [0, 2])

    def test_delete_old_edges_with_changing_winner_index(self):
        # the winner index is changed by deleting nodes
        self.soinn.winning_times = [i for i in range(4)]
        expected = self.soinn.nodes[3, :]
        m = self.soinn.max_edge_age
        self.soinn.adjacent_mat[[3, 0, 3, 2], [0, 3, 2, 3]] = m + 2
        self.soinn.adjacent_mat[[3, 1], [1, 3]] = m + 1
        winner_index = self.soinn._Soinn__delete_old_edges(3)
        np.testing.assert_array_equal(self.soinn.nodes[winner_index, :], expected)

    def test_delete_nodes(self):
        self.soinn.winning_times = [i for i in range(4)]
        self.soinn.adjacent_mat[[0, 1], [1, 0]] = 1
        self.soinn.adjacent_mat[[2, 3], [3, 2]] = 2
        self.soinn._Soinn__delete_nodes([1])
        expected = np.array([[0, 0], [1, 1], [0, 1]], dtype=np.float64)
        np.testing.assert_array_equal(self.soinn.nodes, expected)
        self.assertEqual(self.soinn.winning_times, [0, 2, 3])
        expected = dok_matrix([[0, 0, 0], [0, 0, 2], [0, 2, 0]]).toarray()
        np.testing.assert_array_equal(self.soinn.adjacent_mat.toarray(), expected)

    def test_delete_nodes_with_deleting_several_nodes(self):
        # delete several nodes simultaneously
        self.soinn.winning_times = [i for i in range(4)]
        self.soinn.adjacent_mat[[0, 1], [1, 0]] = 1
        self.soinn.adjacent_mat[[2, 3], [3, 2]] = 2
        self.soinn._Soinn__delete_nodes([1, 3])
        expected = np.array([[0, 0], [1, 1]], dtype=np.float64)
        np.testing.assert_array_equal(self.soinn.nodes, expected)
        self.assertEqual(self.soinn.winning_times, [0, 2])
        expected = dok_matrix((2, 2)).toarray()
        np.testing.assert_array_equal(self.soinn.adjacent_mat.toarray(), expected)

    def test_delete_noise_nodes(self):
        self.soinn.adjacent_mat[0, 2:] = 1
        self.soinn.adjacent_mat[2:, 0] = 1
        self.soinn.winning_times = [2, 1, 2, 1]
        self.soinn._Soinn__delete_noise_nodes()
        np.testing.assert_array_equal(self.soinn.nodes, [[0, 0], [1, 1], [0, 1]])
        self.assertEqual(self.soinn.winning_times, [2, 2, 1])
        expected = [[0, 1, 1], [1, 0, 0], [1, 0, 0]]
        np.testing.assert_array_equal(self.soinn.adjacent_mat.toarray(), expected)

    def test_delete_nodes_from_adjacent_mat(self):
        self.soinn.adjacent_mat[0, 1] = 1
        self.soinn.adjacent_mat[1, 0] = 1
        self.soinn.adjacent_mat[0, 2] = 2
        self.soinn.adjacent_mat[2, 0] = 2
        self.soinn.adjacent_mat[2, 3] = 3
        self.soinn.adjacent_mat[3, 2] = 3

        indexes = [1]
        expected1 = self.soinn.adjacent_mat[np.ix_([0, 2, 3], [0, 2, 3])]
        self.soinn._Soinn__delete_nodes_from_adjacent_mat(indexes, 4, 3)
        expected2 = [[0, 2, 0], [2, 0, 3], [0, 3, 0]]
        np.testing.assert_array_equal(self.soinn.adjacent_mat.toarray(), expected1.toarray())
        np.testing.assert_array_equal(self.soinn.adjacent_mat.toarray(), expected2)

    def test_performance_of_update_adjacent_mat(self):
        n = 500
        p = 0.01
        a = dok_matrix((n, n))
        for c in range(n):
            i = np.random.randint(n)
            j = np.random.randint(n)
            if i == j:
                continue
            a[i, j] += 1
        indexes = np.random.randint(n, size=int(p * n)).tolist()
        indexes = sorted(list(set(indexes)))
        remain_indexes = list(set([i for i in range(n)]) - set(indexes))
        self.soinn.adjacent_mat = a.copy()

        start = time.time()
        expected = a[np.ix_(remain_indexes, remain_indexes)]
        expected_time = time.time() - start
        start = time.time()
        self.soinn._Soinn__delete_nodes_from_adjacent_mat(indexes, n, len(remain_indexes))
        actual_time = time.time() - start
        self.assertEqual(self.soinn.adjacent_mat.shape, expected.shape)
        np.testing.assert_array_equal(self.soinn.adjacent_mat.toarray(), expected.toarray())
        #print('np._ix: ', expected_time)
        #print('__update_adjacent_mat:', actual_time)
        self.assertLess(actual_time, expected_time)

    def test_find_nearest_nodes(self):
        signal = np.array([-1, 0])
        indexes, sq_dists = self.soinn._Soinn__find_nearest_nodes(1, signal)
        self.assertEqual(indexes, [0])
        self.assertEqual(sq_dists, [1])
        indexes, sq_dists = self.soinn._Soinn__find_nearest_nodes(2, signal)
        self.assertEqual(indexes, [0, 3])
        self.assertEqual(sq_dists, [1, 2])

    def test_calculate_similarity_thresholds(self):
        self.soinn.adjacent_mat[0, 2:] = 1
        self.soinn.adjacent_mat[2:, 0] = 1
        self.assertEqual(self.soinn._Soinn__calculate_similarity_thresholds([0]), [2])
        self.assertEqual(self.soinn._Soinn__calculate_similarity_thresholds([0, 1]), [2, 1])

    def test_update_winner(self):
        self.soinn.winning_times[0] = 2 - 1
        np.testing.assert_array_equal(self.soinn.nodes[0, :], [0, 0])
        self.soinn._Soinn__update_winner(0, np.array([-1, 0], dtype=np.float64))
        np.testing.assert_array_equal(self.soinn.nodes[0, :], [-0.5, 0])
        self.assertEqual(self.soinn.winning_times[0], 2)
        self.soinn.winning_times[1] = 3 - 1
        np.testing.assert_array_equal(self.soinn.nodes[1, :], [1, 0])
        self.soinn._Soinn__update_winner(1, np.array([2, 0], dtype=np.float64))
        np.testing.assert_array_equal(self.soinn.nodes[1, :], [1 + 1/3, 0])
        self.assertEqual(self.soinn.winning_times[1], 3)

    def test_update_adjacent_nodes(self):
        self.soinn.adjacent_mat[0, 1:3] = 1
        self.soinn.adjacent_mat[1:3, 0] = 1
        np.testing.assert_array_equal(self.soinn.nodes[1], [1, 0])
        np.testing.assert_array_equal(self.soinn.nodes[2], [1, 1])
        self.soinn._Soinn__update_adjacent_nodes(0, np.array([-1, 0]))
        np.testing.assert_array_equal(self.soinn.nodes[1], [1 - 2/100, 0])
        np.testing.assert_array_equal(self.soinn.nodes[2], [1 - 2/100, 1 - 1/100])
        np.testing.assert_array_equal(self.soinn.nodes[0], [0, 0])
        np.testing.assert_array_equal(self.soinn.nodes[3], [0, 1])

    @unittest.skip('skip test_input_signal() because it takes much time.')
    def test_input_signal(self):
        n = 5000
        loop_num = 10
        elapsed_time = 0
        for l in range(loop_num):
            data = np.random.rand(n, 2)
            self.soinn = Soinn()
            start = time.time()
            for i in range(n):
                self.soinn.input_signal(data[i])
            elapsed_time += time.time() - start
        elapsed_time /= loop_num
        print('average time: ', str(elapsed_time), 'sec')
        print(self.soinn)

    def test_label_nodes(self):
        self.soinn._Soinn__add_node([0, 2])
        self.soinn._Soinn__add_node([1, 2])
        self.soinn._Soinn__add_edge([0, 2])
        self.soinn._Soinn__add_edge([0, 3])
        self.soinn._Soinn__add_edge([1, 4])
        labels = self.soinn._Soinn__label_nodes()
        self.assertEqual(len(labels), self.soinn.nodes.shape[0])
        self.assertEqual(labels[0], labels[2])
        self.assertEqual(labels[0], labels[3])
        self.assertNotEqual(labels[0], -1)
        self.assertEqual(labels[1], -1)
        self.assertEqual(labels[4], -1)
        self.assertEqual(labels[5], -1)
        labels = self.soinn._Soinn__label_nodes(min_cluster_size=2)
        self.assertEqual(len(labels), self.soinn.nodes.shape[0])
        self.assertEqual(labels[0], labels[2])
        self.assertEqual(labels[0], labels[3])
        self.assertNotEqual(labels[0], -1)
        self.assertEqual(labels[1], labels[4])
        self.assertNotEqual(labels[1], -1)
        self.assertEqual(labels[5], -1)

    def test_label_samples(self):
        # There are 6 nodes and nodes indexed 0, 2 and 3 make a cluster.
        self.soinn._Soinn__add_node([0, 2])
        self.soinn._Soinn__add_node([1, 2])
        self.soinn._Soinn__add_edge([0, 2])
        self.soinn._Soinn__add_edge([0, 3])
        self.soinn._Soinn__add_edge([1, 4])
        actual = self.soinn._Soinn__label_samples(np.array([[-0.1, -0.1],
                                                            [1.1, 1.1],
                                                            [100, 100]]))
        expected = np.array(
            [self.soinn.node_labels[0]] * 2 + [Soinn.NOISE_LABEL])
        assert_array_equal(actual, expected)


if __name__ == '__main__':
    unittest.main()
