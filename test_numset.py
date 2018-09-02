import unittest
import math
import dis

from numset import (Identity, Image, Integers, generator_to_function,
                     get_property, get_member)


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
                    self.assertTrue(math.isnan(obt.argval))
                    continue
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_function_call(self):
        obtained = generator_to_function(x for x in () if x == 1)
        self.assertEqual(obtained(1), 1)
        self.assertTrue(math.isnan(obtained(2)))

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
                    self.assertTrue(math.isnan(obt.argval))
                    continue
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_call_two_arguments(self):
        obtained = generator_to_function((x, y) for x, y in () if x == y)
        self.assertEqual(obtained(2, 2), (2, 2))
        self.assertTrue(math.isnan(obtained(1, 2)))

    def test_name(self):
        obtained = generator_to_function(x for x in ())
        self.assertEqual(obtained.__name__, "<function>")


class GetPropertySuite(unittest.TestCase):
    def test_no_property(self):
        def expected(x):
            return True
        obtained = get_property(x for x in ())
        zip_exp_obt = zip(dis.Bytecode(expected), dis.Bytecode(obtained))
        for i, (exp, obt) in enumerate(zip_exp_obt):
            with self.subTest(i=i):
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_property(self):
        def expected(x, y):
            return x == 1
        obtained = get_property(x for x, y in () if x == 1)
        zip_exp_obt = zip(dis.Bytecode(expected), dis.Bytecode(obtained))
        for i, (exp, obt) in enumerate(zip_exp_obt):
            with self.subTest(i=i):
                self.assertEqual(exp.opname, obt.opname)
                self.assertEqual(exp.argval, obt.argval)

    def test_name(self):
        obtained = get_property(x for x in ())
        self.assertEqual(obtained.__name__, "<property>")


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

    def test_complex_member(self):
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


class IdentitySuite(unittest.TestCase):
    def test_send_and_return_same_object(self):
        identity = Identity()
        next(identity)
        a = identity.send(1)
        self.assertEqual(a, 1)
        b = next(identity)
        self.assertEqual(b, 1)


class ImageSuite(unittest.TestCase):
    def test_domain(self):
        identity = Identity()
        add_four = Image(x + 4 for x in identity)
        self.assertEqual(add_four.domain, identity)

    def test_return_correct_value(self):
        return_b = Image("b" for x in Identity())
        self.assertEqual(return_b(1), "b")

    def test_basic_iteration(self):
        f = Image(x for x in Integers(-2, 0) if x + 1 == 0)
        self.assertEqual(list(f), [-1])

    def test_cache_elements(self):
        f = Image(x for x in Integers(-3, 0) if x + 2 == 0)
        for i in range(10):
            self.assertEqual(list(f), [-2])
        self.assertEqual(f.cache, [-2])
        self.assertEqual(f(-2), -2)

    def test_callable(self):
        add_five = Image(x + 5 for x in Identity())
        self.assertEqual(add_five(5), 10)

    def test_property(self):
        add_six = Image(x + 6 for x in Integers(-3, 0) if x + 3 == 0)
        self.assertTrue(add_six.property(-3))
        self.assertFalse(add_six.property(3))

    def test_member(self):
        add_seven = Image(x + 6 for x in Integers(-3, 0) if x + 3 == 0)
        self.assertEqual(add_seven.member(6), 12)


if __name__ == '__main__':
    unittest.main()
