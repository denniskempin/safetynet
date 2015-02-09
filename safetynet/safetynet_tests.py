import unittest
from collections import OrderedDict

from safetynet import typecheck, Iterable, Mapping, Optional, InterfaceMeta

class CustomType(object):
  pass

class CustomSubType(CustomType):
  pass

def DefineTypeCheckExample():
  """Defines an example class.

  Note that we are doing this in a function. Some errors detected by
  InterfaceMeta are thrown at the time of definition. We want to catch those
  in the tests.
  """
  class TypeCheckExample(object):
    __metaclass__ = InterfaceMeta

    def docstring_example(self, a, b, c, d, e, return_):
      """ Docstring

        :type a: CustomType
        :type b: Iterable(int)
        :type c: Mapping(str, int)
        :type d: callable
        :type e: Optional(int)
        :rtype: int
      """
      return return_

    @typecheck(a=CustomType, b=Iterable(int), c=Mapping(str, int),
           d=callable, e=Optional(int), returns=int)
    def annotation_example(self, a, b, c, d, e, return_):
      return return_

    @typecheck(a="TypeCheckExample")
    def self_reference_example(self, a):
      pass

    def self_reference_example2(self, a):
      """ Docstring
        :type a: TypeCheckExample
      """
  return TypeCheckExample


class TypeCheckTests(unittest.TestCase):

  def assert_correct_example_type_checks(self, function):
    """ Assumes function has the following type checks and tests them.

      a: CustomType
      b: Iterable(int)
      c: Mapping(str, int)
      d: callable
      e: Optional(int)
      return value: int

      The function should return the argument: return_
    """
    def get_args(kwargs):
      defaults = [("a", CustomType()), ("b", []), ("c", {}),
            ("d", lambda: None), ("e", 1), ("return_", 1)]
      args = OrderedDict(defaults)
      args.update(kwargs)
      return args
    def assert_success(**kwargs):
      args = get_args(kwargs)
      function(*args.values())
      function(**args)
    def assert_failure(**kwargs):
      args = get_args(kwargs)
      self.assertRaises(TypeError, function, *args.values())
      self.assertRaises(TypeError, function, **args)

    # Test CustomType
    assert_success(a=CustomSubType())
    assert_failure(a=1)
    assert_failure(a=None)

    # Test Iterable(int)
    assert_success(b=[1, 2, 3])
    assert_failure(b=[1.0])
    assert_failure(b=[1, None, 3])
    assert_failure(b=None)

    # Test Mapping(str, int)
    assert_success(c={"key": 1})
    assert_failure(c={"key": None})
    assert_failure(c={"key": "1"})
    assert_failure(c={1: 1})
    assert_failure(c=None)

    # Test callable
    def dummy():
      pass
    assert_success(d=lambda a, b, c: None)
    assert_success(d=dummy)
    assert_success(d=CustomType)
    assert_failure(d=None)
    assert_failure(d=1)

    # Test Optional(int)
    assert_success(e=1)
    assert_success(e=None)
    assert_failure(e=1.0)

    # Test return value
    assert_failure(return_=1.0)
    assert_failure(return_=None)

  def test_type_annotation(self):
    @typecheck(a=CustomType, b=Iterable(int), c=Mapping(str, int),
           d=callable, e=Optional(int), returns=int)
    def test_function(a, b, c, d, e, return_):
      return return_
    self.assert_correct_example_type_checks(test_function)

  def test_string_type_annotation(self):
    @typecheck(a="CustomType", b="Iterable(int)", c="Mapping(str, int)",
           d="callable", e="Optional(int)", returns="int")
    def test_function(a, b, c, d, e, return_):
      return return_
    self.assert_correct_example_type_checks(test_function)

  def test_docstring_param_annotation(self):
    @typecheck
    def test_function(a, b, c, d, e, return_):
      """ Docstring

        :param CustomType a: description
        :param Iterable(int) b: description
        :param Mapping(str, int) c: description
        :param callable d: description
        :param Optional(int) e: description
        :returns int: description
      """
      return return_
    self.assert_correct_example_type_checks(test_function)

  def test_docstring_type_annotation(self):
    @typecheck
    def test_function(a, b, c, d, e, return_):
      """ Docstring

        :type a: CustomType
        :type b: Iterable(int)
        :type c: Mapping(str, int)
        :type d: callable
        :type e: Optional(int)
        :rtype: int
      """
      return return_
    self.assert_correct_example_type_checks(test_function)

  def test_class_docstring_annotation(self):
    instance = DefineTypeCheckExample()()
    self.assert_correct_example_type_checks(instance.docstring_example)

  def test_class_type_annotation(self):
    instance = DefineTypeCheckExample()()
    self.assert_correct_example_type_checks(instance.annotation_example)

  def test_class_self_reference(self):
    instance = DefineTypeCheckExample()()
    instance.self_reference_example(instance)
    instance.self_reference_example2(instance)
    self.assertRaises(TypeError, instance.self_reference_example, None)
    self.assertRaises(TypeError, instance.self_reference_example2, None)

  def test_class_inheritance_typechecks(self):
    class InheritedExample(DefineTypeCheckExample()):
      pass
    instance = InheritedExample()
    self.assert_correct_example_type_checks(instance.docstring_example)
    self.assert_correct_example_type_checks(instance.annotation_example)

  def test_class_override_typechecks(self):
    class OverrideExample(DefineTypeCheckExample()):
      def docstring_example(self, a, b, c, d, e, return_):
        return return_
    instance = OverrideExample()
    self.assert_correct_example_type_checks(instance.docstring_example)
    self.assert_correct_example_type_checks(instance.annotation_example)

  def test_compile_time_type_errors(self):
    self.assertRaises(TypeError, typecheck, (), dict(a="UnknownName"))

  def test_docstring_preserved(self):
    @typecheck
    def test_function():
      "docstring"
    self.assertEqual(test_function.__doc__, "docstring")

  def test_return_value_preserved(self):
    @typecheck
    def test_function():
      return 42
    self.assertEqual(test_function(), 42)

  def test_class_override_arguments_check(self):
    def DefineClass():
      class OverrideExample(DefineTypeCheckExample()):
        def docstring_example(self, a, b, c, CHANGES, e, return_):
          return return_
    self.assertRaises(TypeError, DefineClass)

  def test_class_override_public_check(self):
    def DefineClass():
      class OverrideExample(DefineTypeCheckExample()):
        def public_method_not_defined_in_interface(self):
          pass
    self.assertRaises(TypeError, DefineClass)

  def test_class_variables_untouched(self):
    class VariablesExample:
      __metaclass__ = InterfaceMeta
      variable = 1
    self.assertEqual(VariablesExample.variable, 1)
