from functools import singledispatch

STATE_MAGIC = "__b2_state__"
MUTATING_DICT_METHODS = """
    __setitem__ __delitem__ clear pop popitem setdefault update
""".split()
MUTATING_LIST_METHODS = """
    __setitem__ __delitem__ append clear extend insert pop remove
    reverse
    """.split()


def init_module():
    global Idict, Ilist
    Idict = instrument_class(dict, *MUTATING_DICT_METHODS)
    Ilist = instrument_class(list, *MUTATING_LIST_METHODS)


def get_state(obj):
    return getattr(obj, STATE_MAGIC)


class InstrumentedState:
    def __init__(self):
        self.container = None
        self._dirty = False

    def __repr__(self):
        return f"<istate dirty={self._dirty} container={self.container}>"

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, value):
        self._dirty = value
        if value and self.container:
            get_state(self.container).dirty = True


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
        get_state(self).dirty = True
        return super_method(self, *args, **kwargs)

    return f


@singledispatch
def instrument_object(obj, container=None):
    return obj


@instrument_object.register
def _instrument_object_dict(obj: dict, container=None):
    obj = Idict((key, instrument_object(value)) for key, value in obj.items())
    instrument_object_container(obj, container)
    return obj


@instrument_object.register
def _instrument_object_list(obj: list, container=None):
    obj = Ilist(instrument_object(value) for value in obj)
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
def cleanse_object(obj):
    pass


@cleanse_object.register
def _cleanse_object_dict(obj: dict):
    get_state(obj).dirty = False
    for value in obj.values():
        cleanse_object(value)


@cleanse_object.register
def _cleanse_object_list(obj: list):
    get_state(obj).dirty = False
    for value in obj:
        cleanse_object(value)


init_module()
