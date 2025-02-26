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

import pytest

from dice import Advantage, parse, roll
from dice.errors import DiceSyntaxError


def test_comments() -> None:
    r = roll('1d20 foo bar', allow_comments=True)
    assert 1 <= r.total <= 20
    assert r.comment == 'foo bar'
    with pytest.raises(DiceSyntaxError):
        roll('1d20 foo bar', allow_comments=False)


def test_conflicting_comments() -> None:
    r = roll('1d20 keep something', allow_comments=True)
    assert 1 <= r.total <= 20
    assert r.comment == 'keep something'
    with pytest.raises(DiceSyntaxError):
        roll('1d20 keep something', allow_comments=False)
    r = roll('1d20 damage', allow_comments=True)
    assert 1 <= r.total <= 20
    assert r.comment == 'damage'
    with pytest.raises(DiceSyntaxError):
        roll('1d20 damage', allow_comments=False)
    r = roll('1d20 **bold**', allow_comments=True)
    assert 1 <= r.total <= 20
    assert r.comment == '**bold**'
    with pytest.raises(DiceSyntaxError):
        roll('1d20 **bold**', allow_comments=False)
    r = roll('1d20 please save me from this parsing weirdness', allow_comments=True)
    assert 1 <= r.total <= 20
    assert r.comment == 'please save me from this parsing weirdness'
    with pytest.raises(DiceSyntaxError):
        roll('1d20 please save me from this parsing weirdness', allow_comments=False)


def test_advantage() -> None:
    r = roll('1d20', advantage=Advantage.adv)
    assert 1 <= r.total <= 20
    assert r.result.startswith('2d20kh1 ')
    r = roll('1d20', advantage=Advantage.dis)
    assert 1 <= r.total <= 20
    assert r.result.startswith('2d20kl1 ')
    r = roll('1d20', advantage=Advantage.none)
    assert 1 <= r.total <= 20
    assert r.result.startswith('1d20 ')
    r = roll('1d6', advantage=Advantage.adv)
    assert 1 <= r.total <= 6
    assert r.result.startswith('1d6 ')
    r = roll('1d6', advantage=Advantage.dis)
    assert 1 <= r.total <= 6
    assert r.result.startswith('1d6 ')


def test_ast() -> None:
    ast = parse('1d20')
    r = roll(ast)
    assert 1 <= r.total <= 20
    assert r.result.startswith('1d20 ')
