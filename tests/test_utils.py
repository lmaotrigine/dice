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

import copy
import re
from typing import Any

from dice import Advantage, ast_ as ast, parse, roll, utils
from dice.expr import Dice, Literal, Number, Set
from dice.formatters import SimpleFormatter


class TestAstAdvCopy:
    @staticmethod
    def test_adv() -> None:
        for expr in ('1d20', '1d20+1', '1d20-1d4'):
            tree = parse(expr)
            original = copy.deepcopy(tree)
            adv_tree = utils.ast_adv_copy(tree, Advantage.adv)
            assert str(adv_tree).startswith('2d20kh1')
            assert str(adv_tree) != str(original)
            adv_tree = utils.ast_adv_copy(tree, Advantage.dis)
            assert str(adv_tree).startswith('2d20kl1')
            assert str(adv_tree) != str(original)
            adv_tree = utils.ast_adv_copy(tree, Advantage.none)
            assert str(adv_tree).startswith('1d20')
            assert str(adv_tree) == str(original)

    @staticmethod
    def test_inapplicable() -> None:
        for expr in ('1', '1d6', '1+1'):
            tree = parse(expr)
            original = copy.deepcopy(tree)
            adv_tree = utils.ast_adv_copy(tree, Advantage.adv)
            assert str(adv_tree) == str(original)

    @staticmethod
    def test_copy() -> None:
        for expr in ('1d20', '1d20ro1'):
            tree = parse(expr)
            adv_tree = utils.ast_adv_copy(tree, Advantage.adv)
            assert tree is not adv_tree
            assert str(tree) != str(adv_tree)
            assert str(parse(expr)) == str(tree)


class TestSimplifyAnnotations:
    @staticmethod
    def test_annotation_simplify() -> None:
        expr = roll('1 [a] +2 + 3 [b] + 4').expr
        utils.simplify_annotations(expr, None)
        assert SimpleFormatter().format(expr) == '1 + 2 [a] + 3 [b] + 4 = 10'
        expr = roll('1 [a] + 2 + 3 [b] + 4').expr
        utils.simplify_annotations(expr, 'left')
        assert SimpleFormatter().format(expr) == '1 + 2 [a] + 3 [b] + 4 [a] = 10'
        expr = roll('1 [a] + 2 + 3 [b] + 4').expr
        utils.simplify_annotations(expr, 'right')
        assert SimpleFormatter().format(expr) == '1 + 2 [a] + 3 [b] + 4 [b] = 10'
        expr = roll('1 [a] + 2 + 3 [a] + 4').expr
        utils.simplify_annotations(expr.roll)
        assert SimpleFormatter().format(expr) == '1 + 2 + 3 + 4 [a] = 10'

    @staticmethod
    def test_parenthetical_annotation() -> None:
        expr = roll('(1 [a])').expr
        utils.simplify_annotations(expr.roll)
        assert SimpleFormatter().format(expr) == '(1) [a] = 1'

    @staticmethod
    def test_simplify() -> None:
        expr = roll('1 [a] + 2 + 3 [b] + 4').expr
        utils.simplify(expr)
        assert SimpleFormatter().format(expr) == '3 [a] + 3 [b] + 4 = 10'
        expr = roll('1 [a] + 2 + 3').expr
        utils.simplify(expr)
        assert SimpleFormatter().format(expr) == '6 [a] = 6'
        expr = roll('1 + 2 + 3 + 4').expr
        utils.simplify(expr)
        assert SimpleFormatter().format(expr) == '10 = 10'
        expr = roll('8d6').expr
        utils.simplify(expr)
        assert re.match(r'(\d+) = \1', SimpleFormatter().format(expr))
        expr = roll('8d6 [fire]').expr
        utils.simplify(expr)
        assert re.match(r'(\d+) \[fire] = \1', SimpleFormatter().format(expr))


class TestTreeMap:
    @staticmethod
    def test_ast_map() -> None:
        tree = parse('1d20 + 4d6 + 3')

        def mapper[T: ast.Node[Any]](node: T) -> T:
            if isinstance(node, ast.DiceExpr):
                node.num *= 2
            return node

        mapped = utils.tree_map(mapper, tree)
        assert mapped is not tree
        assert str(mapped) == '2d20 + 8d6 + 3'
        assert str(tree) == '1d20 + 4d6 + 3'

    @staticmethod
    def test_expr_map() -> None:
        expr = roll('1 + 2 +3').expr

        def mapper[T: Number[Any]](node: T) -> T:
            if isinstance(node, Literal):
                copied = node.values.copy()
                copied[-1] *= 2
                node.values = copied
            return node

        mapped = utils.tree_map(mapper, expr)
        assert SimpleFormatter().format(mapped) == '2 + 4 + 6 = 12'
        assert mapped.total == 12
        assert mapped is not expr
        assert SimpleFormatter().format(expr) == '1 + 2 + 3 = 6'

    @staticmethod
    def test_ast_map_set_copy() -> None:
        tree = parse('(1d6, 1d6)kh1')

        def mapper(node: ast.Node[Any]) -> ast.Node[Any]:
            if isinstance(node, ast.DiceExpr):
                return ast.DiceExpr(node.num * 2, node.sides)
            return node

        mapped = utils.tree_map(mapper, tree)
        assert str(mapped) == '(2d6, 2d6)kh1'
        assert mapped is not tree
        assert str(tree) == '(1d6, 1d6)kh1'

    @staticmethod
    def test_expr_map_set_copy() -> None:
        expr = roll('(1, 2, 3)').expr

        def mapper[T: Number[Any]](node: T) -> T:
            if isinstance(node, Literal):
                copied = node.values.copy()
                copied[-1] *= 2
                node.values = copied
            return node

        mapped = utils.tree_map(mapper, expr)
        assert SimpleFormatter().format(mapped) == '(2, 4, 6) = 12'
        assert mapped.total == 12
        assert mapped is not expr
        assert SimpleFormatter().format(expr) == '(1, 2, 3) = 6'

    @staticmethod
    def test_expr_map_types() -> None:
        expr = roll('(1, 2, 3) + (4, 5, 6)').expr

        def mapper(node: Number[Any]) -> Number[Any]:
            if isinstance(node, Set):
                return Literal(int(node))
            return node

        mapped = utils.tree_map(mapper, expr)
        assert SimpleFormatter().format(mapped) == '6 + 15 = 21'
        assert mapped.total == 21
        assert mapped is not expr
        assert SimpleFormatter().format(expr) == '(1, 2, 3) + (4, 5, 6) = 21'


def test_leftmost() -> None:
    tree = parse('1d20 + 4d6 + 3')
    assert str(utils.leftmost(tree)) == '1d20'
    expr = roll(tree).expr
    assert SimpleFormatter().format(utils.leftmost(expr)).startswith('1d20 ')


def test_rightmost() -> None:
    tree = parse('1d20 + 4d6 + 3')
    assert str(utils.rightmost(tree)) == '3'
    expr = roll(tree).expr
    assert SimpleFormatter().format(utils.rightmost(expr)) == '3'


def test_dfs() -> None:
    mixed = roll('-1d8 + 4 - (3, 1d4)kh1')
    result = utils.dfs(lambda n: isinstance(n, Dice) and n.num == 1 and n.sides == 4, mixed.expr)
    assert result
    assert SimpleFormatter().format(result).startswith('1d4 ')
