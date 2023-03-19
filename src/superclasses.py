import copy
from enum import Flag
from functools import update_wrapper, partial
from typing import Callable, Any, Iterable, Optional

from makefun import wraps
from more_itertools import collapse


def flatten_until(cls: type) -> Callable:
    def clear(fn: Callable[[Any], Iterable]) -> Callable:
        @wraps(fn)
        def inner(*args, **kwargs):
            res = collapse(fn(*args, **kwargs), base_type=cls)
            return [r for r in res if r is not None]

        return inner

    return clear


RECEIVER_PARAMETER_TYPE = tuple[type, str]


def send_value_to(obj: object, attr_name: str, decorator: Callable[[type | Callable], Callable]):
    @wraps(decorator)
    def condition(*args, **kwargs):
        if kwargs.get('name') == '_value_':
            return kwargs.get('self')

    def worm(value: Any):
        setattr(obj, attr_name, value)

    decorator = partial(decorator, condition=condition, worm=worm)
    return decorator


def watch_def(fn: Callable, worm: Callable,
              condition: Callable[[list, dict], Optional[Callable[[], Any]]]):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        value_to_export = condition(fn, *args, **kwargs)
        result = fn(*args, **kwargs)
        worm(value_to_export)
        return result

    return fn


def watch_cls(cls: type, target_name: str, worm: Callable,
              condition: Callable[[list, dict], Optional[Callable[[], Any]]]):
    watched_cls = copy.deepcopy(cls)
    update_wrapper(watched_cls, cls, updated=())
    method_target = getattr(watched_cls, target_name)

    @wraps(method_target)
    def wrapper(*args, **kwargs):
        value_to_export = condition(method_target, *args, **kwargs)
        result = method_target(*args, **kwargs)
        worm(value_to_export)
        return result

    setattr(watched_cls, method_target.__name__, wrapper)
    return watched_cls


class BoolFlag(Flag):
    def __hash__(self):
        return int.__hash__(self.value)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if type(other) is type(self):
            return Flag.__eq__(self, other)
        if type(other) is bool:
            return self.value is other

    def __and__(self, other):
        if isinstance(other, bool):
            return self.value == other
        return Flag.__and__(self, other)

    def __or__(self, other):
        if isinstance(other, bool):
            return self.value == other
        return Flag.__or__(self, other)


class ColorFlag(BoolFlag):
    def direction(self) -> int:
        return 1 if self else -1

    def next(self):
        return self.WHITE if self == self.BLACK else self.BLACK
