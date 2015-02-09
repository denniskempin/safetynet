import re
import inspect
import collections
import abc

__all__ = [
  "typecheck",
  "Iterable",
  "Mapping",
  "Optional",
  "Typename",
  "TypeChecker",
  "TypecheckMeta",
  "InterfaceMeta"
]


param_regexp_str = "^\s*:param\s+([^:]*?)([^\s:]+):\s*(.*?)\s*$"
param_regexp = re.compile(param_regexp_str, re.MULTILINE)

returns_regexp_str = "^\s*:returns\s+([^:]+):\s*(.*?)\s*$"
returns_regexp = re.compile(returns_regexp_str, re.MULTILINE)

type_regexp_str = "^\s*:type\s+([^:]+):\s*(.*?)\s*$"
type_regexp = re.compile(type_regexp_str, re.MULTILINE)

rtype_regexp_str = "^\s*:rtype\s*:\s*(.*?)\s*$"
rtype_regexp = re.compile(rtype_regexp_str, re.MULTILINE)


class TypecheckMeta(abc.ABCMeta):
  """ Metaclass to automatically decorate all members with @typecheck

  This metaclass will ensure that all members are properly decorated with
  typechecks and also allows this class to automatically inherit it's method's
  types to subclasses. This allows the user to override methods without
  re-defining the types.
  """
  def __new__(cls, class_name, parents, dct):
    typecheck_parent = cls.FindTypecheckParent(parents)
    for name, member in cls.ListMethodsOfInterest(dct):
      parent_member = cls.FindParentMember(typecheck_parent, name)
      dct[name] = cls.Decorate(class_name, member, parent_member)

    return abc.ABCMeta.__new__(cls, class_name, parents, dct)

  @classmethod
  def ListMethodsOfInterest(cls, dct):
    for name, member in dct.items():
      if inspect.isfunction(member) and not name.endswith("__"):
        yield name, member

  @classmethod
  def Decorate(cls, class_name, member, parent_member):
    """Decorates a member with @typecheck. Inherit checks from parent member."""
    if hasattr(member, "type_check_dict"):
      return member

    parent_type_check_dict = {}
    if parent_member and hasattr(parent_member, "type_check_dict"):
      parent_type_check_dict = parent_member.type_check_dict

    return _TypecheckFunction(member, parent_type_check_dict, 3, class_name)

  @classmethod
  def FindTypecheckParent(cls, parents):
    """Find parent class that uses this metaclass."""
    for parent in parents:
      if hasattr(parent, "__metaclass__") and parent.__metaclass__ == cls:
        return parent
    return None

  @classmethod
  def FindParentMember(cls, typecheck_parent, name):
    """Returns member by name from parent class if it exists."""
    if typecheck_parent and hasattr(typecheck_parent, name):
      return getattr(typecheck_parent, name)
    return None


class InterfaceMeta(TypecheckMeta):
  """Extends TypecheckMeta with checks to ensure Interface boundaries.

  Classes defined with his meta class will not allow any subclasses that
  override it's public methods with different argument names, nor any other
  public methods.
  """
  def __new__(cls, class_name, parents, dct):
    typecheck_parent = cls.FindTypecheckParent(parents)

    for name, member in cls.ListMethodsOfInterest(dct):
      parent_member = cls.FindParentMember(typecheck_parent, name)
      if typecheck_parent:
        cls.CheckOverridenArgumentNames(class_name, member, parent_member)
        cls.CheckUndefinedPublicMethod(class_name, name,
                                       typecheck_parent.__name__,
                                       parent_member)
      dct[name] = cls.Decorate(class_name, member, parent_member)

    # Note: We are not calling TypeCheckMeta.__new__ since we decorated all
    # members already.
    return abc.ABCMeta.__new__(cls, class_name, parents, dct)

  @classmethod
  def CheckOverridenArgumentNames(cls, class_name, member, parent_member):
    if parent_member and hasattr(parent_member, "wrapped_function"):
      parent_arg_names = inspect.getargspec(parent_member.wrapped_function)[0]
      arg_names = inspect.getargspec(member)[0]
      if parent_arg_names != arg_names:
        message = "Overriding %s.%s in %s with different argument names"
        message = message % (parent_member.im_class.__name__,
                             parent_member.__name__, class_name)
        raise TypeError(message)

  @classmethod
  def CheckUndefinedPublicMethod(cls, class_name, member_name, parent_name,
                                 parent_member):
    if not parent_member and not member_name.startswith("_"):
      message = "Public method %s.%s has not been defined in %s"
      message = message % (class_name, member_name, parent_name)
      raise TypeError(message)

