# safetynet (Deprecated in favor of PEP 484)
Type documentation and checking for python

## Motivation
Pythons flexible dynamic type system is great in many ways. However in bigger object oriented projects it can also become quite painful and reduce maintainability and also readability.

One solution to this is to extensively make use of :param tags in docstrings. In a perfect world that would be enough, however in reality those docstrings can easily be incorrect or become out of date. 

Safetynet allows you to have the types specified in docstrings checked automatically during runtime.

## Examples
```python
from safetynet import typecheck, Iterable, Mapping, Optional
@typecheck
def test_function(a, b, c, d, e):
  """ Docstring
    :param MyType a: description
    :param Iterable(int) b: description
    :param Mapping(str, int) c: description
    :param callable d: description
    :param Optional(int) e: description
    :returns int: description
  """
  return 1
```

The arguments will be checked at every call of the method.

You can specify any type you want or use the Iterable, Mapping helper to check for lists or dicts of certain types. Or any method that returns True/False when called with the argument value.
The types are evaluated at the time of definition. So if you want to use a type, you'll have to import it:
```python
@typecheck
def test_function(a):
  """
    :param UnknownType a: description
  """
# NameError: name 'UnknownName' is not defined
```

Is the docstring too verbose? You can use the decorator directly as an alternative:
```python
@typecheck(a=CustomType, b=Iterable(int), c=Mapping(str, int),
           d=callable, e=Optional(int), returns=int)
def test_function(a):
  pass
```

Using classes? You can automatically annotate all members using the TypecheckMeta meta class:
```python
class TypeCheckExample(object):
  __metaclass__ = TypecheckMeta

  def test_function(self, a, b, c, d, e):
    """ Docstring

      :type a: CustomType
      :type b: Iterable(int)
      :type c: Mapping(str, int)
      :type d: callable
      :type e: Optional(int)
      :rtype: int
    """
    return 1
```

The type checks will be inherited when you override the method in a subclass:
```python
class Subclass(TypeCheckExample):
  def test_function(self, a, b, c, d, e):
    """ Still has the same typechecks as TypeCheckExample.test_function."""
    return 2
```

## Why docstrings?
It's a standard way of annotating types and supported by many IDEs to infer variable types for autocomplete.
