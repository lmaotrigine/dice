#!/usr/bin/env python3

import cmd
import pathlib
import sys

from lark import Lark
from lark.tree import pydot__tree_to_png  # pyright: ignore[reportUnknownVariableType]  # untyped upstream

GRAMMAR = pathlib.Path(__file__).parent.parent / 'dice' / 'dice.lark'

grammar = GRAMMAR.read_text('utf-8')
parser = Lark(grammar, start='expr', parser='lalr')


class Parser(cmd.Cmd):
    prompt = 'dice> '

    @staticmethod
    def do_quit(line: str) -> bool:
        return True

    do_exit = do_quit

    def default(self, line: str) -> None:  # noqa: PLR6301
        if line == 'EOF':
            return
        result = parser.parse(line)
        print(result.pretty())  # noqa: T201
        print(result)  # noqa: T201
        pydot__tree_to_png(result, 'tree.png')


if __name__ == '__main__':
    try:
        Parser().cmdloop()
    except KeyboardInterrupt:
        sys.exit(1)
