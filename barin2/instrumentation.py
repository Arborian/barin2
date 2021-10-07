import enum
from functools import singledispatch

STATE_MAGIC = "__b2_state__"
MUTATING_DICT_METHODS = """
    __setitem__ __delitem__ clear pop popitem setdefault update
""".split()
MUTATING_LIST_METHODS = """
    __setitem__ __delitem__ append clear extend insert pop remove
    reverse
    """.split()


class Status(enum.Enum):
    NEW = enum.auto()
    CLEAN = enum.auto()
    DIRTY = enum.auto()
    DELETED = enum.auto()


def init_module():
    global Idict, Ilist
    Idict = instrument_class(dict, *MUTATING_DICT_METHODS)
    Ilist = instrument_class(list, *MUTATING_LIST_METHODS)


def get_state(obj):
    return getattr(obj, STATE_MAGIC)


class InstrumentedState:
    def __init__(self):
        self.container = None
        self._status = Status.CLEAN

    def __repr__(self):
        return f"<istate status={self._status} container={self.container}>"

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        old_status = self._status
        self._status = value
        # If we move from CLEAN => DIRTY, dirty up all our containers
        if self.container and (old_status, value) == (
            Status.CLEAN,
            Status.DIRTY,
        ):
            get_state(self.container).status = value

    def on_modify(self):
        if self._status == Status.CLEAN:
            self.status = Status.DIRTY


class Instrumented:
    """Parent class of Idict and Ilist"""

    def __init__(self, *args, **kwargs):
        setattr(self, STATE_MAGIC, InstrumentedState())
        super().__init__(*args, **kwargs)


def instrument_class(cls, *dirty_methods):
    methods = {
        method_name: instrument_method(cls, method_name)
        for method_name in dirty_methods
    }
    icls = type(
        "I" + cls.__qualname__,
        (
            Instrumented,
            cls,
        ),
        methods,
    )
    return icls


def instrument_method(cls, method_name):
    super_method = getattr(cls, method_name)

    def f(self, *args, **kwargs):
        get_state(self).on_modify()
        return super_method(self, *args, **kwargs)

    return f


@singledispatch
def instrument_object(obj, status, container=None):
    return obj


@instrument_object.register
def _instrument_object_dict(obj: dict, status, container=None):
    obj = Idict(
        (key, instrument_object(value, status)) for key, value in obj.items()
    )
    instrument_object_container(obj, container)
    return obj


@instrument_object.register
def _instrument_object_list(obj: list, status, container=None):
    obj = Ilist(instrument_object(value, status) for value in obj)
    instrument_object_container(obj, container)
    return obj


@singledispatch
def instrument_object_container(obj, container):
    pass


@instrument_object_container.register
def _instrument_object_container_dict(obj: dict, container):
    get_state(obj).container = container
    for value in obj.values():
        instrument_object_container(value, obj)


@instrument_object_container.register
def _instrument_object_container_list(obj: list, container):
    get_state(obj).container = container
    for value in obj:
        instrument_object_container(value, obj)


@singledispatch
def set_object_status(obj, status):
    pass


@set_object_status.register
def _cleanse_object_dict(obj: dict, status):
    get_state(obj).status = status
    for value in obj.values():
        set_object_status(value, status)


@set_object_status.register
def _cleanse_object_list(obj: list, status):
    get_state(obj).status = status
    for value in obj:
        set_object_status(value, status)


init_module()
