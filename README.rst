###
🎲
###

A reasonably fast, powerful, and extensible dice engine for D&D, and any other
systems that need dice.

Features
********

- Easy to get started. ``dice.roll()`` should cover most common cases.
- Optimized for speed and memory efficiency.
- Extensible API to customize behaviours and formatting of dice.
- Execution limits built in.
- Tree-like expression representation for easy manipulation.

Installation
************

**Python 3.12 or higher required**.

.. code-block:: console

  $ pip install git+https://github.com/lmaotrigine/dice

If ``numpy`` is installed, a PCG64DXSM random number generator is used, which
provides better performance and quality than the standard library. You can
install this package with ``numpy`` using the ``pcg`` extra:

.. code-block:: console

  $ pip install 'lmaotrigine-dice[pcg] @ git+https://github.com/lmaotrigine/dice'


Getting started
***************

.. code-block:: pycon

  >>> import dice
  >>> result = dice.roll('1d20+5')
  >>> str(result)
  '1d20 (14) + 5 = `19`'
  >>> result.total
  19
  >>> result.crit
  <Crit.none: 0>
  >>> str(result.ast)
  '1d20 + 5'

Dice syntax
***********

This is the grammar supported by the parser, roughly in binding order

Numbers
=======

The smallest syntactical units.

.. list-table::
  :header-rows: 1

  * - Name
    - Syntax
    - Description
    - Examples
  * - literal
    - ``INTEGER | DECIMAL``
    - A literal number
    - ``1``, ``3.14``, ``.4``
  * - dice
    - ``INTEGER? "d" (INTEGER | "%")``
    - ``NdS``: ``N`` dice of ``S`` sides
    - ``d20``, ``3d8``
  * - set
    - ``"(" (expr ("," expr)* ","?)? ")"``
    - A set of expressions
    - ``()``, ``(1,)``, ``(1, 3 + 3, 1d20)``

Note that ``(3d8)`` is equivalent to ``3d8``, but ``(3d8,)`` is the set
containing a single ``3d8`` element. This mirrors Python syntax for tuples.

Set operations
==============

Operations that can be performed on dice and sets. They are expressed as
``operator selector`` pairs, where ``operator`` is applied on each item that
satisfies ``selector``

Operators
---------

Operators are followed by a selector, and are applied to the items that match
the selector

.. list-table::
  :header-rows: 1

  * - Name
    - Syntax
    - Description
  * - keep
    - ``k``
    - Keep only matched values
  * - drop
    - ``p``
    - Drop matched values
  * - re-roll
    - ``rr``
    - Dice only. Re-roll matched values until there are no matches
  * - re-roll once
    - ``ro``
    - Dice only. Re-roll matched values once
  * - re-roll and add
    - ``ra``
    - Dice only. Re-roll the first matched value once, keeping the original roll
  * - explode on
    - ``e``
    - Dice only. Roll another dice for each matched value
  * - minimum
    - ``mi``
    - Dice only. Set the minimum value for each die
  * - maximum
    - ``ma``
    - Dice only. Set the maximum value for each die

Selectors
---------

Selectors match values from kept values in dice or a set

.. list-table::
  :header-rows: 1

  * - Name
    - Syntax
    - Description
  * - literal
    - ``X``
    - Match values in the set that are exactly ``X``
  * - highest
    - ``hX``
    - Match the highest ``X`` values in the set
  * - lowest
    - ``lX``
    - Match the lowest ``X`` values in the set
  * - greater than
    - ``>X``
    - Match values in the set that are greater than ``X``
  * - less than
    - ``<X``
    - Match values in the set that are less than ``X``

Unary operators
===============

.. list-table::
  :header-rows: 1

  * - Name
    - Syntax
    - Description
  * - positive
    - ``+X``
    - No-op
  * - negative
    - ``-X``
    - Negates the value of ``X``

Binary operators
================

PEMDAS precedence. Boolean operators are coerced to integers

