"""Do numeric operations with the syntax of the generator expression."""


# NOTE 1: A generator expression have the following parts:
#
#            varnames                                  constraints
#             ┌─┴──┐                                 ┌──────┴───────┐
# ((x, y) for (x, y) in zip(iterable1, iterable2) if x > 0 and y == 0)
#  └──┬─┘               └──────────┬────────────┘
#   member                       domain


from collections import abc
import functools
import itertools
import opcode
import types

import bytecode
import numpy


# In the generator, jump to loop start label if the element satisfy the
# constraint. The loop start label in the generator will be the function end
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


# Find the start of the new bytecode. The
# beginign is before the loop initialization.
def _get_new_start(old_bytecode):
    sentinel = 0
    for i, b in enumerate(old_bytecode):

        # Come here if the FOR_ITER bytecode is stil not found
        if sentinel == 0:

            # I know that I enter to the loop set
            # up when I found the FOR_ITER bytecode
            if isinstance(b, bytecode.Instr) and b.name == "FOR_ITER":
                sentinel = 1  # report that FOR_ITER was already found

        # Come here if the FOR_ITER bytecode was found
        elif sentinel == 1:
            if b.name == "UNPACK_SEQUENCE":
                continue
            previous_name = b.name
            sentinel = 2

        # I know that the loop set up was finished when
        # the current bytecode is different of the previous
        elif isinstance(b, bytecode.Instr) and b.name != previous_name:
            return i


# Get the member part of the generator expression. See NOTE 1
def _get_member_bytecode(generator):
    old_bytecode = bytecode.Bytecode.from_code(generator.gi_code)
    new_bytecode = bytecode.Bytecode()

    # Member bytecode start after the last POP_JUMP_IF_FALSE bytecode
    start_list = []
    for ns, b in enumerate(old_bytecode):
        if isinstance(b, bytecode.Instr) and b.name == "POP_JUMP_IF_FALSE":
            start_list.append(ns)
    if start_list:
        new_start = start_list.pop()
    else:
        new_start = ns

    for i in old_bytecode[new_start + 1:]:   # remove the loop initialization

        # Replace YIELD_VALUE  by RETURN_VALUE bytecode because
        # the new code will be a function, not a generator
        if isinstance(i, bytecode.Instr) and i.name == "YIELD_VALUE":
            new_bytecode.append(bytecode.Instr("RETURN_VALUE"))
            break  # the new code ends when return the value
        new_bytecode.append(i)

    # NOTE 2: generator.gi_code.co_varnames everytime contains
    # the ".0" constant. The another names are the variable names used by the
    # generator. That varnames will be the arguments of the new function.
    new_bytecode.varnames = generator.gi_code.co_varnames[:1]
    new_bytecode.argcount = len(new_bytecode.varnames)

    return new_bytecode


# Create a function object with the given bytecode
def _bytecode_to_function(generator, byte_code, name):
    new_code = byte_code.to_code()
    new_globals = generator.gi_frame.f_globals
    return types.FunctionType(new_code, new_globals, name)


def get_member(generator):
    "Extract the member bytecode (see NOTE 1) and create a function with it."
    fun_bytecode = _get_member_bytecode(generator)
    return _bytecode_to_function(generator, fun_bytecode, "<member>")


# Get the constraint bytecode of the generator expression
def _get_constraints_bytecode(generator):
    old_bytecode = bytecode.Bytecode.from_code(generator.gi_code)
    new_bytecode = bytecode.Bytecode()
    new_start = _get_new_start(old_bytecode)
    end_label = bytecode.Label()

    # Count the amount of POP_JUMP_IF_FALSE bytecodes
    pjif_count = 0
    for b in old_bytecode:
        if isinstance(b, bytecode.Instr) and b.name == "POP_JUMP_IF_FALSE":
            pjif_count += 1

    for b in old_bytecode[new_start:]:   # remove the loop initialization
        if isinstance(b, bytecode.Instr) and b.name == "POP_JUMP_IF_FALSE":
            pjif_count -= 1
            if pjif_count:
                new_bytecode.append(bytecode.Instr("JUMP_IF_FALSE_OR_POP",
                                                   end_label, lineno=b.lineno))
                continue
            else:
                new_bytecode.append(end_label)
                new_bytecode.append(bytecode.Instr("RETURN_VALUE"))
                break
        new_bytecode.append(b)

    new_bytecode.varnames = generator.gi_code.co_varnames[:1]  # See NOTE 2
    new_bytecode.argcount = len(new_bytecode.varnames)
    return new_bytecode


