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

import typing as t
from collections import Counter
from collections.abc import Iterator, MutableMapping

__all__ = ('Cache',)


class Cache[K, V](MutableMapping[K, V]):
    __marker: t.Any = object()

    def __init__(self, maxsize: int) -> None:
        self.__inner: dict[K, V] = {}
        self.__cursize = 0
        self.__maxisze = maxsize
        self.__counter: Counter[K] = Counter()

    def __getitem__(self, key: K) -> V:
        v = self.__inner[key]
        if key in self:
            self.__counter[key] -= 1
        return v

    def __setitem__(self, key: K, value: V) -> None:
        maxsize = self.__maxisze
        if key not in self.__inner:
            while self.__cursize + 1 > maxsize:
                self.popitem()
        if key not in self.__inner:
            self.__cursize += 1
        self.__inner[key] = value
        self.__counter[key] -= 1

    def __delitem__(self, key: K) -> None:
        del self.__inner[key]
        self.__cursize -= 1
        del self.__counter[key]

    def __len__(self) -> int:
        return len(self.__inner)

    def __contains__(self, key: object) -> bool:
        return key in self.__inner

    def __iter__(self) -> Iterator[K]:
        return iter(self.__inner)

    def popitem(self) -> tuple[K, V]:
        try:
            ((k, _),) = self.__counter.most_common(1)
        except ValueError:
            msg = f'{self.__class__.__name__} is empty'
            raise KeyError(msg) from None
        else:
            return k, self.pop(k)

    @t.overload
    def pop(self, key: K) -> V: ...
    @t.overload
    def pop(self, key: K, default: V) -> V: ...
    @t.overload
    def pop[D](self, key: K, default: D) -> V | D: ...

    def pop[D](self, key: K, default: D = __marker) -> V | D:
        if key in self.__inner:
            value = self[key]
            del self[key]
        elif default is self.__marker:
            raise KeyError(key)
        else:
            value = default
        return value