.. list-table::
  :header-rows: 1

  * - Name
    - Syntax
  * - multiplication
    - ``X * Y``
  * - division
    - ``X / Y``
  * - integer division (rounded down)
    - ``X // Y``
  * - Euclidean modulus
    - ``X % Y``
  * - addition
    - ``X + Y``
  * - subtraction
    - ``X - Y``
  * - equality
    - ``X == Y``
  * - greater than or equal
    - ``X >= Y``
  * - less than or equal
    - ``X <= Y``
  * - less than
    - ``X < Y``
  * - greater than
    - ``X > Y``
  * - inequality
    - ``X != Y``

Example expressions
===================

.. code-block:: pycon

  >>> from dice import roll
  >>> r = roll('4d6kh3')  # highest 3 of 4 6-sided dice
  >>> r.total
  14
  >>> str(r)
  '4d6kh3 (~~**1**~~, 5, 4, 5) = `14`'

  >>> r = roll('2d6ro<3')  # roll 2d6s, then re-roll any 1s or 2s once
  >>> r.total
  10
  >>> str(r)
  '2d6ro<3 (**~~1~~**, **6**, 4) = `10`'

  >>> r = roll('8d6mi2')  # roll 8d6s, with each roll having a minimum value of 2
  >>> r.total
  33
  >>> str(r)
  '8d6mi2 (4, **6**, **6**, **6**, 1 -> 2, 2, 5, 2) = `33`'

  >>> r = roll('(1d4 + 1, 3, 2d6kl1)kh1')  # the highest of 1d4+1, 3, and the lower of 2 d6s
  >>> r.total
  4
  >>> str(r)
  '(~~1d4 (2) + 1~~, ~~3~~, 2d6kl1 (~~5~~, 4))kh1 = `4`'

Custom formatter
****************

By default, the result of each dice roll is formatted in Markdown. This might
not be useful in your application.

To change this behaviour, you can create a subclass of the abstract class
``dice.Formatter`` (or ``dice.SimpleFormatter`` for a base implementation), and
implement the ``_format_*`` methods to customize how each node type in the
expression tree is formatted. You can then pass an instance of this class to the
``roll`` function.

.. code-block:: pycon

  >>> import dice
  >>> class MyFormatter(dice.SimpleFormatter):
  ...     def _format(self, node):
  ...         if not node.kept:
  ...             return '\N{CROSS MARK}'
  ...         return super()._format(node)
  ...     def _format_expression(self, node):
  ...         return f'The result of the roll {self._format(node.roll)} was {int(node.total)}'
  ...
  >>> result = dice.roll('4d6e6kh3', formatter=MyFormatter())
  >>> str(result)
  'The result of the roll 4d6e6kh3 (6!, ❌, 5, 5, ❌) was 16'

Annotations and comments
************************

Each expression node supports value annotations - a method to assign parts of an
expression a tag. For example,

.. code-block:: pycon

  >>> from dice import roll
  >>> str(roll('3d6 [fire] + 1d4 [piercing]'))
  '3d6 (4, 3, 3) [fire] + 1d4 (**4**) [piercing] = `14`'

  >>> str(roll('-(1d8 + 3) [healing]'))
  '-(1d8 (4) + 3) [healing] = `-7`'

  >>> str(roll('(1 [one], 2 [two], 3 [three])'))
  '(1 [one], 2 [two], 3 [three]) = `6`'

Annotations are purely visual and do not affect the evaluation of the roll.

When ``allow_comments=True`` is passed to ``roll()``, the result of the roll may
have a comment. A comment is free text attached to the end of an expression
and is any sequence of characters that cannot be parsed.

.. code-block:: pycon

  >>> from dice import roll
  >>> result = roll('1d20 I rolled a d20', allow_comments=True)
  >>> str(result)
  '1d20 (15) = `15`'
  >>> result.comment
  'I rolled a d20'

When ``allow_comments`` is set to ``True``, caching of parse results is
disabled, which may lead to performance degradation over time.

Traversing the result tree
**************************

The raw results of rolls are represented as ``dice.Expression`` objects

