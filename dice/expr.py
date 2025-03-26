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

import operator
import typing as t
from collections.abc import Callable, Mapping, Sequence

from . import ast_ as ast, rand
from .context import Context
from .errors import DiceValueError

__all__ = ('BinOp', 'Dice', 'Die', 'Expression', 'Literal', 'Number', 'Parenthetical', 'Set', 'SetOp', 'SetSel', 'UnOp')


class Number[T: Number](ast.NodeMixin[T]):
    __slots__ = ('annotation', 'kept')

    def __init__(self, *, kept: bool = True, annotation: str | None = None) -> None:
        self.kept: bool = kept
        self.annotation: str | None = annotation

    @property
    def number(self) -> float:
        return sum(n.number for n in self.kept_set)

    @property
    def total(self) -> float:
        return self.number if self.kept else 0

    @property
    def set(self) -> Sequence[T]:
        raise NotImplementedError

    @property
    def kept_set(self) -> Sequence[T]:
        return [n for n in self.set if n.kept]

    def drop(self) -> None:
        self.kept = False

    def __int__(self) -> int:
        return int(self.total)

    def __float__(self) -> float:
        return float(self.total)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} total={self.total} kept={self.kept}>'

    @property
    def children(self) -> Sequence[T]:
        raise NotImplementedError


class Expression(Number[Number[t.Any]]):
    __slots__ = ('comment', 'roll')

    def __init__(
        self, roll: Number[Number[t.Any]], comment: str | None, *, kept: bool = True, annotation: str | None = None
    ) -> None:
        super().__init__(kept=kept, annotation=annotation)
        self.roll: Number[Number[t.Any]] = roll
        self.comment: str | None = comment

    @property
    def number(self) -> float:
        return self.roll.number

    @property
    def set(self) -> Sequence[Number[Number[t.Any]]]:
        return self.roll.set

    @property
    def children(self) -> Sequence[Number[Number[t.Any]]]:
        return [self.roll]

    def _set_child(self, idx: int, value: Number[Number[t.Any]]) -> None:
        self.roll = value

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} roll={self.roll} comment={self.comment}>'


class Literal(Number[Number[t.Any]]):
    __slots__ = ('exploded', 'values')

    def __init__(self, value: float, *, kept: bool = True, annotation: str | None = None) -> None:
        super().__init__(kept=kept, annotation=annotation)
        self.values: list[float] = [value]
        self.exploded: bool = False

    @property
    def number(self) -> float:
        return self.values[-1]

    @property
    def set(self) -> Sequence[Number[Number[t.Any]]]:
        return [self]

    @property
    def children(self) -> Sequence[Number[Number[t.Any]]]:
        return []

    def explode(self) -> None:
        self.exploded = True

    def update(self, value: float) -> None:
        self.values.append(value)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.number}>'


class UnOp(Number[Number[t.Any]]):
    __slots__ = ('op', 'value')

    OPS: Mapping[str, Callable[[float], float]] = {'-': operator.neg, '+': operator.pos}

    def __init__(
        self, op: str, value: Number[Number[t.Any]], *, kept: bool = True, annotation: str | None = None
    ) -> None:
        super().__init__(kept=kept, annotation=annotation)
        self.op: str = op
        self.value: Number[Number[t.Any]] = value

    @property
    def number(self) -> float:
        return self.OPS[self.op](self.value.total)

    @property
    def set(self) -> Sequence[Number[Number[t.Any]]]:
        return [self]

    @property
    def children(self) -> Sequence[Number[Number[t.Any]]]:
        return [self.value]

    def _set_child(self, idx: int, value: Number[Number[t.Any]]) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} op={self.op} value={self.value}>'


class BinOp(Number[Number[t.Any]]):
    __slots__ = ('left_', 'op', 'right_')

    OPS: Mapping[str, Callable[[float, float], float]] = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '//': operator.floordiv,
        '%': operator.mod,
        '<': operator.lt,
        '>': operator.gt,
        '==': operator.eq,
        '>=': operator.ge,
        '<=': operator.le,
        '!=': operator.ne,
    }

    def __init__(
        self,
        left: Number[Number[t.Any]],
        op: str,
        right: Number[Number[t.Any]],
        *,
        kept: bool = True,
        annotation: str | None = None,
    ) -> None:
        super().__init__(kept=kept, annotation=annotation)
        self.left_: Number[Number[t.Any]] = left
        self.right_: Number[Number[t.Any]] = right
        self.op: str = op
        # eagerly evaluate to catch division by zero errors
        _ = self.number

    @property
    def number(self) -> float:
        try:
            v = self.OPS[self.op](self.left_.total, self.right_.total)
            if v is False:
                v = 0
            elif v is True:
                v = 1
        except ZeroDivisionError as e:
            msg = 'Cannot divide by zero.'
            raise DiceValueError(msg) from e
        else:
            return v

    @property
    def set(self) -> Sequence[Number[Number[t.Any]]]:
        return [self]

    @property
    def children(self) -> Sequence[Number[Number[t.Any]]]:
        return [self.left_, self.right_]

    def _set_child(self, idx: int, value: Number[Number[t.Any]]) -> None:
        if self.children[idx] is self.left_:
            self.left_ = value
        else:
            self.right_ = value

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} left={self.left_} op={self.op} right={self.right_}>'


