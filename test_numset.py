import unittest

import numset


class StatementSuite(unittest.TestCase):
    def test_true(self) -> None:
        P = numset.Statement(True)
        Q = numset.Statement(True)
        T = numset.Statement(True)
        self.assertTrue(P >> Q)
        self.assertTrue(Q >> P)
        self.assertTrue(((P >> Q) >> (Q >> P)) >> T)


class GivenSuite(unittest.TestCase):
    def test_paradox(self) -> None:
        P = numset.Statement()
        Q = numset.Statement()
        T = numset.Statement()
        obtainded = numset.Given(P).statement(T).must_be(True) \
                          .and_given(Q).statement(T).must_be(False) \
                          .end
        self.assertIsInstance(obtainded, numset.Paradox)
        self.assertEqual(obtainded.affirmations, [(P, T, True), (Q, T, False)])


class ClassSuite(unittest.TestCase):
    def test_class_that_is_not_an_element(self) -> None:
        x = numset.Class(belongs_to=None)
        self.assertFalse(numset.is_element(x))


class AxiomSuite(unittest.TestCase):
    def test_axiom_of_extent(self) -> None:
        A = numset.Class(1, 2, 3)
        B = numset.Class(1, 2, 3)
        self.assertEqual(A, B)

    def test_A_is_subset_of_B(self) -> None:
        A = numset.Class(1, 2, 3)
        B = numset.Class(1, 2, 3, 4)
        self.assertTrue(A.is_subset(B))

    def test_A_is_proper_subset_of_B(self) -> None:
        A = numset.Class(1, 2, 3)
        B = numset.Class(1, 2, 3, 4)
        self.assertTrue(A.is_proper_subset(B))



if __name__ == '__main__':
    unittest.main()