.. code-block:: pycon

  >>> from dice import roll
  >>> result = roll('3d6 + 1d4 + 3')
  >>> str(result)
  '3d6 (2, 5, 4) + 1d4 (3) + 3 = `17`'
  >>> result.expr
  <Expression roll=<BinOp left=<BinOp left=<Dice num=3 sides=6 values=[<Die sides=6 values=[<Literal 2>]>, <Die sides=6 values=[<Literal 5>]>, <Die sides=6 values=[<Literal 4>]>] ops=[]> op=+ right=<Dice num=1 sides=4 values=[<Die sides=4 values=[<Literal 3>]>] ops=[]>> op=+ right=<Literal 3>> comment=None>

In a prettier format:

.. code-block:: text

  <Expression
    roll=<BinOp
      left=<BinOp
        left=<Dice
          num=3
          sides=6
          values=[
            <Die sides=6 values=[<Literal 2>]>,
            <Die sides=6 values=[<Literal 5>]>,
            <Die sides=6 values=[<Literal 4>]>
          ]
          ops=[]
        >
        op=+
        right=<Dice
          num=1
          sides=4
          values=[
            <Die sides=4 values=[<Literal 3>]>
          ]
          ops=[]
        >
      >
      op=+
      right=<Literal 3>
    >
    comment=None
  >

The ``Expression.children`` property returns a list of nodes that constitute the
expression from left to right, each of which may have children of their own.
This behaves like a regular tree, and is therefore well suited for operations
such as locating a specific die, finding the leftmost or rightmost leaf,
changing the result to include resistance or other modifications, etc.

Examples
========

Finding the leftmost/rightmost operands

.. code-block:: pycon

  >>> from dice import roll
  >>> binop = roll('1 + 2 + 3 + 4')
  >>> left = binop.expr
  >>> while left.children:
  ...     left = left.children[0]
  ...
  >>> left
  <Literal 1>

  >>> right = binop.expr
  >>> while right.children:
  ...     right = right.children[-1]
  ...
  >>> right
  <Literal 4>

  >>> from dice import utils  # these patterns are available in this module
  >>> utils.leftmost(binop.expr)
  <Literal 1>
  >>> utils.rightmost(binop.expr)
  <Literal 4>

Searching for the d4

.. code-block:: pycon

  >>> from dice import Dice, SimpleFormatter, roll, utils
  >>>
  >>> mixed = roll('-1d8 + 4 - (3, 1d4)kh1')
  >>> str(mixed)
  '-1d8 (5) + 4 - (3, ~~1d4 (**1**)~~)kh1 = `-4`'
  >>> root = mixed.expr
  >>> result = utils.dfs(root, lambda node: type(node) is Dice and node.num == 1 and node.sides == 4)
  >>> result
  <Dice num=1 sides=4 values=[<Die sides=4 values=[<Literal 1>]>] ops=[]>
  >>> SimpleFormatter().format(result)
  '1d4 (1)'

Performance
***********

By default, the parser caches the 256 most frequently used dice expressions,
which allows a significant speed-up when rolling the same kind of dice
numerous times. When ``allow_comments`` is set to ``True``, the results of that
roll are not cached. Here are some hasty, rudimentary benchmarks that are only
representative of relative speed-up

With caching:

.. code-block:: console

  $ python -m timeit -s 'from dice import roll' 'roll("1d20")'
  50000 loops, best of 5: 4.65 usec per loop
  $ python -m timeit -s 'from dice import roll' 'roll("100d20")'
  1000 loops, best of 5: 198 usec per loop
  $ python -m timeit -s 'from dice import roll; expr = "1d20 + " * 50 + "1d20"' 'roll(expr)'
  2000 loops, best of 5: 159 usec per loop
  $ python -m timeit -s 'from dice import roll' 'roll("10d20rr<20")'
  500 loops, best of 5: 483 usec per loop

Without caching:

.. code-block:: console

  $ python -m timeit -s 'from dice import roll' 'roll("1d20")'
  10000 loops, best of 5: 29.3 usec per loop
  $ python -m timeit -s 'from dice import roll' 'roll("100d20")'
  1000 loops, best of 5: 241 usec per loop
  $ python -m timeit -s 'from dice import roll; expr = "1d20 + " * 50 + "1d20"' 'roll(expr)'
  200 loops, best of 5: 1.14 msec per loop
  $ python -m timeit -s 'from dice import roll' 'roll("10d20rr<20")'
  500 loops, best of 5: 541 usec per loop