# Check if the generator expression has the constraint part
def _has_constraints(generator):
    for i, op_code in enumerate(generator.gi_code.co_code):
        if i%2 == 0 and op_code == opcode.opmap["POP_JUMP_IF_FALSE"]:
            return True
    return False


# Get the constraint part of the generator expression and
# make a function with it. Create a function that everytime
# return True if the generator have not constraints.
def get_constraints(generator):
    if _has_constraints(generator):
        fun_bytecode = _get_constraints_bytecode(generator)
    else:
        fun_bytecode = bytecode.Bytecode([
            bytecode.Instr("LOAD_CONST", True),
            bytecode.Instr("RETURN_VALUE")])
    fun_bytecode.varnames = generator.gi_code.co_varnames[1:]  # See NOTE 2
    fun_bytecode.argcount = len(fun_bytecode.varnames)
    return _bytecode_to_function(generator, fun_bytecode, "<constraint>")


# Create a function bytecode with the generator expression bytecode.
def _generator_to_function_bytecode(generator):
    old_bytecode = bytecode.Bytecode.from_code(generator.gi_code)
    new_bytecode = bytecode.Bytecode()
    new_end_label = _get_new_end_label(old_bytecode)
    old_end_label = _get_old_end_label(old_bytecode)
    new_start = _get_new_start(old_bytecode)

    for i in old_bytecode[new_start:]:   # remove the loop initialization
        if isinstance(i, bytecode.Instr):
            # Return the element that satisfy the constraint
            if i.name == "YIELD_VALUE":
                new_bytecode.append(bytecode.Instr("RETURN_VALUE", i.arg))

            # remove jump that go to the start of the loop
            elif i.name in ("POP_TOP", "JUMP_ABSOLUTE", "UNPACK_SEQUENCE"):
                continue
            else:
                new_bytecode.append(bytecode.Instr(i.name, i.arg))
        else:
            # jump to end if element not satisfy the constraint
            if i == old_end_label:
                new_bytecode.append(new_end_label)
            else:
                new_bytecode.append(i)

    # return math.nan if element not satisfy the constraint
    new_bytecode[-2] = bytecode.Instr("LOAD_CONST", numpy.nan)
    new_bytecode.varnames = generator.gi_code.co_varnames[1:]  # See NOTE 2
    new_bytecode.argcount = len(new_bytecode.varnames)

    return new_bytecode


def generator_to_function(generator):
    """Create a function object with the generator expression object."""
    fun_bytecode = _generator_to_function_bytecode(generator)
    return _bytecode_to_function(generator, fun_bytecode, "<function>")


# A decorator that ensure that ".elements" property is not none and if full.
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

    @_ensure_elements
    def __add__(self, other):
        return Sum(self, other)

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


class Sum(BaseSet):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __iter__(self):
        return itertools.chain(self.left, self.right)

class _ConstrainedSet:
    def __init__(self, elements, constraint):
        self.elements = elements
        self.constraint = constraint

    def __next__(self):
        return next(self.elements)

    def __iter__(self):
        return self


class Set(BaseSet):
    def __init__(self, expression):
        self.expression = expression
        self.member = get_member(expression)
        self.varnames = expression.gi_code.co_varnames[1:]
        self.domain = expression.gi_frame.f_locals['.0']
        self.constraint = get_constraints(expression)
        _function = generator_to_function(expression)
        if isinstance(self.domain, _ConstrainedSet):
            _constraint = self.domain.constraint
            def constrained_function(*args):
                if _constraint(*args):
                    return _function(*args)
                else:
                    raise ValueError("Variable do not satisfy the constraint.")
            self.function = constrained_function
        else:
            self.function = _function
        self.elements = None

    def __call__(self, *element):
        return self.function(*element)

    def __iter__(self):
        if self.elements is None:
            self.elements = numpy.array(list(self.expression))
        return _ConstrainedSet(iter(self.elements), self.constraint)


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


Universal = U  = "𝕌"
Naturals0 = N0 = "ℕ0"
Naturals1 = N1 = "ℕ1"
Integers  = Z  = "ℤ"
Rationals = Q  = "ℚ"
Reals     = R  = "ℝ"
Complexes = C  = "ℂ"
Empty     = E  = "Ø"
