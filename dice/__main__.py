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

import argparse
import cmd
import importlib.metadata
import platform
import sys
import typing as t

import lark

import dice

try:
    import numpy as np
except ImportError:
    np = None


def show_version() -> None:
    entries: list[str] = []
    vi = sys.version_info
    entries.append(f'- Python v{vi.major}.{vi.minor}.{vi.micro}-{vi.releaselevel}')
    vi = dice.version_info
    entries.append(f'- lmaotrigine-dice v{vi.major}.{vi.minor}.{vi.micro}-{vi.releaselevel}')
    if vi.releaselevel != 'final':
        version = importlib.metadata.version('lmaotrigine-dice')
        if version:
            entries.append(f'    - lmaotrigine-dice metadata: v{version}')
    entries.append(f'- lark v{lark.__version__}')
    if np is not None:
        entries.append(f'- numpy v{np.__version__}')
    uname = platform.uname()
    entries.append(f'- system info: {uname.system} {uname.release} {uname.version}')
    print('\n'.join(entries))  # noqa: T201


def core(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.version:
        show_version()
    else:
        parser.print_help()


def add_roll_one_args(subparser: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:  # pyright: ignore[reportPrivateUsage]
    parser = subparser.add_parser('roll', help='roll a single dice expression')
    parser.set_defaults(func=roll_one)
    parser.add_argument('-c', '--allow-comments', action='store_true', help='allow comments in the expression')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-a', '--adv', '--advantage', action='store_const', const=dice.Advantage.adv, help='roll with advantage'
    )
    group.add_argument(
        '-d', '--dis', '--disadvantage', action='store_const', const=dice.Advantage.dis, help='roll with disadvantage'
    )
    parser.add_argument('expr', nargs='?', help='the dice expression', default='d20')


class ANSIFormatter(dice.MarkdownFormatter):
    def _format(self, node: dice.Number[t.Any]) -> str:
        if not node.kept and not self._context.in_dropped:
            self._context.in_dropped = True
            inner = super()._format(node)
            self._context.in_dropped = False
            return f'\x1b[31m{inner}\x1b[0m'
        return super()._format(node)

    def _format_expression(self, node: dice.Expression) -> str:
        return f'{self._format(node.roll)} = \x1b[1m{int(node.total)}\x1b[0m'

    def _format_die(self, node: dice.Die) -> str:
        rolls: list[str] = []
        for v in node.values:
            inner = self._format(v)
            if v.number in {1, node.sides}:
                inner = f'\x1b[4m{inner}\x1b[0m'
            rolls.append(inner)
        return ', '.join(rolls)


class RollRepl(cmd.Cmd):
    intro: str = 'Welcome to the dice REPL. Enter any dice expression to roll it.'
    prompt = 'dice> '

    def default(self, line: str) -> None:  # noqa: PLR6301
        if line == 'EOF':
            return
        try:
            res = dice.roll(line, allow_comments=True, formatter=ANSIFormatter())
        except dice.DiceError as e:
            print(e)  # noqa: T201
        else:
            print(res)  # noqa: T201

    @staticmethod
    def do_quit(_: str) -> bool:
        """Exit the REPL."""
        return True

    do_exit = do_quit


def roll_repl(_: argparse.ArgumentParser, _args: argparse.Namespace) -> None:
    try:
        RollRepl().cmdloop()
    except KeyboardInterrupt:
        sys.exit(1)


def roll_one(_: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    formatter = ANSIFormatter() if sys.stdout.isatty() else dice.MarkdownFormatter()
    advantage = args.adv or args.dis or dice.Advantage.none
    res = dice.roll(args.expr, allow_comments=args.allow_comments, advantage=advantage, formatter=formatter)
    print(res)  # noqa: T201


def parse_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    parser = argparse.ArgumentParser(prog='dice', description='A dice engine.')
    parser.add_argument('-v', '--version', action='store_true', help='shows the library version')
    parser.set_defaults(func=core)
    subparser = parser.add_subparsers(dest='subcommand', title='subcommand', required=False)
    subparser.add_parser('repl', help='starts a REPL', parents=[]).set_defaults(func=roll_repl)
    add_roll_one_args(subparser)
    return parser, parser.parse_args()


def main() -> None:
    parser, args = parse_args()
    args.func(parser, args)


if __name__ == '__main__':
    main()
