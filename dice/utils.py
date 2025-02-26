# Copyright (c) 2019-present, Isis E., All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import annotations

import copy
import typing as t
from collections.abc import Callable

from . import ast_ as ast, expr
from .enums import Advantage

__all__ = ('ast_adv_copy', 'dfs', 'leftmost', 'rightmost', 'simplify', 'simplify_annotations', 'tree_map')


def ast_adv_copy[N: ast.Node[ast.Node[t.Any]]](n: N, advantage: Advantage) -> N:
    """Return a minimally shallow copy of a dice AST with respect to advantage.

    Examples
    --------

    .. code-block:: pycon

        >>> tree = dice.parse('1d20 + 5')
        >>> str(tree)
        '1d20 + 5'
        >>> str(ast_adv_copy(tree, dice.Advantage.adv))
        '2d20kh1 + 5'

    Parameters
    ----------
    n:
        The parsed AST.
    advantage:
        The advantage to roll at.

    Returns
    -------
    The copied AST.
    """
    root = copy.copy(n)
    if not advantage:
        return root
    parent = child = root
    while child.children:
        parent = child
        assert parent.left
        parent.left = child = copy.copy(parent.left)
    if not isinstance(child, ast.DiceExpr):
        return root
    if not (child.num == 1 and child.sides == 20):
        return root
    if not isinstance(parent, ast.Dice):
        new_parent = ast.Dice(child)
        parent.left = new_parent
        parent = new_parent
    else:
        parent.ops = parent.ops.copy()
    child.num = 2
    hilo = ast.SetSel('h', 1) if advantage == 1 else ast.SetSel('l', 1)
    kh1 = ast.SetOp('k', [hilo])
    parent.ops.insert(0, kh1)
    return root


def simplify_annotations(
    expr_: expr.Number[expr.Number[t.Any]], ambig_inherit: t.Literal['left', 'right'] | None = None
) -> None:
    """Simplify an expression tree's annotations in-place.

    Simplification is done using a bubble-up method.

    Examples
    --------

    .. code-block:: pycon

        >>> roll_expr = dice.roll('1d20[foo] + 3').expr
        >>> simplify_annotations(roll_expr.roll)
        >>> dice.SimpleFormatter().format(roll_expr)
        '1d20 (4) + 3 [foo] = 7'

    Parameters
    ----------
    expr:
        The expression to transform.
    ambig_inherit:
        When encountering a child node with no annotation and the parent has
        ambiguous types, which to inherit. Can be one of:
        * ``None`` for no inherit
        * ``'left'`` for leftmost
        * ``'right'`` for rightmost.

    Raises
    ------
    ValueError
        If ``ambig_inherit`` is not one of ``'left'``, ``'right'``, or ``None``.
    """
    if ambig_inherit not in {'left', 'right', None}:
        msg = 'ambig_inherit must be "left", "right", or None'
        raise ValueError(msg)

    def do_simplify(node: expr.Number[expr.Number[t.Any]]) -> tuple[str | None, ...]:
        possible_types: list[str | None] = []
        child_possibilities: dict[expr.Number[t.Any], tuple[str | None, ...]] = {}
        for child in node.children:
            child_possibilities[child] = do_simplify(child)
            possible_types.extend(t for t in child_possibilities[child] if t not in possible_types)
        if node.annotation is not None:
            possible_types.append(node.annotation)
        if len(possible_types) == 1:
            node.annotation = possible_types[0]
            for child in node.children:
                child.annotation = None
        elif possible_types and ambig_inherit is not None:
            for i, child in enumerate(node.children):
                if child_possibilities[child]:
                    continue
                if isinstance(node, expr.BinOp) and node.op in {'*', '/', '//', '%'} and i:
                    continue
                if ambig_inherit == 'left':
                    child.annotation = possible_types[0]
                elif ambig_inherit == 'right':
                    child.annotation = possible_types[-1]
        return tuple(possible_types)

    do_simplify(expr_)


def simplify(expr_: expr.Expression, *, ambig_inherit: t.Literal['left', 'right'] | None = None) -> None:
    """Simplify an expression tree in-place.

    Simplifying involves removing all dice and evaluating branches with
    respect to annotations.

    Examples
    --------

    .. code-block:: pycon

        >>> roll_expr = dice.roll('1d20[foo] + 3 - 1d4[bar]').expr
        >>> simplify(roll_expr)
        >>> dice.SimpleFormatter().format(roll_expr)
        '7 [foo] - 2 [bar] = 5'

    Parameters
    ----------
    expr:
        The expression to transform.
    ambig_inherit:
        When encountering a child node with no annotation and the parent has
        ambiguous types, which to inherit. Can be one of:
        * ``None`` for no inherit
        * ``'left'`` for leftmost
        * ``'right'`` for rightmost.
    """
    simplify_annotations(expr_.roll, ambig_inherit)

    def do_simplify(node: expr.Number[expr.Number[t.Any]], *, first: bool = False) -> tuple[expr.Number[t.Any], bool]:
        if node.annotation:
            return expr.Literal(node.total, annotation=node.annotation), True
        had_replacement: set[int] = set()
        for i, child in enumerate(node.children):
            replacement, branch_had = do_simplify(child)
            if branch_had:
                had_replacement.add(i)
            if replacement is not child:
                node.set_child(i, replacement)
        for i, child in enumerate(node.children):
            if i not in had_replacement and (had_replacement or first):
                replacement = expr.Literal(child.total)
                node.set_child(i, replacement)
        return node, bool(had_replacement)

    do_simplify(expr_, first=True)


def tree_map[T: (ast.Node[t.Any], expr.Number[t.Any])](fn: Callable[[T], T], tree: T) -> T:
    """Return a new tree with ``fn`` applied to each node.

    The original tree is not modified.

    Parameters
    ----------
    fn:
        The function to apply to each node.
    tree:
        The tree to map.

    Returns
    -------
    The new tree with ``fn`` applied to each node.
    """
    copied = copy.copy(tree)
    for i, child in enumerate(copied.children):
        copied.set_child(i, tree_map(fn, child))
    return fn(copied)


def leftmost[T: (ast.Node[t.Any], expr.Number[t.Any])](tree: T) -> T:
    """Return the leftmost node in the tree.

    Parameters
    ----------
    tree:
        The tree to search.

    Returns
    -------
    The leftmost node in the tree.
    """
    left = tree
    while left.children:
        left = left.children[0]
    return left


def rightmost[T: (ast.Node[t.Any], expr.Number[t.Any])](tree: T) -> T:
    """Return the rightmost node in the tree.

    Parameters
    ----------
    tree:
        The tree to search.

    Returns
    -------
    The rightmost node in the tree.
    """
    right = tree
    while right.children:
        right = right.children[-1]
    return right


def dfs[T: (ast.Node[t.Any], expr.Number[t.Any])](predicate: Callable[[T], bool], tree: T) -> T | None:
    """Return the first element in the tree that meets the predicate.

    The tree is searched depth-first, left-to-right.

    For example: ::

        d4 = dice.utils.dfs(expr, lambda n: isinstance(n, dice.Dice) and n.sides  == 4)

    would find the first dice node with 4 sides. If a node is not found, then
    ``None`` is returned.

    Parameters
    ----------
    tree:
        The tree to search.
    predicate:
        A callable that returns a boolean-like result.

    Returns
    -------
    The first node that meets the predicate, or ``None`` if no node is found.
    """
    if predicate(tree):
        return tree
    for child in tree.children:
        res = dfs(predicate, child)
        if res is not None:
            return res
    return None
