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
from collections.abc import Iterable

from ._callback_lookup import CallbackMapping
from .expr import BinOp, Dice, Die, Expression, Literal, Number, Parenthetical, Set, SetOp, UnOp

__all__ = ('Formatter', 'MarkdownFormatter', 'SimpleFormatter')


class Formatter:
    def __init__(self) -> None:
        self._nodes: CallbackMapping[str] = {  # pyright: ignore[reportAttributeAccessIssue]
            Expression: self._format_expression,
            Literal: self._format_literal,
            UnOp: self._format_unop,
            BinOp: self._format_binop,
            Parenthetical: self._format_parenthetical,
            Set: self._format_set,
            Dice: self._format_dice,
            Die: self._format_die,
        }

    def format(self, node: Number[t.Any]) -> str:
        return self._format(node)

    def _format(self, node: Number[t.Any]) -> str:
        handler = self._nodes[type(node)]
        inner = handler(node)
        if node.annotation:
            return f'{inner} {node.annotation}'
        return inner

    def _format_expression(self, node: Expression) -> str:
        raise NotImplementedError

    def _format_literal(self, node: Literal) -> str:
        raise NotImplementedError

    def _format_unop(self, node: UnOp) -> str:
        raise NotImplementedError

    def _format_binop(self, node: BinOp) -> str:
        raise NotImplementedError

    def _format_parenthetical(self, node: Parenthetical) -> str:
        raise NotImplementedError

    def _format_set(self, node: Set[t.Any]) -> str:
        raise NotImplementedError

    def _format_dice(self, node: Dice) -> str:
        raise NotImplementedError

    def _format_die(self, node: Die) -> str:
        raise NotImplementedError

    @staticmethod
    def _format_ops(ops: Iterable[SetOp]) -> str:
        return ''.join(str(op) for op in ops)


class SimpleFormatter(Formatter):
    def _format_expression(self, node: Expression) -> str:
        return f'{self._format(node.roll)} = {int(node.total)}'

    def _format_literal(self, node: Literal) -> str:  # noqa: PLR6301
        history = ' -> '.join(str(v) for v in node.values)
        if node.exploded:
            return f'{history}!'
        return history

    def _format_unop(self, node: UnOp) -> str:
        return f'{node.op}{self._format(node.value)}'

    def _format_binop(self, node: BinOp) -> str:
        return f'{self._format(node.left_)} {node.op} {self._format(node.right_)}'

    def _format_parenthetical(self, node: Parenthetical) -> str:
        return f'({self._format(node.value)}){self._format_ops(node.ops)}'

    def _format_set(self, node: Set[t.Any]) -> str:
        out = f'{", ".join(self._format(v) for v in node.values)}'
        if len(node.values) == 1:
            return f'({out},){self._format_ops(node.ops)}'
        return f'({out}){self._format_ops(node.ops)}'

    def _format_dice(self, node: Dice) -> str:
        dice = [self._format(die) for die in node.values]
        return f'{node.num}d{node.sides}{self._format_ops(node.ops)} ({", ".join(dice)})'

    def _format_die(self, node: Die) -> str:
        return ', '.join(self._format(v) for v in node.values)


class MarkdownFormatter(SimpleFormatter):
    class _Context:
        def __init__(self) -> None:
            self.in_dropped = False

        def reset(self) -> None:
            self.in_dropped = False

    def __init__(self) -> None:
        super().__init__()
        self._context = self._Context()

    def format(self, node: Number[t.Any]) -> str:
        self._context.reset()
        return super().format(node)

    def _format(self, node: Number[t.Any]) -> str:
        if not node.kept and not self._context.in_dropped:
            self._context.in_dropped = True
            inner = super()._format(node)
            self._context.in_dropped = False
            return f'~~{inner}~~'
        return super()._format(node)

    def _format_expression(self, node: Expression) -> str:
        return f'{self._format(node.roll)} = `{int(node.total)}`'

    def _format_die(self, node: Die) -> str:
        rolls: list[str] = []
        for v in node.values:
            inner = self._format(v)
            if v.number in {1, node.sides}:
                inner = f'**{inner}**'
            rolls.append(inner)
        return ', '.join(rolls)
