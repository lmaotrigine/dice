#!/usr/bin/env python3

import cmd
import pathlib
import sys

from lark import Lark

from dice.ast_ import RollTransformer


class _Parser(cmd.Cmd):
    prompt = 'dice> '

    @staticmethod
    def do_quit(line: str) -> bool:
        return True

    do_exit = do_quit

    def __init__(self) -> None:
        super().__init__()
        g = pathlib.Path(__file__).parent.parent.joinpath('dice').joinpath('dice.lark').read_text('utf-8')
        self._parser = Lark(grammar=g, start=['expr', 'commented_expr'], parser='lalr', maybe_placeholders=True)

    def default(self, line: str) -> None:
        if line == 'EOF':
            return
        result = self._parser.parse(line, start='expr')
        print(result.pretty())  # noqa: T201
        print(result)  # noqa: T201
        expr = RollTransformer().transform(result)
        print(expr)  # noqa: T201


if __name__ == '__main__':
    try:
        _Parser().cmdloop()
    except KeyboardInterrupt:
        sys.exit(1)
