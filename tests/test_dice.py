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

import pytest

from dice import Crit, Result, ast_ as ast, roll
from dice.errors import DiceValueError, RollLimitReached
from dice.expr import BinOp, Expression, Literal

STANDARD_EXPRS = (
    '1d20',
    '1d%',
    '1+1',
    '4d6kh3',
    '(1)',
    '(1,)',
    '((1d6))',
    '4*(3d8kh2+9[fire]+(9d2e2+3[cold])/2)',
    '(1d4, 2+2, 3d6kl1)kh1',
    '((10d6kh5)kl2)kh1',
)


def r(e: str) -> int:
    return roll(e).total


def test_rolls_dont_error() -> None:
    for expr in STANDARD_EXPRS:
        assert roll(expr)


def test_roll_types() -> None:
    for expr in STANDARD_EXPRS:
        result = roll(expr)
        assert isinstance(result, Result)
        assert isinstance(result.result, str)
        assert isinstance(result.total, (int, float))
        assert isinstance(result.ast, ast.Node)
        assert isinstance(result.expr, Expression)


def test_sane_totals() -> None:
    for _ in range(1000):
        assert 1 <= r('1d20') <= 20
        assert 0 <= r('1d%') <= 100
        assert 0 <= r('1d%') % 10 <= 9
        assert 3 <= r('4d6kh3') <= 18
        assert 1 <= r('((1d6))') <= 6
        assert 4 <= r('(1d4, 2+2, 3d6kl1)kh1') <= 6
        assert 1 <= r('((10d6kh5)kl2)kh1') <= 6


def test_precedence() -> None:
    assert r('1 + 3 * 6') == r('1 + (3 * 6)') == 19
    assert r('(1 + 3) * 6') == 24
    assert r('1 + 2 + 3') == r('(1 + 2) + 3') == r('1 + (2 + 3)') == 6
    assert r('1 + 2 == 2') == 0
    assert r('1 + (2 == 2)') == 2


def test_invalid_rolls() -> None:
    with pytest.raises(RollLimitReached):
        r('1001d6')
    with pytest.raises(DiceValueError):
        r('6d0')
    with pytest.raises(DiceValueError):
        r('10d6mil1')


def test_chaining() -> None:
    assert 0 <= r('10d6k1k2k3') <= 30
    assert 0 <= r('10d6k1ph1') <= 9
    assert r('(1, 2, 3)k1k2') == 3


def test_crit() -> None:
    result = roll('1d20')
    while result.total != 20:
        result = roll('1d20')
    assert result.crit == Crit.success
    while result.total != 1:
        result = roll('1d20')
    assert result.crit == Crit.failure
    while result.total in {1, 20}:
        result = roll('1d20')
    assert result.crit == Crit.none


def test_literal() -> None:
    assert r('1') == 1
    assert r('10000') == 10000
    assert r('1.5') == 1
    assert r('0.5') == r('.5') == 0


def test_dice() -> None:
    for _ in range(1000):
        assert r('0d6') == 0
        assert 1 <= r('d6') <= 6
        assert 1 <= r('1d6') <= 6
        assert 2 <= r('2d6') <= 12
        assert r('0d%') == 0
        assert 0 <= r('d%') <= 100
        assert 0 <= r('1d%') <= 100
        assert 0 <= r('2d%') <= 200


def test_set() -> None:
    assert r('(1)') == 1
    assert r('(1,)') == 1
    assert r('(1, 1)') == 2


def test_unop() -> None:
    assert r('1') == r('+1') == 1
    assert r('-1') == -1
    assert r('--1') == 1
    assert r('-+-++---+1') == -1


def test_binop() -> None:
    assert r('2 + 2') == 4
    assert r('2 - 2') == 0
    assert r('2 * 5') == 10
    assert r('15 / 2') == 7
    assert r('15 // 2') == 7
    assert r('13 % 2') == 1


def test_binop_dice() -> None:
    for _ in range(1000):
        assert 3 <= r('2 + 1d6') <= 8
        assert 2 <= r('2 * 1d6') <= 12
        assert r('60 / 1d6') in {60, 30, 20, 15, 12, 10}
        assert r('60 // 1d6') in {60, 30, 20, 15, 12, 10}
        assert r('1d100 % 10') <= 9
        assert r('1d% % 10') <= 9


def test_div_zero() -> None:
    with pytest.raises(DiceValueError):
        r('10 / 0')
    with pytest.raises(DiceValueError):
        r('10 // 0')
    with pytest.raises(DiceValueError):
        r('10 % 0')


def test_comparison() -> None:
    assert r('1 == 1') == 1
    assert r('1 == 2') == 0
    assert r('1 > 1') == 0
    assert r('2 > 1') == 1
    assert r('1 < 1') == 0
    assert r('1 < 2') == 1
    assert r('1 >= 1') == 1
    assert r('1 >= 2') == 0
    assert r('1 <= 1') == 1
    assert r('2 <= 1') == 0
    assert r('1 != 1') == 0
    assert r('1 != 2') == 1


def test_selectors() -> None:
    assert r('(1, 2, 3, 4, 5)k3') == 3
    assert r('(1, 2, 3, 4, 5)k<3') == 3
    assert r('(1, 2, 3, 4, 5)k>3') == 9
    assert r('(1, 2, 3, 4, 5)kl2') == 3
    assert r('(1, 2, 3, 4, 5)kh2') == 9
    assert r('(1)k1') == 1
    assert r('(1)k2') == 0


def test_k() -> None:
    assert r('(1, 2, 3, 4, 5)k3') == 3
    assert r('(1, 2, 3, 4, 5)k1k2') == 3
    assert r('(1, 2, 3, 4, 5)kh1kl1') == 6


def test_p() -> None:
    assert r('(1, 2, 3, 4, 5)p3') == 12
    assert r('(1, 2, 3, 4, 5)p1p2') == 12
    assert r('(1, 2, 3, 4, 5)ph1pl1') == 9


def test_rr() -> None:
    assert r('1d20rr<20') == 20
    assert r('1d20rr>1') == 1
    with pytest.raises(RollLimitReached):
        r('1d20rr<21')
    with pytest.raises(RollLimitReached):
        r('1d1rr1')


def test_ro() -> None:
    assert r('1d1ro1') == 1
    assert 1 <= r('1d6rol1') <= 6


def test_ra() -> None:
    assert r('1d1ra1') == 2
    assert 2 <= r('1d6ral1') <= 12


def test_e() -> None:
    assert r('1d2e2') % 2 == 1
    with pytest.raises(RollLimitReached):
        r('1d20e<21')
    with pytest.raises(RollLimitReached):
        r('1d1e1')


def test_mi() -> None:
    assert r('10d6mi6') == 60
    assert r('10d6mi10') == 100
    assert 20 <= r('10d6mi2') <= 60


def test_ma() -> None:
    assert r('10d6ma1') == 10
    assert r('10d6ma0') == 0
    assert 10 <= r('10d6ma5') <= 50


def test_correct_results() -> None:
    result = roll('1 + 2 + 3')
    assert result.total == 6
    assert result.result == '1 + 2 + 3 = `6`'
    result.expr.roll = BinOp(result.expr.roll, '+', Literal(4))
    assert result.total == 10
    assert result.result == '1 + 2 + 3 + 4 = `10`'