class Parenthetical(Number[Number[t.Any]]):
    __slots__ = ('ops', 'value')

    def __init__(
        self,
        value: Number[Number[t.Any]],
        ops: list[SetOp] | None = None,
        *,
        kept: bool = True,
        annotation: str | None = None,
    ) -> None:
        super().__init__(kept=kept, annotation=annotation)
        self.value: Number[Number[t.Any]] = value
        self.ops: list[SetOp] = ops or []

    @property
    def total(self) -> float:
        return self.value.total if self.kept else 0

    @property
    def set(self) -> Sequence[Number[Number[t.Any]]]:
        return self.value.set

    @property
    def children(self) -> Sequence[Number[Number[t.Any]]]:
        return [self.value]

    def _set_child(self, idx: int, value: Number[Number[t.Any]]) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} value={self.value} ops={self.ops}>'


class Set[T: Number[t.Any]](Number[T]):
    __slots__ = ('ops', 'values')

    def __init__(
        self, values: list[T], ops: list[SetOp] | None = None, *, kept: bool = True, annotation: str | None = None
    ) -> None:
        super().__init__(kept=kept, annotation=annotation)
        self.values: list[T] = values
        self.ops: list[SetOp] = ops or []

    @property
    def set(self) -> Sequence[T]:
        return self.values

    @property
    def children(self) -> Sequence[T]:
        return self.values

    def _set_child(self, idx: int, value: T) -> None:
        self.values[idx] = value

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} values={self.values} ops={self.ops}>'

    def __copy__(self) -> Set[T]:
        return Set(values=self.values.copy(), ops=self.ops.copy(), kept=self.kept, annotation=self.annotation)


class Die(Number[Literal]):
    __slots__ = ('_context', '_rng', 'sides', 'values')

    MAX_SIDES = 9_223_372_036_854_775_807  # i64::MAX

    def __init__(
        self,
        sides: int | t.Literal['%'],
        values: list[Literal],
        context: Context | None = None,
        rng: rand.Random = rand.impl,
    ) -> None:
        super().__init__()
        self.sides: int | t.Literal['%'] = sides
        self.values: list[Literal] = values
        self._context: Context | None = context
        self._rng = rng

    @classmethod
    def new(cls, sides: int | t.Literal['%'], context: Context | None = None, rng: rand.Random = rand.impl) -> Die:
        self = cls(sides, [], context=context, rng=rng)
        self._add_roll()
        return self

    @property
    def number(self) -> float:
        return self.values[-1].total

    @property
    def set(self) -> Sequence[Literal]:
        return [self.values[-1]]

    @property
    def children(self) -> Sequence[Literal]:
        return []

    def _add_roll(self) -> None:
        if self.sides != '%':
            if self.sides < 1:
                msg = "Can't roll a 0 sided die."
                raise DiceValueError(msg)
            if self.sides > self.MAX_SIDES + 1:
                msg = "Can't roll dice with more than 9 quintillion sides."
                raise DiceValueError(msg)
        if self._context:
            self._context.count_roll()
        if self.sides == '%':
            # percent dice emulation 00 -> 90 and 0 -> 9
            # 00 0 is 100
            n = Literal((self._rng.randrange(10) * 10 + self._rng.randrange(10)) or 100)
        else:
            n = Literal(self._rng.randrange(self.sides) + 1)
        self.values.append(n)

    def reroll(self) -> None:
        if self.values:
            self.values[-1].drop()
        self._add_roll()

    def explode(self) -> None:
        if self.values:
            self.values[-1].explode()

    def force_value(self, v: float) -> None:
        if self.values:
            self.values[-1].update(v)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} sides={self.sides} values={self.values}>'


class Dice(Set[Die]):
    __slots__ = ('_context', '_rng', 'num', 'sides')

    def __init__(
        self,
        num: int,
        sides: int | t.Literal['%'],
        values: list[Die],
        ops: list[SetOp] | None = None,
        context: Context | None = None,
        rng: rand.Random = rand.impl,
        *,
        kept: bool = True,
        annotation: str | None = None,
    ) -> None:
        super().__init__(values, ops, kept=kept, annotation=annotation)
        self.num: int = num
        self.sides: int | t.Literal['%'] = sides
        self._context: Context | None = context
        self._rng = rng

    @classmethod
    def new(
        cls, num: int, sides: int | t.Literal['%'], context: Context | None = None, rng: rand.Random = rand.impl
    ) -> Dice:
        return cls(num, sides, [Die.new(sides, context=context) for _ in range(num)], context=context, rng=rng)

    def roll_another(self) -> None:
        self.values.append(Die.new(self.sides, context=self._context, rng=self._rng))

    @property
    def children(self) -> Sequence[Die]:
        return []

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} num={self.num} sides={self.sides} values={self.values} ops={self.ops}>'

    def __copy__(self) -> Dice:
        return Dice(
            num=self.num,
            sides=self.sides,
            values=self.values.copy(),
            ops=self.ops.copy(),
            context=self._context,
            rng=self._rng,
            kept=self.kept,
            annotation=self.annotation,
        )