def _FormatTypeCheck(type_):
  """Pretty format of type check."""
  if isinstance(type_, TypeChecker):
    return repr(type_)
  else:
    return type_.__name__

class TypeChecker(object):
  """Baseclass for all TypeCheckers."""
  pass

class Optional(TypeChecker):
  """Allows either None or subtype."""
  def __init__(self, subtype=None):
    self.subtype = subtype

  def __call__(self, value):
    if value is not None and self.subtype is not None:
      return _ValidateValue(value, self.subtype)
    return True

  def __repr__(self):
    return "Optional(%s)" % (_FormatTypeCheck(self.subtype)
                             if self.subtype else "")

class Typename(TypeChecker):
  """Allows only objects of a type with the name type_name."""
  def __init__(self, type_name=None):
    self.type_name = type_name

  def __call__(self, value):
    if self.type_name:
      return type(value).__name__ == self.type_name
    return True

  def __repr__(self):
    return "Typename(%s)" % self.type_name


class Iterable(TypeChecker):
  """Allows only iterable objects with all items being of item_type.

  If item_type is none, any item type is allowed.
  """
  def __init__(self, item_type=None):
    self.item_type = item_type

  def __call__(self, value):
    if not isinstance(value, collections.Iterable):
      return False
    if self.item_type is not None:
      for item in value:
        if not _ValidateValue(item, self.item_type):
          return False
    return True

  def __repr__(self):
    subtype = _FormatTypeCheck(self.item_type) if self.item_type else ""
    return "Iterable(%s)" % subtype


class Mapping(TypeChecker):
  """Allows only mapping (dict) objects with additional checks on each item.

  If key_type is specified, all keys have to be of that type.
  If value_type is specified, all values have to be of that type.
  """
  def __init__(self, key_type=None, value_type=None):
    self.key_type = key_type
    self.value_type = value_type

  def __call__(self, value):
    if not isinstance(value, collections.Mapping):
      return False
    if self.key_type is not None and self.value_type is not None:
      for key, item in value.items():
        if (self.key_type is not None and
            not _ValidateValue(key, self.key_type)):
          return False
        if (self.value_type is not None and
            not _ValidateValue(item, self.value_type)):
          return False
    return True

  def __repr__(self):
    subtype = ", ".join([
        _FormatTypeCheck(self.key_type) if self.key_type else "",
        _FormatTypeCheck(self.value_type) if self.value_type else ""
    ])
    return "Mapping(%s)" % subtype


def _ValidateValue(value, type_check):
  """Validate a single value with type_check."""
  if inspect.isclass(type_check):
    return isinstance(value, type_check)
  elif callable(type_check):
    return type_check(value)
  else:
    raise TypeError("Invalid type")


def _ParseTypeCheckString(type_check_string, stack_location, self_name):
  """Convert string version of a type_check into a python instance.

  Type checks can be either defined directly in python code or in a string.
  The syntax is exactly the same since we use eval to parse the string.

  :param int stack_location: For eval to get the right globals() scope,
    we require a stack_location to tell us the index in inspect.stack to
    where the string was defined.
  :param str self_name: Optional name of the class itself, which can be used
    to type check for an instance of a class you are currently defining, and
    thus would not be available in the globals namespace. If none, it will
    be quessed from the stack.
  """
  target_frame = inspect.stack()[stack_location][0]
  self_name = self_name or inspect.stack()[stack_location][3]
  eval_globals = target_frame.f_globals
  eval_locals = {self_name: Typename(self_name)}

  try:
    return eval(type_check_string, eval_globals, eval_locals)
  except:
    print "Exception while parsing", type_check_string
    raise


