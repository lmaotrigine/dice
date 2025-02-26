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

import string

from hypothesis import strategies as st


@st.composite
def expr(draw: st.DrawFn) -> str:
    return draw(num())


@st.composite
def commented_expr(draw: st.DrawFn) -> str:
    a = draw(num())
    b = draw(st.just('') | term_comment)
    return a + b


@st.composite
def num(draw: st.DrawFn) -> str:
    return draw(comparison())


@st.composite
def comparison(draw: st.DrawFn) -> str:
    elems = draw(st.lists(a_num(), min_size=1))
    if len(elems) > 1:
        op = draw(term_comp_op)
        return op.join(elems)
    return elems[0]


@st.composite
def a_num(draw: st.DrawFn) -> str:
    elems = draw(st.lists(m_num(), min_size=1))
    if len(elems) > 1:
        op = draw(term_add_op)
        return op.join(elems)
    return elems[0]


@st.composite
def m_num(draw: st.DrawFn) -> str:
    elems = draw(st.lists(u_num(), min_size=1))
    if len(elems) > 1:
        op = draw(term_mul_op)
        return op.join(elems)
    return elems[0]


@st.composite
def u_num(draw: st.DrawFn) -> str:
    @st.composite
    def rec(draw_i: st.DrawFn, b: st.SearchStrategy) -> str:
        a = draw_i(term_u_op)
        return a + draw_i(b)

    return draw(st.recursive(numexpr(), rec))


@st.composite
def numexpr(draw: st.DrawFn) -> str:
    a = draw(dice() | rule_set() | literal())
    b = draw(st.lists(term_annotation).map(''.join))
    return a + b


@st.composite
def literal(draw: st.DrawFn) -> str:
    return draw(term_integer | term_decimal)


@st.composite
def rule_set(draw: st.DrawFn) -> str:
    a = draw(setexpr())
    b = draw(st.lists(set_op()).map(''.join))
    return a + b


@st.composite
def set_op(draw: st.DrawFn) -> str:
    a = draw(term_set_op)
    b = draw(selector())
    return a + b


@st.composite
def setexpr(draw: st.DrawFn) -> str:
    elems = draw(st.lists(num(), min_size=1).map(', '.join))
    trailing_comma = draw(st.just('') | term_comma)
    return draw(st.just('()') | st.just('(' + elems + trailing_comma + ')'))


term_comma = st.just(',')


@st.composite
def dice(draw: st.DrawFn, *, only_valid: bool = True) -> str:
    a = draw(diceexpr(only_valid=only_valid))
    b = draw(st.lists(dice_op()).map(''.join))
    return a + b


@st.composite
def dice_op(draw: st.DrawFn) -> str:
    a = draw(term_dice_op | term_set_op)
    b = draw(selector())
    return a + b


@st.composite
def diceexpr(draw: st.DrawFn, *, only_valid: bool = True) -> str:
    if only_valid:
        a = draw(st.just('') | st.integers(min_value=1, max_value=100).map(str))
        b = draw(st.integers(min_value=1).map(str) | st.just('%'))
    else:
        a = draw(st.just('') | term_integer)
        b = draw(term_dice_value)
    return a + 'd' + b


@st.composite
def selector(draw: st.DrawFn) -> str:
    a = draw(st.just('') | term_seltype)
    b = draw(term_integer)
    return a + b


@st.composite
def annotation(draw: st.DrawFn) -> str:
    inner = draw(st.text(alphabet=st.characters(blacklist_characters='[]\n', blacklist_categories=('Cs',))))
    return '[' + inner + ']'


term_annotation = annotation()

term_comment = st.text().map(lambda t: ' ' + t)
term_comp_op = st.sampled_from(('==', '>=', '<=', '!=', '<', '>'))
term_add_op = st.sampled_from('+-')
term_mul_op = st.sampled_from(('*', '/', '//', '%'))
term_u_op = st.sampled_from('+-')
term_set_op = st.sampled_from('kp')
term_dice_op = st.sampled_from(('rr', 'ro', 'ra', 'e', 'mi', 'ma'))
term_dice_value = st.integers(min_value=0).map(str) | st.just('%')
term_seltype = st.sampled_from('lh<>')
term_whitespace = st.text(alphabet='\t\f\r\n')
term_integer = st.integers(min_value=0).map(str)


@st.composite
def decimal1(draw: st.DrawFn) -> str:
    a = draw(st.text(alphabet=string.digits, min_size=1))
    b = draw(st.text(alphabet=string.digits, min_size=0))
    return a + '.' + b


@st.composite
def decimal2(draw: st.DrawFn) -> str:
    return '.' + draw(st.text(alphabet=string.digits, min_size=1))


term_decimal = decimal1() | decimal2()