class SetOp:
    __slots__ = ('op', 'sels')

    def __init__(self, op: str, sels: list[SetSel]) -> None:
        self.op: str = op
        self.sels: list[SetSel] = sels

    @classmethod
    def from_ast(cls, node: ast.SetOp) -> SetOp:
        return cls(node.op, [SetSel.from_ast(sel) for sel in node.sels])

    def select[T: Number[t.Any]](self, target: Number[T], max_targets: int | None = None) -> set[T]:
        out: set[T] = set()
        for sel in self.sels:
            batch = None
            if max_targets is not None:
                batch = max_targets - len(out)
                if batch == 0:
                    break
            out.update(sel.select(target, max_targets=batch))
        return out

    @property
    def ops(self) -> dict[str, Callable[[Number[t.Any]], None]]:
        return {
            'k': self.keep,
            'p': self.drop,
        }

    @property
    def dice_ops(self) -> dict[str, Callable[[Dice], None]]:
        return {
            'k': self.keep,
            'p': self.drop,
            'rr': self.reroll,
            'ro': self.reroll_once,
            'ra': self.explode_once,
            'e': self.explode,
            'mi': self.min,
            'ma': self.max,
        }

    def operate(self, target: Number[Number[t.Any]]) -> None:
        if type(target) is Dice:
            self.dice_ops[self.op](target)
        else:
            self.ops[self.op](target)

    def keep(self, target: Number[t.Any]) -> None:
        to_keep = self.select(target)
        for v in target.kept_set:
            if v not in to_keep:
                v.drop()

    def drop(self, target: Number[t.Any]) -> None:
        for v in self.select(target):
            v.drop()

    def reroll(self, target: Dice) -> None:
        to_reroll = self.select(target)
        while to_reroll:
            for v in to_reroll:
                v.reroll()
            to_reroll = self.select(target)

    def reroll_once(self, target: Dice) -> None:
        for v in self.select(target):
            v.reroll()

    def explode(self, target: Dice) -> None:
        to_explode = self.select(target)
        exploded: set[Die] = set()
        while to_explode:
            for v in to_explode:
                v.explode()
                target.roll_another()
            exploded.update(to_explode)
            to_explode = self.select(target) - exploded

    def explode_once(self, target: Dice) -> None:
        for v in self.select(target):
            v.explode()
            target.roll_another()

    def min(self, target: Dice) -> None:
        selector = self.sels[-1]
        if selector.cat is not None:
            msg = f'{selector} is not a valid selector for min'
            raise DiceValueError(msg)
        min_ = selector.num
        for v in target.kept_set:
            if v.number < min_:
                v.force_value(min_)

    def max(self, target: Dice) -> None:
        selector = self.sels[-1]
        if selector.cat is not None:
            msg = f'{selector} is not a valid selector for max'
            raise DiceValueError(msg)
        max_ = selector.num
        for v in target.kept_set:
            if v.number > max_:
                v.force_value(max_)

    def __str__(self) -> str:
        return ''.join(f'{self.op}{sel}' for sel in self.sels)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} op={self.op} sels={self.sels}>'


class SetSel:
    __slots__ = ('cat', 'num')

    def __init__(self, cat: str | None, num: int) -> None:
        self.cat: str | None = cat
        self.num: int = num

    @classmethod
    def from_ast(cls, node: ast.SetSel) -> SetSel:
        return cls(node.cat, node.num)

    def select[T: Number[t.Any]](self, target: Number[T], max_targets: int | None = None) -> set[T]:
        sels = {'l': self.lown, 'h': self.highn, '<': self.lt, '>': self.gt, None: self.lit}
        selected = sels[self.cat](target)
        if max_targets is not None:
            selected = selected[:max_targets]
        return set(selected)

    def lown[T: Number[t.Any]](self, target: Number[T]) -> list[T]:
        return sorted(target.kept_set, key=operator.attrgetter('total'))[: self.num]

    def highn[T: Number[t.Any]](self, target: Number[T]) -> list[T]:
        return sorted(target.kept_set, key=operator.attrgetter('total'), reverse=True)[: self.num]

    def lt[T: Number[t.Any]](self, target: Number[T]) -> list[T]:
        return [n for n in target.kept_set if n.total < self.num]

    def gt[T: Number[t.Any]](self, target: Number[T]) -> list[T]:
        return [n for n in target.kept_set if n.total > self.num]

    def lit[T: Number[t.Any]](self, target: Number[T]) -> list[T]:
        return [n for n in target.kept_set if n.total == self.num]

    def __str__(self) -> str:
        if self.cat:
            return f'{self.cat}{self.num}'
        return str(self.num)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} cat={self.cat} num={self.num}>'
