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

import typing as t

from . import ast_ as ast, utils
from .context import Context
from .dice import Result, Roller
from .enums import Advantage, Crit
from .errors import DiceError, DiceSyntaxError, DiceValueError, RollLimitReached
from .expr import BinOp, Dice, Die, Expression, Literal, Number, Parenthetical, Set, SetOp, SetSel, UnOp
from .formatters import Formatter, MarkdownFormatter, SimpleFormatter

__version__ = '0.0.1a'

__all__ = (
    'Advantage',
    'BinOp',
    'Context',
    'Crit',
    'Dice',
    'DiceError',
    'DiceSyntaxError',
    'DiceValueError',
    'Die',
    'Expression',
    'Formatter',
    'Literal',
    'MarkdownFormatter',
    'Number',
    'Parenthetical',
    'Result',
    'RollLimitReached',
    'Roller',
    'Set',
    'SetOp',
    'SetSel',
    'SimpleFormatter',
    'UnOp',
    'ast',
    'utils',
)


class _VersionInfo(t.NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: t.Literal['alpha', 'beta', 'candidate', 'final']
    serial: int


class Roll(t.Protocol):
    def __call__(
        self,
        expr: str | ast.Expression,
        *,
        formatter: Formatter | None = ...,
        allow_comments: bool = ...,
        advantage: Advantage = ...,
    ) -> Result: ...


class Parse(t.Protocol):
    def __call__(self, expr: str, *, allow_comments: bool = ...) -> ast.Expression: ...


version_info: _VersionInfo = _VersionInfo(major=0, minor=0, micro=1, releaselevel='alpha', serial=0)

__roller = Roller()
roll: Roll = __roller.roll
parse: Parse = __roller.parse

del _VersionInfo, t, Parse, Roll
