import unittest
import numpy
import dis

from numset import (Set, generator_to_function, get_constraints, get_member,
                    Domain)


class GeneratorToFunctionSuite(unittest.TestCase):
    def test_generator_to_function_bytecodes(self):
        def expected(x):
            if x == 1:
                return x
            return NAN

        obtained = generator_to_function(x for x in () if x == 1)

        zip_exp_obt = zip(dis.Bytecode(expected), dis.Bytecode(obtained))
        for i, (exp, obt) in enumerate(zip_exp_obt):
            with self.subTest(i=i):
                if exp.opname == "LOAD_GLOBAL":
                    self.assertTrue(numpy.isnan(obt.argval))
                    continue
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_function_call(self):
        obtained = generator_to_function(x for x in () if x == 1)
        self.assertEqual(obtained(1), 1)
        self.assertTrue(numpy.isnan(obtained(2)))

    def test_two_arguments(self):
        def expected(x, y):
            if x == y:
                return (x, y)
            return NAN

        obtained = generator_to_function(((x, y) for x, y in () if x == y))

        zip_exp_obt = zip(dis.Bytecode(expected), dis.Bytecode(obtained))
        for i, (exp, obt) in enumerate(zip_exp_obt):
            with self.subTest(i=i):
                if exp.opname == "LOAD_GLOBAL":
                    self.assertTrue(numpy.isnan(obt.argval))
                    continue
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_call_two_arguments(self):
        obtained = generator_to_function((x, y) for x, y in () if x == y)
        self.assertEqual(obtained(2, 2), (2, 2))
        self.assertTrue(numpy.isnan(obtained(1, 2)))

    def test_name(self):
        obtained = generator_to_function(x for x in ())
        self.assertEqual(obtained.__name__, "<function>")


class GetConstraintSuite(unittest.TestCase):
    def test_no_constraint(self):
        def expected(x):
            return True
        obtained = get_constraints(x for x in ())
        zip_exp_obt = zip(dis.Bytecode(expected), dis.Bytecode(obtained))
        for i, (exp, obt) in enumerate(zip_exp_obt):
            with self.subTest(i=i):
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_constraint(self):
        def expected(x, y):
            return x == 1
        obtained = get_constraints(x for x, y in () if x == 1)
        zip_exp_obt = zip(dis.Bytecode(expected), dis.Bytecode(obtained))
        for i, (exp, obt) in enumerate(zip_exp_obt):
            with self.subTest(i=i):
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_many_constraints(self):
        def expected(x):
            return 0 < x and x < 1
        obtained = get_constraints(x for x in () if 0 < x and x < 1)
        zip_exp_obt = zip(dis.Bytecode(expected), dis.Bytecode(obtained))
        for i, (exp, obt) in enumerate(zip_exp_obt):
            with self.subTest(i=i):
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_name(self):
        obtained = get_constraints(x for x in ())
        self.assertEqual(obtained.__name__, "<constraint>")


class GetMememberSuite(unittest.TestCase):
    def test_single_member(self):
        def expected(x):
            return x
        obtained = get_member(x for x in ())
        zip_exp_obt = zip(dis.Bytecode(expected), dis.Bytecode(obtained))
        for i, (exp, obt) in enumerate(zip_exp_obt):
            with self.subTest(i=i):
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_elaborated_expression_member(self):
        def expected(x, y):
            return max(x, y)
        obtained = get_member(max(x, y) for x, y in ())
        zip_exp_obt = zip(dis.Bytecode(expected), dis.Bytecode(obtained))
        for i, (exp, obt) in enumerate(zip_exp_obt):
            with self.subTest(i=i):
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_name(self):
        obtained = get_member(x for x in ())
        self.assertEqual(obtained.__name__, "<member>")


class SetSuite(unittest.TestCase):
    def test_domain(self):
        domain = iter(range(5))
        add_four = Set(x + 4 for x in domain)
        self.assertEqual(add_four.domain, domain)

    def test_return_correct_value(self):
        return_b = Set("b" for x in range(5))
        self.assertEqual(return_b(1), "b")

    def test_basic_iteration(self):
        f = Set(x for x in range(-2, 0) if x + 1 == 0)
        self.assertEqual(list(f), [-1])

    def test_cache_3_elements(self):
        f = Set(x for x in range(-3, 0) if x + 2 == 0)
        for i in range(10):
            self.assertEqual(list(f), [-2])
        self.assertEqual(f.elements, [-2])
        self.assertEqual(f(-2), -2)

    def test_cache_0_elements(self):
        f = Set(x for x in () if x + 2 == 0)
        for i in range(10):
            self.assertEqual(list(f), [])
        self.assertTrue(numpy.array_equal(f.elements, numpy.array([])))
        self.assertEqual(f(-2), -2)

    def test_callable(self):
        add_five = Set(x + 5 for x in range(6))
        self.assertEqual(add_five(5), 10)

    def test_wrong_argument(self):
        A = Set(x for x in () if x < 5)
        add_ten = Set(x + 10 for x in A)
        message = "Variable do not satisfy the constraint."
        with self.assertRaisesRegex(ValueError, message):
            add_ten(6)

    def test_wrong_arguments(self):
        A = Set((x, y) for x, y in () if x < 5 if y < 5)
        add_ten = Set(x + 10 for x, y in A)
        message = "Variable do not satisfy the constraint."
        with self.assertRaisesRegex(ValueError, message):
            add_ten(4, 7)

    def test_constraint(self):
        add_six = Set(x + 6 for x in range(-3, 0) if x + 3 == 0)
        self.assertTrue(add_six.constraint(-3))
        self.assertFalse(add_six.constraint(3))

    def test_member(self):
        add_seven = Set(x + 7 for x in range(-3, 0) if x + 3 == 0)
        self.assertEqual(add_seven.member(7), 14)

    def test_varnames(self):
        add_eight = Set(... for x, y, z in ())
        self.assertEqual(add_eight.varnames, ("x", "y", "z"))


