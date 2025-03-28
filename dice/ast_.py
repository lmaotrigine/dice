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

import pathlib
import typing as t
from collections.abc import Sequence
from functools import cache

import lark

__all__ = (
    'Annotated',
    'BinOp',
    'Dice',
    'DiceExpr',
    'Expression',
    'Literal',
    'Node',
    'Parenthetical',
    'Set',
    'SetExpr',
    'SetOp',
    'SetSel',
    'UnOp',
    'parser',
)


class NodeMixin[T: NodeMixin]:
    @property
    def children(self) -> Sequence[T]:
        raise NotImplementedError

    @property
    def left(self) -> T | None:
        try:
            return self.children[0]
        except IndexError:
            return None

    def __child_set_sanity(self, idx: int) -> None:
        if idx > len(self.children) - 1 or idx < -len(self.children):
            raise IndexError

    def set_child(self, idx: int, value: T) -> None:
        self.__child_set_sanity(idx)
        self._set_child(idx, value)

    def _set_child(self, idx: int, value: T) -> None:
        raise NotImplementedError

    @left.setter
    def left(self, value: T) -> None:
        self.set_child(0, value)

    @property
    def right(self) -> T | None:
        try:
            return self.children[-1]
        except IndexError:
            return None

    @right.setter
    def right(self, value: T) -> None:
        self.set_child(-1, value)


class Node[T: Node](NodeMixin[T]):
    def _set_child(self, idx: int, value: T) -> None:
        raise NotImplementedError

    @property
    def children(self) -> Sequence[T]:
        raise NotImplementedError


class Expression(Node[Node[t.Any]]):
    __slots__ = ('comment', 'roll')

    def __init__(self, roll: Node[Node[t.Any]], comment: str | lark.Token | None = None) -> None:
        self.roll: Node[Node[t.Any]] = roll
        self.comment: str | None = str(comment) if comment is not None else None

    @property
    def children(self) -> Sequence[Node[Node[t.Any]]]:
        return [self.roll]

    def _set_child(self, idx: int, value: Node[Node[t.Any]]) -> None:
        self.roll = value

    def __str__(self) -> str:
        if self.comment:
            return f'{self.roll} {self.comment}'
        return str(self.roll)


class Annotated(Node[Node[t.Any]]):
    __slots__ = ('annotations', 'value')

    def __init__(self, value: Node[Node[t.Any]], *annotations: str | lark.Token) -> None:
        self.value: Node[Node[t.Any]] = value
        self.annotations: list[str] = [str(a).strip() for a in annotations]

    @property
    def children(self) -> Sequence[Node[Node[t.Any]]]:
        return [self.value]

    def _set_child(self, idx: int, value: Node[Node[t.Any]]) -> None:
        self.value = value

    def __str__(self) -> str:
        return f'{self.value} {"".join(self.annotations)}'


class Literal(Node[t.Any]):
    __slots__ = ('value',)

    def __init__(self, value: float | lark.Token) -> None:
        if isinstance(value, lark.Token):
            if value.type == 'INTEGER':
                self.value = int(value)
            else:
                self.value = float(value)
        else:
            self.value: float | int = value

    @property
    def children(self) -> Sequence[Node[t.Any]]:
        return []

    def __str__(self) -> str:
        return str(self.value)


class Parenthetical(Node[Node[t.Any]]):
    __slots__ = ('value',)

    def __init__(self, value: Node[Node[t.Any]]) -> None:
        self.value: Node[Node[t.Any]] = value

    @property
    def children(self) -> list[Node[Node[t.Any]]]:
        return [self.value]

    def _set_child(self, idx: int, value: Node[Node[t.Any]]) -> None:
        self.value = value

    def __str__(self) -> str:
        return f'({self.value})'


class UnOp(Node[Node[t.Any]]):
    __slots__ = ('op', 'value')

    def __init__(self, op: str | lark.Token, value: Node[Node[t.Any]]) -> None:
        self.op: str = str(op)
        self.value: Node[Node[t.Any]] = value

    @property
    def children(self) -> list[Node[Node[t.Any]]]:
        return [self.value]

    def _set_child(self, idx: int, value: Node[Node[t.Any]]) -> None:
        self.value = value

    def __str__(self) -> str:
        return f'{self.op}{self.value}'


class BinOp(Node[Node[t.Any]]):
    __slots__ = ('left_', 'op', 'right_')

    def __init__(self, left: Node[Node[t.Any]], op: str | lark.Token, right: Node[Node[t.Any]]) -> None:
        self.left_: Node[Node[t.Any]] = left
        self.right_: Node[Node[t.Any]] = right
        self.op: str = str(op)

    @property
    def children(self) -> list[Node[Node[t.Any]]]:
        return [self.left_, self.right_]

    def _set_child(self, idx: int, value: Node[Node[t.Any]]) -> None:
        if self.children[idx] is self.left_:
            self.left_ = value
        else:
            self.right_ = value

    def __str__(self) -> str:
        return f'{self.left_} {self.op} {self.right_}'


class SetOp:
    __slots__ = ('op', 'sels')

    IMMEDIATE = ('mi', 'ma')

    def __init__(self, op: str | lark.Token, sels: list[SetSel]) -> None:
        self.op: str = str(op)
        self.sels: list[SetSel] = sels

    @classmethod
    def new(cls, op: str, sel: SetSel) -> SetOp:
        return cls(op, [sel])

    def add_sels(self, sels: list[SetSel]) -> None:
        self.sels.extend(sels)

    def __str__(self) -> str:
        return ''.join(f'{self.op}{sel}' for sel in self.sels)