def _ParseDocstring(function):
  """Parses the functions docstring into a dictionary of type checks."""
  if not function.__doc__:
    return {}

  type_check_dict = {}
  for match in param_regexp.finditer(function.__doc__):
    type_str = match.group(1)
    name = match.group(2)
    type_check_dict[name] = type_str
  for match in returns_regexp.finditer(function.__doc__):
    type_check_dict["returns"] = match.group(1)

  for match in type_regexp.finditer(function.__doc__):
    name = match.group(1)
    type_str = match.group(2)
    type_check_dict[name] = type_str
  for match in rtype_regexp.finditer(function.__doc__):
    type_check_dict["returns"] = match.group(1)
  return type_check_dict


def _CollectArguments(function, args, kwargs):
  """Merges positional and keyword arguments into a single dict."""
  all_args = dict(kwargs)
  arg_names = inspect.getargspec(function)[0]
  for position, arg in enumerate(args):
    if position < len(arg_names):
      all_args[arg_names[position]] = arg
  return all_args


def _CollectTypeChecks(function, parent_type_check_dict, stack_location,
                      self_name):
  """Collect all type checks for this function."""
  type_check_dict = dict(parent_type_check_dict)
  type_check_dict.update(_ParseDocstring(function))

  # Convert any potential string based checks into python instances.
  for key, value in type_check_dict.items():
    if isinstance(value, str):
      type_check_dict[key] = _ParseTypeCheckString(value, stack_location + 1,
                                                  self_name)

  return type_check_dict


def _ValidateArguments(arg_dict, type_check_dict):
  """Validate dictionary of arguments and return list of errors messages."""
  messages = []
  for arg_name, arg_value in arg_dict.items():
    if arg_name in type_check_dict:
      type_check = type_check_dict[arg_name]
      res = _ValidateValue(arg_value, type_check)
      if not res:
        message = ("Invalid value '%s' for argument %s. Expected %s" %
                   (arg_value, arg_name, _FormatTypeCheck(type_check)))
        messages.append(message)
  return messages


def _ValidateReturnValue(return_value, type_check_dict):
  """Validate return value and return list of errors messages."""
  return_check = type_check_dict.get("returns", None)
  if not return_check:
    return []

  messages = []
  if not _ValidateValue(return_value, return_check):
    message = ("Invalid return value '%s'. Expected %s" %
               (return_value, _FormatTypeCheck(return_check)))
    messages.append(message)
  return messages


def _TypecheckFunction(function, parent_type_check_dict, stack_location,
                      self_name):
  """Decorator function to collect and execute type checks."""
  type_check_dict = _CollectTypeChecks(function, parent_type_check_dict,
                                      stack_location + 1, self_name)
  if not type_check_dict:
    return function

  def TypecheckWrapper(*args, **kwargs):
    arg_dict = _CollectArguments(function, args, kwargs)
    errors = _ValidateArguments(arg_dict, type_check_dict)
    if errors:
      raise TypeError("\n".join(errors))

    return_value = function(*args, **kwargs)

    errors = _ValidateReturnValue(return_value, type_check_dict)
    if errors:
      raise TypeError("\n".join(errors))
    return return_value

  TypecheckWrapper.__doc__ = function.__doc__
  TypecheckWrapper.__name__ = function.__name__
  TypecheckWrapper.type_check_dict = type_check_dict
  TypecheckWrapper.wrapped_function = function

  return TypecheckWrapper


def _TypecheckDecoratorFactory(kwargs):
  """Decorator factory for defining type checks in the decorator itself."""
  return lambda function: _TypecheckFunction(function, kwargs, 2, None)


def _TypecheckDecorator(subject=None, **kwargs):
  """Dispatches type checks based on what the subject is.

  Functions or methods are annotated directly. If this method is called
  with keyword arguments only, return a decorator.
  """
  if subject is None:
    return _TypecheckDecoratorFactory(kwargs)
  elif inspect.isfunction(subject) or inspect.ismethod(subject):
    return _TypecheckFunction(subject, {}, 2, None)
  else:
    raise TypeError()

typecheck = _TypecheckDecorator
"""Decorator to automatically check a functions argument types.

These types can either be defined directly in the decorator:
  @typecheck(a=int, b=str)
  def test(a, b):
    pass

Or in sphinx formatted docstrings:
  @typecheck
  def test(a, b):
    \"""
    :param int a:
    :param str b:
    \"""

For classes you can use the TypecheckMeta meta-class instead. For additional
options to check besides type, have a look at Iterable, Mapping or Optional.
"""