class SetOperationsSuite(unittest.TestCase):
    def test_belonging(self):
        A = Set(x for x in range(0, 10))
        self.assertTrue(5 in A)

    def test_equality(self):
        A = Set(x for x in range(0, 10) if x%2 != 0)
        B = Set(y for y in range(0, 10) if y%2 != 0)
        self.assertEqual(A, B)

    def test_isubset(self):
        A = Set(x for x in range(0, 10) if x%2 != 0)
        B = Set(x for x in range(0, 10))
        self.assertTrue(A.issubset(B))

    def test_issuperset(self):
        A = Set(x for x in range(0, 10) if x%2 != 0)
        B = Set(x for x in range(0, 10))
        self.assertTrue(B.issuperset(A))

    def test_isdisjoint(self):
        A = Set(x for x in range(0, 10))
        B = Set(x for x in range(11, 20))
        self.assertTrue(B.isdisjoint(A))
        C = Set(x for x in range(0, 10))
        D = Set(x for x in range(5, 15))
        self.assertFalse(C.isdisjoint(D))

    def test_less_than(self):
        A = Set(x for x in range(0, 5))
        B = Set(x for x in range(0, 10))
        self.assertLess(A, B)

    def test_less_equal(self):
        A = Set(x for x in range(0, 5))
        B = Set(x for x in range(0, 10))
        self.assertLessEqual(A, B)
        C = Set(x for x in range(5))
        D = Set(x for x in range(5))
        self.assertLessEqual(C, D)

    def test_greater_than(self):
        A = Set(x for x in range(0, 5))
        B = Set(x for x in range(0, 10))
        self.assertGreater(A, B)

    def test_greater_equal(self):
        A = Set(x for x in range(0, 5))
        B = Set(x for x in range(0, 10))
        self.assertGreaterEqual(A, B)
        C = Set(x for x in range(5))
        D = Set(x for x in range(5))
        self.assertGreaterEqual(C, D)

    def test_union(self):
        A = Set(x for x in range(5))
        B = Set(x for x in range(5, 10))
        C = Set(x for x in range(10))
        self.assertEqual(A.union(B), C)
        self.assertEqual(A | B, C)

    def test_intersection(self):
        A = Set(x for x in range(10))
        B = Set(x for x in range(5, 15))
        C = Set(x for x in range(5, 10))
        self.assertEqual(A.intersection(B), C)
        self.assertEqual(A & B, C)

    def test_difference(self):
        A = Set(x for x in range(10))
        B = Set(x for x in range(5))
        C = Set(x for x in range(5, 10))
        self.assertEqual(A.difference(B), C)
        self.assertEqual(A - B, C)

    def test_symmetric_difference(self):
        A = Set(x for x in (1, 2, 3))
        B = Set(x for x in (3, 4, 5))
        C = Set(x for x in (1, 2, 4, 5))
        self.assertEqual(A.symmetric_difference(B), C)
        self.assertEqual(A ^ B, C)

    def test_product(self):
        A = Set(x for x in [0, 1, 2])
        B = Set(x for x in [3, 4, 5])
        C = Set((x, y) for x, y in A*B)
        D = Set((x, y) for x, y in [(0, 3), (1, 4), (2, 5)])
        self.assertEqual(C, D)

    def test_power(self):
        A = Set(x for x in [6, 7, 8])
        B = Set((x, y) for x, y in A**2)
        C = Set((x, y) for x, y in zip(A, A))
        self.assertEqual(B, C)

    def test_flattern(self):
        A = Set(x for x in [9, 10, 11])
        B = Set(x for x in [12, 13, 14])
        C = Set(x for x in [15, 16, 17])
        D = Set((x, y, z) for x, y, z in (A*B)*C)
        E = Set((x, y, z) for x, y, z in A*(B*C))
        F = Set((x, y, z) for x, y, z
                in [(9, 12, 15), (10, 13, 16), (11, 14, 17)])
        self.assertEqual(D, F)
        self.assertEqual(E, F)


class DomainSuite(unittest.TestCase):
    def test_product(self):
        A = Domain([0, 1, 2])
        B = Domain([3, 4, 5])
        C = Set((x, y) for x, y in A*B)
        D = Set((x, y) for x, y in [(0, 3), (1, 4), (2, 5)])
        self.assertEqual(C, D)

    def test_power(self):
        A = Domain([6, 7, 8])
        B = Set((x, y) for x, y in A**2)
        C = Set((x, y) for x, y in zip(A, A))
        self.assertEqual(B, C)

    def test_flattern(self):
        A = Domain([9, 10, 11])
        B = Domain([12, 13, 14])
        C = Domain([15, 16, 17])
        D = Set((x, y, z) for x, y, z in (A*B)*C)
        E = Set((x, y, z) for x, y, z in A*(B*C))
        F = Set((x, y, z) for x, y, z
                in [(9, 12, 15), (10, 13, 16), (11, 14, 17)])
        self.assertEqual(D, F)
        self.assertEqual(E, F)

    def test_sum(self):
        A = Domain([0, 1, 2])
        B = Domain([3, 4, 5])
        C = Set(x for x in A + B)
        D = Set(x for x in [0, 1, 2, 3, 4, 5])
        self.assertEqual(C, D)


if __name__ == "__main__":
    unittest.main()
