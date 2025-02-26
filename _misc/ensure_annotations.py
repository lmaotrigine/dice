#!/usr/bin/env python3

import ast
import inspect
import sys
from functools import partial
from types import FunctionType
from typing import Any

_cycle_blocked = False
rec = partial(compile, filename='<string>', mode='exec', flags=0, dont_inherit=True)


def ensure_annotations[T: type | FunctionType](f: T) -> T:
    global _cycle_blocked  # noqa: PLW0603
    if _cycle_blocked:
        return f
    new_ast = rec(ast.parse(inspect.getsource(f)), optimize=1)
    env = sys.modules[f.__module__].__dict__
    _cycle_blocked = True
    try:
        exec(new_ast, env)  # noqa: S102
    finally:
        _cycle_blocked = False
    return env[f.__name__]


def version_specific_annotation_interactions(obj: Any) -> None:
    if sys.version_info[:2] >= (3, 14):
        import annotationlib  # pyright: ignore[reportMissingImports]

        if isinstance(obj, type):
            for t in inspect.getmro(obj):
                for _, static in inspect.getmembers_static(t):
                    annotationlib.get_annotations(static)  # pyright: ignore[reportUnknownMemberType]
        else:
            annotationlib.get_annotations(obj)  # pyright: ignore[reportUnknownMemberType]


if __name__ == '__main__':
    import importlib
    import pkgutil
    import sys

    import dice

    failures: list[tuple[str, Exception]] = []
    print('checking annotations for runtime validity', flush=True)  # noqa: T201
    for mod_info in pkgutil.iter_modules(dice.__spec__.submodule_search_locations):
        mod = importlib.import_module(f'dice.{mod_info.name}')
        for name in getattr(mod, '__all__', ()):
            obj = getattr(mod, name)
            try:
                no_annotations_future_obj = ensure_annotations(obj)
                version_specific_annotation_interactions(no_annotations_future_obj)
            except TypeError:
                pass
            except (NameError, AttributeError) as e:
                failures.append((f'{mod_info.name}.{name}', e))
    if failures:
        for f, e in failures:
            exc_info = f'{e.__class__.__name__}: {e.args[0]}'
            print(f, exc_info, flush=True)  # noqa: T201
        sys.exit(1)