class SetSel:
    __slots__ = ('cat', 'num')

    def __init__(self, cat: str | lark.Token | None, num: int | lark.Token) -> None:
        self.cat: str | None = str(cat) if cat is not None else None
        self.num: int = int(num)

    def __str__(self) -> str:
        if self.cat:
            return f'{self.cat}{self.num}'
        return str(self.num)


class SetExpr(Node[Node[t.Any]]):
    __slots__ = ('values',)

    def __init__(self, values: list[Node[Node[t.Any]]]) -> None:
        self.values: list[Node[Node[t.Any]]] = values

    @property
    def children(self) -> Sequence[Node[Node[t.Any]]]:
        return self.values

    def _set_child(self, idx: int, value: Node[Node[t.Any]]) -> None:
        self.values[idx] = value

    def __str__(self) -> str:
        if len(self.values) == 1:
            return f'({self.values[0]},)'
        return f'({", ".join(str(v) for v in self.values)})'

    def __copy__(self) -> SetExpr:
        return SetExpr(self.values.copy())


class DiceExpr(Node[t.Any]):
    __slots__ = ('num', 'sides')
    sides: t.Literal['%'] | int

    def __init__(self, num: int | lark.Token, sides: int | str | lark.Token) -> None:
        self.num: int = int(num)
        if sides == '%':
            self.sides = '%'
        else:
            try:
                self.sides = int(sides)
            except ValueError as e:
                msg = f'sides must be an integer or "%", not {sides!r}'
                raise ValueError(msg) from e

    @property
    def children(self) -> Sequence[Node[t.Any]]:
        return []

    def __str__(self) -> str:
        return f'{self.num}d{self.sides}'


class Set(Node[SetExpr | DiceExpr]):
    __slots__ = ('ops', 'value')

    def __init__(self, s: SetExpr | DiceExpr, *ops: SetOp) -> None:
        self.value: SetExpr | DiceExpr = s
        self.ops: list[SetOp] = list(ops)
        self._simplify()

    @property
    def children(self) -> Sequence[SetExpr | DiceExpr]:
        return [self.value]

    def _set_child(self, idx: int, value: SetExpr | DiceExpr) -> None:
        self.value = value

    def _simplify(self) -> None:
        new: list[SetOp] = []
        for op in self.ops:
            if op.op in SetOp.IMMEDIATE or not new:
                new.append(op)
            else:
                last = new[-1]
                if op.op == last.op:
                    last.add_sels(op.sels)
                else:
                    new.append(op)
        self.ops = new

    def __str__(self) -> str:
        return f'{self.value}{"".join(str(op) for op in self.ops)}'


class Dice(Set):
    __slots__ = ()

    def __init__(self, dice: DiceExpr, *ops: SetOp) -> None:
        super().__init__(dice, *ops)


class RollTransformer(lark.Transformer[lark.Token, Expression]):
    _comma = object()

    @staticmethod
    def expr(n: list[t.Any]) -> Expression:
        return Expression(*n)

    @staticmethod
    def commented_expr(n: list[t.Any]) -> Expression:
        return Expression(*n)

    @staticmethod
    def comparison(n: list[t.Any]) -> BinOp:
        return BinOp(*n)

    @staticmethod
    def a_num(n: list[t.Any]) -> BinOp:
        return BinOp(*n)

    @staticmethod
    def m_num(n: list[t.Any]) -> BinOp:
        return BinOp(*n)

    @staticmethod
    def u_num(n: list[t.Any]) -> UnOp:
        return UnOp(*n)

    @staticmethod
    def numexpr(n: list[t.Any]) -> Annotated:
        return Annotated(*n)

    @staticmethod
    def literal(n: list[t.Any]) -> Literal:
        return Literal(*n)

    @staticmethod
    def set(n: list[t.Any]) -> Set:
        return Set(*n)

    @staticmethod
    def set_op(n: list[t.Any]) -> SetOp:
        return SetOp.new(*n)

    def setexpr(self, n: list[t.Any]) -> Parenthetical | SetExpr:
        if len(n) == 1 and n[-1] is not self._comma:
            return Parenthetical(n[0])
        if n and n[-1] is self._comma:
            n = n[:-1]
        return SetExpr(n)

    @staticmethod
    def dice(n: list[t.Any]) -> Dice:
        return Dice(*n)

    @staticmethod
    def dice_op(n: list[t.Any]) -> SetOp:
        return SetOp.new(*n)

    @staticmethod
    def diceexpr(n: list[t.Any]) -> DiceExpr:
        if len(n) == 1:
            return DiceExpr(1, *n)
        return DiceExpr(*n)

    @staticmethod
    def selector(n: list[t.Any]) -> SetSel:
        num = n.pop()
        cat = n.pop() if n else None
        return SetSel(cat, num)

    def comma(self, _: list[t.Any]) -> object:
        return self._comma


@cache
def grammar() -> str:
    return pathlib.Path(__file__).parent.joinpath('dice.lark').read_text('utf-8')


class Parser:
    def __init__(self) -> None:
        self._parser = lark.Lark(
            grammar=grammar(),
            start=['expr', 'commented_expr'],
            parser='lalr',
            maybe_placeholders=True,
        )
        self._transformer = RollTransformer()

    def parse(self, expr: str, start: t.Literal['expr', 'commented_expr']) -> Expression:
        tree = self._parser.parse(expr, start)
        return self._transformer.transform(tree)


parser: Parser = Parser()
