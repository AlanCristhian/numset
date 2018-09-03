import types
import opcode
import functools
from collections import abc

import bytecode
import numpy


# In the generator, jump to loop start label if the element satisfy the
# property. The loop start label in the generator will be the function end
# label.
def _get_new_end_label(old_bytecode):
    for i in old_bytecode:
        if isinstance(i, bytecode.Label):
            return i  # First label found will be the function end label


# Find the generator end label
def _get_old_end_label(old_bytecode):
    for i in reversed(old_bytecode):
        if isinstance(i, bytecode.Label):
            return i  # Penultimate label found is that will be replaced


# Start before the loop initialization
def _get_new_start(old_bytecode):
    flag = 0
    for i, b in enumerate(old_bytecode):
        if flag == 0:
            if isinstance(b, bytecode.Instr) and b.name == "FOR_ITER":
                flag = 1
        elif flag == 1:
            if b.name == "UNPACK_SEQUENCE":
                continue
            name = b.name
            flag = 2
        elif isinstance(b, bytecode.Instr) and b.name != name:
            return i


def _get_member_bytecode(generator):
    old_bytecode = bytecode.Bytecode.from_code(generator.gi_code)
    new_bytecode = bytecode.Bytecode()

    for new_start, b in enumerate(old_bytecode):
        if isinstance(b, bytecode.Instr) and b.name == "POP_JUMP_IF_FALSE":
            break

    for i in old_bytecode[new_start + 1:]:   # remove the loop initialization
        if isinstance(i, bytecode.Instr) and i.name == "YIELD_VALUE":
            new_bytecode.append(bytecode.Instr("RETURN_VALUE"))
            break
        new_bytecode.append(i)

    new_bytecode.varnames = generator.gi_code.co_varnames[:1]
    new_bytecode.argcount = len(new_bytecode.varnames)

    return new_bytecode


def _bytecode_to_function(generator, byte_code, name):
    new_code = byte_code.to_code()
    new_globals = generator.gi_frame.f_globals
    return types.FunctionType(new_code, new_globals, name)


def get_member(generator):
    fun_bytecode = _get_member_bytecode(generator)
    return _bytecode_to_function(generator, fun_bytecode, "<member>")


def _get_property_bytecode(generator):
    old_bytecode = bytecode.Bytecode.from_code(generator.gi_code)
    new_bytecode = bytecode.Bytecode()
    new_start = _get_new_start(old_bytecode)

    for i in old_bytecode[new_start:]:   # remove the loop initialization
        if isinstance(i, bytecode.Instr) and i.name == "POP_JUMP_IF_FALSE":
            new_bytecode.append(bytecode.Instr("RETURN_VALUE"))
            break
        new_bytecode.append(i)

    new_bytecode.varnames = generator.gi_code.co_varnames[:1]
    new_bytecode.argcount = len(new_bytecode.varnames)
    return new_bytecode


def _has_property(generator):
    for i, op_code in enumerate(generator.gi_code.co_code):
        if i%2 == 0 and op_code == opcode.opmap["POP_JUMP_IF_FALSE"]:
            return True
    return False


def get_property(generator):
    if _has_property(generator):
        fun_bytecode = _get_property_bytecode(generator)
    else:
        fun_bytecode = bytecode.Bytecode([
            bytecode.Instr("LOAD_CONST", True),
            bytecode.Instr("RETURN_VALUE")])
        fun_bytecode.argcount = generator.gi_code.co_argcount
        fun_bytecode.varnames = generator.gi_code.co_varnames[1:]
    return _bytecode_to_function(generator, fun_bytecode, "<property>")


