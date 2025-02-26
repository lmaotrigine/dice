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

import typing as t

import lark

from . import ast_ as ast, rand, utils
from ._callback_lookup import CallbackMapping
from .cache import Cache
from .context import Context
from .enums import Advantage, Crit
from .errors import DiceSyntaxError
from .expr import BinOp, Dice, Expression, Literal, Number, Parenthetical, Set, SetOp, UnOp
from .formatters import Formatter, MarkdownFormatter

__all__ = ('Result', 'Roller')


class Result:
    def __init__(self, ast_: ast.Expression, roll: Expression, formatter: Formatter) -> None:
        self.ast: ast.Expression = ast_
        self.expr: Expression = roll
        self.formatter: Formatter = formatter
        self.comment: str | None = roll.comment

    @property
    def total(self) -> int:
        return int(self.expr.total)

    @property
    def result(self) -> str:
        return self.formatter.format(self.expr)

    @property
    def crit(self) -> Crit:
        left = utils.leftmost(self.expr)
        if not isinstance(left, Dice):
            return Crit.none
        if not (len(left.kept_set) == 1 and left.sides == 20):
            return Crit.none
        if left.total == 1:
            return Crit.failure
        if left.total == 20:
            return Crit.success
        return Crit.none

    def __str__(self) -> str:
        return self.result

    def __int__(self) -> int:
        return self.total

    def __float__(self) -> float:
        return self.expr.total

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} total={self.total}>'


class Roller:
    def __init__(self, context: Context | None = None, rng: rand.Random = rand.impl) -> None:
        if context is None:
            context = Context()
        self._nodes: CallbackMapping[Number[t.Any]] = {  # pyright: ignore[reportAttributeAccessIssue]
            ast.Expression: self._eval_expression,
            ast.Annotated: self._eval_annotated,
            ast.Literal: self._eval_literal,
            ast.Parenthetical: self._eval_parenthetical,
            ast.UnOp: self._eval_unop,
            ast.BinOp: self._eval_binop,
            ast.Set: self._eval_set,
            ast.SetExpr: self._eval_setexpr,
            ast.Dice: self._eval_dice,
            ast.DiceExpr: self._eval_diceexpr,
        }
        self._cache: Cache[str, ast.Expression] = Cache(256)
        self.context: Context = context
        self.rng: rand.Random = rng

    def roll(
        self,
        expr: str | ast.Expression,
        *,
        formatter: Formatter | None = None,
        allow_comments: bool = False,
        advantage: Advantage = Advantage.none,
    ) -> Result:
        if formatter is None:
            formatter = MarkdownFormatter()
        self.context.reset()
        tree = self.parse(expr, allow_comments=allow_comments) if isinstance(expr, str) else expr
        if advantage is not Advantage.none:
            tree = utils.ast_adv_copy(tree, advantage)
        dice_expr = self._eval_expression(tree)
        return Result(tree, dice_expr, formatter)

    def parse(self, expr: str, *, allow_comments: bool = False) -> ast.Expression:
        try:
            if not allow_comments:
                return self._parse_no_comment(expr)
            return self._parse_comment(expr)
        except lark.UnexpectedToken as e:
            raise DiceSyntaxError(line=e.line, col=e.column, got=expr[e.pos_in_stream or 0], expected=e.expected) from e

    def _parse_no_comment(self, expr: str) -> ast.Expression:
        clean = expr.replace(' ', '')
        try:
            return self._cache[clean]
        except KeyError:
            pass
        tree = ast.parser.parse(expr, start='expr')
        self._cache[clean] = tree
        return tree

    @staticmethod
    def _parse_comment(expr: str) -> ast.Expression:
        try:
            return ast.parser.parse(expr, start='commented_expr')
        except lark.UnexpectedInput as e:
            frag = expr[: e.pos_in_stream or 0]
            if frag.endswith('*'):
                frag = frag[:-1]
                force_comment = expr[len(frag) :]
            else:
                raise
            res: ast.Expression = ast.parser.parse(frag, start='commented_expr')
            res.comment = force_comment
            return res

    def _eval(self, node: ast.Node[t.Any]) -> Number[t.Any]:
        handler = self._nodes[type(node)]
        return handler(node)

    def _eval_expression(self, node: ast.Expression) -> Expression:
        return Expression(self._eval(node.roll), node.comment)

    def _eval_annotated(self, node: ast.Annotated) -> Number[t.Any]:
        target = self._eval(node.value)
        target.annotation = ''.join(node.annotations)
        return target

    @staticmethod
    def _eval_literal(node: ast.Literal) -> Literal:
        return Literal(node.value)

    def _eval_parenthetical(self, node: ast.Parenthetical) -> Parenthetical:
        return Parenthetical(self._eval(node.value))

    def _eval_unop(self, node: ast.UnOp) -> UnOp:
        return UnOp(node.op, self._eval(node.value))

    def _eval_binop(self, node: ast.BinOp) -> BinOp:
        return BinOp(self._eval(node.left_), node.op, self._eval(node.right_))

    def _eval_set(self, node: ast.Set) -> Parenthetical | Set[t.Any]:
        target = self._eval(node.value)
        assert isinstance(target, (Parenthetical, Set))
        for op in node.ops:
            op_ = SetOp.from_ast(op)
            op_.operate(target)
            target.ops.append(op_)
        return target

    def _eval_setexpr(self, node: ast.SetExpr) -> Set[t.Any]:
        return Set([self._eval(n) for n in node.values])

    def _eval_dice(self, node: ast.Dice) -> Number[t.Any]:
        return self._eval_set(node)

    def _eval_diceexpr(self, node: ast.DiceExpr) -> Dice:
        return Dice.new(node.num, node.sides, context=self.context, rng=self.rng)