def _generator_to_function_bytecode(generator):
    old_bytecode = bytecode.Bytecode.from_code(generator.gi_code)
    new_bytecode = bytecode.Bytecode()
    new_end_label = _get_new_end_label(old_bytecode)
    old_end_label = _get_old_end_label(old_bytecode)
    new_start = _get_new_start(old_bytecode)

    for i in old_bytecode[new_start:]:   # remove the loop initialization
        if isinstance(i, bytecode.Instr):
            # Return the element that satisfy the property
            if i.name == "YIELD_VALUE":
                new_bytecode.append(bytecode.Instr("RETURN_VALUE", i.arg))

            # remove jump that go to the start of the loop
            elif i.name in ("POP_TOP", "JUMP_ABSOLUTE", "UNPACK_SEQUENCE"):
                continue
            else:
                new_bytecode.append(bytecode.Instr(i.name, i.arg))
        else:
            # jump to end if element not satisfy the property
            if i == old_end_label:
                new_bytecode.append(new_end_label)
            else:
                new_bytecode.append(i)

    # return math.nan if element not satisfy the property
    new_bytecode[-2] = bytecode.Instr("LOAD_CONST", numpy.nan)

    new_bytecode.varnames = generator.gi_code.co_varnames[1:]
    new_bytecode.argcount = len(new_bytecode.varnames)

    return new_bytecode


def generator_to_function(generator):
    fun_bytecode = _generator_to_function_bytecode(generator)
    return _bytecode_to_function(generator, fun_bytecode, "<function>")


def _ensure_elements(method):
    @functools.wraps(method)
    def wrapper(self, other):
        if self.elements is None:
            iter(self)
        if other.elements is None:
            iter(other)
        return method(self, other)
    return wrapper


class BaseSet:
    @_ensure_elements
    def __eq__(self, other):
        return numpy.array_equal(self.elements, other.elements)

    def issubset(self, other):
        return numpy.in1d(self.elements, other.elements)

    def issuperset(self, other):
        return other.issubset(self)

    @_ensure_elements
    def isdisjoint(self, other):
        diff = numpy.intersect1d(self.elements, other.elements)
        if len(diff) == 0:
            return True
        else:
            return False

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other

    @_ensure_elements
    def union(self, other):
        result = numpy.union1d(self.elements, other.elements)
        return Set(x for x in result)

    @_ensure_elements
    def intersection(self, other):
        result = numpy.intersect1d(self.elements, other.elements)
        return Set(x for x in result)

    @_ensure_elements
    def difference(self, other):
        result = numpy.setdiff1d(self.elements, other.elements)
        return Set(x for x in result)

    @_ensure_elements
    def symmetric_difference(self, other):
        result = numpy.setxor1d(self.elements, other.elements)
        return Set(x for x in result)

    @_ensure_elements
    def __mul__(self, other):
        return Product(self, other)

    def __pow__(self, value):
        if self.elements is None:
            iter(self)
        arrays = [self.elements]*value
        product = list(zip(*arrays))
        return Domain(product)

    __xor__ = symmetric_difference
    __sub__ = difference
    __lt__ = issubset
    __or__ = union
    __and__ = intersection


class Product(BaseSet):
    def __init__(self, *sets):
        self.elements = []
        for s in sets:
            if isinstance(s, Product):
                self.elements.extend(s.elements)
            else:
                self.elements.append(s)

    def __iter__(self):
        return iter(zip(*self.elements))


class Set(BaseSet):
    def __init__(self, expression):
        self.expression = expression
        self.function = generator_to_function(expression)
        self.property = get_property(expression)
        self.member = get_member(expression)
        self.domain = expression.gi_frame.f_locals['.0']
        self.elements = None

    def __call__(self, element):
        return self.function(element)

    def __iter__(self):
        if self.elements is None:
            self.elements = numpy.array(list(self.expression))
        return iter(self.elements)


class Domain(BaseSet):
    def __init__(self, iterable):
        if isinstance(iterable, numpy.ndarray):
            self.elements = iterable
        elif isinstance(iterable, Domain):
            self.elements = iterable.elements
        else:
            self.elements = numpy.array(iterable)

    def __iter__(self):
        return iter(self.elements)
