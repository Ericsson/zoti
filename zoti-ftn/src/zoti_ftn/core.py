#!/usr/bin/env python3

from copy import deepcopy
from dataclasses import dataclass, replace
from enum import Enum
from typing import Dict, Optional, Union

import marshmallow as mm
import networkx as nx
from zoti_yaml import get_pos

import zoti_ftn.lang as lang
import zoti_ftn.tokens as tok
import zoti_ftn.util as util
from zoti_ftn.exceptions import FtnError, PrettyValidationError


## Unique identifier ##


class Uid:
    name: str
    module: str

    def __init__(self, qualified_name):
        self.module, self.name = qualified_name.rsplit(".", 1)

    def __hash__(self):
        return hash(self.qualified())

    def __eq__(self, other):
        return (
            isinstance(other, Uid)
            and self.name == other.name
            and self.module == other.module
        )

    def __repr__(self):
        return f"{self.module}.{self.name}"

    def qualified(self):
        return f"{self.module}_{self.name}"

    def to_json(self):
        return{"module": self.module, "name": self.name}

    # class Schema(mm.Schema):
    #     name = mm.fields.String(required=True)
    #     module = mm.fields.String(required=True)

    #     def construct(self, data, **kwargs):

    class Field(mm.fields.Field):
        def _serialize(self, uid, attr, obj, **kwargs):
            return repr(uid)

        def _deserialize(self, val, attr, data, **kwargs):
            if "module" not in val or "name" not in val:
                msg = f"Uid arguments invalid: {val}"
                raise mm.ValidationError(msg)
            uid = Uid(".")
            uid.name = val["name"]
            uid.module = val["module"]
            return uid


## Endian ##


class Endian(Enum, metaclass=util.SearchableEnum):
    LITTLE = "little"
    BIG = "big"


class EndianField(mm.fields.Field):
    # Outside the Endian namespace because Enum does not accept members.
    def _serialize(self, endian, attr, obj, **kwargs):
        if endian is None:
            return None
        return endian.value

    def _deserialize(self, spec, attr, data, **kwargs):
        if spec not in Endian:
            valids = [e.value for e in Endian]
            msg = f"Invalid value '{spec}' for endian. Valid values: {valids}"
            raise mm.ValidationError(msg)
        return Endian[spec]


## IntBase ##


@dataclass
class IntBase:
    value: int
    base: int

    def __repr__(self):
        return repr(self.value)

    class Field(mm.fields.Field):
        def _serialize(self, intb, attr, obj, **kwargs):
            if intb is None:
                return None
            STR_FUNC = {2: bin, 8: oct, 10: int, 16: hex}
            return STR_FUNC[intb.base](intb.value)

        def _deserialize(self, v, attr, data, **kwargs):
            if v is None:
                None
            if isinstance(v, tuple):
                if len(v) != 2:
                    msg = "Integer representation: tuple form needs to have length 2"
                    raise mm.ValidationError(msg)
                return IntBase(*v)
            if isinstance(v, int):
                return IntBase(value=v, base=10)
            if not isinstance(v, str):
                raise mm.ValidationError("Not a valid integer representation")
            v = v.lower()
            if v.startswith("0x"):
                base = 16
            elif v.startswith("0o"):
                base = 8
            elif v.startswith("0b"):
                base = 2
            else:
                base = 10
            try:
                return IntBase(value=int(v, base=base), base=base)
            except ValueError as e:
                raise mm.ValidationError(e)


## Range ##


@dataclass(repr=False)
class Range:
    """A range can be either a list with two elements, low and high
    limits, or a single value in which case the range is just that
    single value.  Values can be an integer, a tuple (<integer value>,
    <source base>), or a string that will be parsed into an
    integer.

    """

    low: IntBase
    high: IntBase

    def __repr__(self):
        return "({}..{})".format(self.low.value, self.high.value)

    def __contains__(self, item):
        return self.low.value <= item <= self.high.value

    def values(self):
        return (self.low.value, self.high.value)

    def size(self):
        return self.high.value - self.low.value + 1

    class Field(mm.fields.Field):
        def _serialize(self, rng, attr, obj, **kwargs):
            if rng is None:
                return None
            return [
                IntBase.Field()._serialize(rng.low, attr, obj),
                IntBase.Field()._serialize(rng.high, attr, obj),
            ]

        def _deserialize(self, spec, attr, data, **kwargs):
            deserialize = IntBase.Field()._deserialize
            if isinstance(spec, list):
                if len(spec) != 2:
                    msg = f"Invalid range representation: {spec}"
                    raise mm.ValidationError(msg)
                low = deserialize(spec[0], attr, spec, **kwargs)
                high = deserialize(spec[1], attr, spec, **kwargs)
            else:
                low = deserialize(spec, attr, spec, **kwargs)
                high = low
            if low.value > high.value:
                msg = f"Invalid range ({low}..{high}), low limit larger than high"
                raise mm.ValidationError(msg)
            return Range(low=low, high=high)


@dataclass(repr=False)
class Constant:
    constant: Union[Endian, IntBase, Range]

    def __repr__(self):
        return "#{repr(self.const)}"

    class Schema(mm.Schema):
        class Meta:
            strict = True

        range = Range.Field(data_key=tok.ATTR_RANGE, load_default=None)
        endian = EndianField(data_key=tok.ATTR_ENDIAN, load_default=None)
        bit_size = IntBase.Field(data_key=tok.ATTR_BIT_SIZE, load_default=None)

        @mm.post_load
        def construct(self, data, **kwargs):
            if len(data) != 1:
                raise mm.ValidationError("A constant can only be one type.")
            return Constant(data.values().next())


## Basic Data Types ##


@dataclass
class TypeABC:
    type: str
    readonly: bool
    _info: dict

    class Schema(mm.Schema):
        class Meta:
            strict = True

        type = mm.fields.String()
        readonly = mm.fields.Bool(load_default=False)
        _info = mm.fields.Raw(data_key=tok.ATTR_INFO, load_default=None)

        # @mm.post_load
        # def construct(self, data, **kwargs):
        #     return TypeABC(**data)

        # comment below if you want to keep None or Info fields in serialization
        @mm.post_dump
        def clear_none_and_info(self, data, **kwargs):
            return {k: v for k, v in data.items() if bool(v) and k != tok.ATTR_INFO}

    class Field(mm.fields.Field):
        def _serialize(self, ty, attr, obj, **kwargs):
            return ty.__class__.Schema().dump(ty)

        def _deserialize(self, spec, attr, data, **kwargs):
            if tok.ATTR_TYPE not in spec:
                msg = "Entry does not contain a 'type' field"
                raise PrettyValidationError(msg, spec)
            try:
                constructor = FtnDb.instance().schema(spec[tok.ATTR_TYPE])
                return constructor.load(spec)
            except mm.ValidationError as error:
                raise PrettyValidationError(error, spec)
            except Exception as err:
                raise PrettyValidationError(str(err), spec)

    def derefer(self):
        return self

    def set_readonly(self, value: bool):
        new = replace(self, readonly=value)
        self.__dict__ = deepcopy(new.__dict__)


class Void(TypeABC):
    class Schema(TypeABC.Schema):
        @mm.post_load
        def construct(self, data, **kwargs):
            return Void(**data)

    def select_types(self, of_class=None):
        return [self] if of_class == tok.TYPE_VOID else []


class Atom(TypeABC):
    class Schema(TypeABC.Schema):
        @mm.post_load
        def construct(self, data, **kwargs):
            return Atom(**data)

    def select_types(self, of_class=None):
        return [self] if of_class == tok.TYPE_ATOM else []


@dataclass
class Boolean(TypeABC):
    bit_size: Optional[IntBase]

    class Schema(TypeABC.Schema):
        bit_size = IntBase.Field(data_key=tok.ATTR_BIT_SIZE, load_default=None)

        @mm.post_load
        def construct(self, data, **kwargs):
            return Boolean(**data)

    def select_types(self, of_class=None):
        return [self] if of_class == tok.TYPE_BOOLEAN else []

    def normalize_value(self, value):
        if isinstance(value, str):
            value = value.lower()
            if value in ["true"]:
                return True
            if value in ["false"]:
                return False
            return None
        elif isinstance(value, bool):
            return value
        return None


@dataclass
class Integer(TypeABC):
    range: Range
    endian: Optional[Endian]
    bit_size: Optional[IntBase]

    class Schema(TypeABC.Schema):
        range = Range.Field(data_key=tok.ATTR_RANGE)
        endian = EndianField(data_key=tok.ATTR_ENDIAN, load_default=None)
        bit_size = IntBase.Field(data_key=tok.ATTR_BIT_SIZE, load_default=None)

        @mm.post_load
        def construct(self, data, **kwargs):
            return Integer(**data)

    def select_types(self, of_class=None):
        return [self] if of_class == tok.TYPE_INTEGER else []

    def normalize_value(self, value):
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                return None
        elif not isinstance(value, int):
            return None
        if value in self.range:
            return value
        return None


@dataclass
class Array(TypeABC):
    range: Range
    len_field: Optional[str]
    element_type: TypeABC

    class Schema(TypeABC.Schema):
        range = Range.Field(data_key=tok.ATTR_RANGE)
        len_field = mm.fields.String(
            data_key=tok.ATTR_LEN_FIELD, load_default=None)
        element_type = TypeABC.Field(data_key=tok.ATTR_ELEMENT_TYPE)

        @mm.validates("range")
        def check_range(self, value):
            if value.low.value < 0:
                msg = f"Invalid range {value}: negative limit illegal for array"
                raise mm.ValidationError(msg)

        @mm.validates("element_type")
        def check_element(self, value):
            if isinstance(value, Void):
                msg = "Invalid array element: void"
                raise mm.ValidationError(msg)

        @mm.post_load
        def construct(self, data, **kwargs):
            return Array(**data)

    def select_types(self, of_class=None):
        return (
            [self]
            if of_class == tok.TYPE_ARRAY
            else [] + self.element_type.select_types(of_class=of_class)
        )


@dataclass
class Structure(TypeABC):
    field: Dict[str, TypeABC]

    class Schema(TypeABC.Schema):
        field = mm.fields.Mapping(
            data_key=tok.ATTR_FIELDS, keys=mm.fields.String(), values=TypeABC.Field()
        )

        @mm.validates("field")
        def check_fields(self, fields):
            for field in fields.values():
                if isinstance(field, Void):
                    msg = "Invalid structure field: void"
                    raise mm.ValidationError(msg)
                if isinstance(field, Array) and field.len_field:
                    ref = field.len_field
                    if ref not in fields:
                        msg = f"Array field '{ref}' refers to "
                        msg += "non-existing length field"
                        raise mm.ValidationError(msg)

        @mm.post_load
        def construct(self, data, **kwargs):
            for field in data["field"].values():
                if isinstance(field, Array) and field.len_field:
                    data["field"][field.len_field].set_readonly(True)
            return Structure(**data)

    def select_types(self, of_class=None):
        res = [self] if of_class == tok.TYPE_STRUCTURE else []
        for field_type in self.field.values():
            sub_res = field_type.select_types(of_class=of_class)
            res.extend(sub_res)
        return res


@dataclass(eq=False)
class TypeRef(TypeABC):
    ref: Uid
    range_mod: Optional[Range]
    endian_mod: Optional[Endian]
    bit_size: Optional[IntBase]

    class Schema(TypeABC.Schema):
        ref = Uid.Field(data_key=tok.ATTR_REF, required=True)
        range_mod = Range.Field(data_key=tok.ATTR_RANGE, load_default=None)
        endian_mod = EndianField(data_key=tok.ATTR_ENDIAN, load_default=None)
        bit_size = IntBase.Field(data_key=tok.ATTR_BIT_SIZE, load_default=None)

        @mm.post_load
        def construct(self, data, **kwargs):
            return TypeRef(**data)

    def __eq__(self, other):
        return isinstance(other, TypeRef) and self.ref == other.ref

    def __hash__(self):
        return hash(self.ref)

    def derefer(self):
        return self.get_referred_type().derefer()

    def get_referred_type(self):
        try:
            return FtnDb.instance().get(self.ref)
        except Exception as e:
            raise FtnError(e, **vars(self))

    def select_types(self, of_class=None):
        referred_type = self.derefer()
        return (
            [self]
            if of_class == tok.TYPE_REF
            else [] + referred_type.select_types(of_class=of_class)
        )


## FtnDb ##

class FtnDb:
    __instance = None
    __specs: Dict[str, mm.Schema] = {
        tok.TYPE_ATOM: Atom.Schema(),
        tok.TYPE_VOID: Void.Schema(),
        tok.TYPE_BOOLEAN: Boolean.Schema(),
        tok.TYPE_INTEGER: Integer.Schema(),
        tok.TYPE_ARRAY: Array.Schema(),
        tok.TYPE_STRUCTURE: Structure.Schema(),
        tok.TYPE_REF: TypeRef.Schema(),
    }

    _srcs: Dict[str, Dict]
    _defs: Dict[Uid, TypeABC]

    @staticmethod
    def instance():
        """ Static access method. """
        if FtnDb.__instance is None:
            raise Exception("FtnDb has not been initialized yet.")
        return FtnDb.__instance

    @staticmethod
    def clear_instance():
        FtnDb.__instance = None

    def to_raw(self):
        return self._srcs
        
    def __init__(self, srcs={}):
        """ Constructor should be called at the beginning of the program. """
        if FtnDb.__instance is not None:
            raise Exception("FtnDb has already been initialized.")
        else:
            FtnDb.__instance = self

        self._srcs = srcs
        self._defs = {}

    def add_source(self, module, name, src) -> None:
        """Adds a user-provided FTN source in the database."""
        if module in self._srcs and name in self._srcs[module]:
            msg = f"Type '{module}.{name}' already exists."
            raise Exception(msg)
        if module not in self._srcs:
            self._srcs[module] = {}
        self._srcs[module][name] = src

    def parse(self, src) -> TypeABC:
        """Returns a base FTN type without adding it to the database."""
        return TypeABC.Field().deserialize(src)

    def schema(self, base_type_name: str) -> mm.Schema:
        """ Returns the JSON schema for a base type. """
        if base_type_name not in self.__specs:
            msg = f"No schema found for base type '{base_type_name}'"
            raise Exception(msg)
        return self.__specs[base_type_name]

    def get(self, uid: Union[Uid, str, TypeABC], **kwargs):
        """Returns a type definition. If not found it searches for its source
        module, loads it and deserializes its respective field using
        a corresponding base type schema.

        """
        if isinstance(uid, TypeABC):
            return uid

        uid = uid if isinstance(uid, Uid) else Uid(uid)
        if uid in self._defs:
            return self._defs[uid]

        if uid.module not in self._srcs:
            raise Exception(f"Module '{uid.module}' not loaded")
        if uid.name not in self._srcs[uid.module]:
            raise Exception(f"No type '{uid.name}' in module '{uid.module}'")

        entry = self._srcs[uid.module][uid.name]
        try:
            self._defs[uid] = TypeABC.Field().deserialize(entry)
        except mm.ValidationError as e:
            raise FtnError(
                e, uid=uid, type=entry.get(tok.ATTR_TYPE), info=get_pos(entry)
            )
        return self._defs[uid]

    def make_type(self, name=None, from_ftn=None, from_spec=None, from_assign=None, value=None):
        def _newsource(assignment):
            qual = next(iter(assignment))
            newid = Uid(qual)
            self.add_source(newid.module, newid.name, assignment[qual])
            return newid

        ndefs = len(
            [x for x in [name, from_ftn, from_spec, from_assign] if x is not None])
        if ndefs == 0:
            raise FtnError("No data type definition provided.")
        if ndefs != 1:
            raise FtnError("Too many definitions provided.")
        if name is not None:
            self.get(name)
            return {"type": Uid(name), "value": value}
        if from_ftn is not None:
            try:
                bind = lang.load_binding(from_ftn)
                return {"type": _newsource(bind), "value": value}
            except Exception:
                spec = lang.load_str(from_ftn)
                return {"type": self.parse(spec), "value": value}
        if from_assign is not None:
            return {"type": _newsource(from_assign), "value": value}
        if from_spec is not None:
            return {"type": self.parse(from_spec), "value": value}

    def dump(self, uid: Union[Uid, str]):
        """Serializes a previously loaded type."""
        uid = uid if isinstance(uid, Uid) else Uid(uid)
        if uid not in self._defs:
            msg = f"Type '{uid}' not loaded yet, hence nothing to dump!"
            raise Exception(msg)
        ty = self._defs[uid]
        try:
            mapping = ty.__class__.Schema().dump(ty)
        except Exception as e:
            raise FtnError(e, **vars(ty))
        return mapping

    def loaded_types(self):
        """ Returns UIDs of all parsed and stored types """
        return self._defs.keys()

    def type_dependency_graph(self):
        deps = nx.DiGraph()
        for ty in self.loaded_types():
            try:
                tydep = [str(t.ref)
                         for t in self.get(ty).select_types(of_class="ref")]
                # print(ty, tydep)
                nx.add_path(deps, tydep + [str(ty)])
            except Exception as e:
                the_type = self.get(ty)
                t, i = ((the_type.__class__.__name__, the_type.info.get("__pos__"))
                        if the_type else (None, None))
                raise FtnError(e, type=t, info=i)
        return deps


#####################################################
# if __name__ == "__main__":
#     from pprint import pprint

#     import zoti_ftn.frontend as front

#     class Test(mm.Schema):
#         num = IntBase.Field()
#         range = Range.Field()

#     tst = Test()
#     print(tst.dump(tst.load({"num": (20, 8)})))
#     print(tst.dump(tst.load({"num": "0x1221"})))
#     print(tst.dump(tst.load({"num": "0b1001"})))
#     print(tst.load({"range": [20, "0x22123"]}))
#     print(tst.dump(tst.load({"range": 20})))

#     print("================================")
#     handler = FtnDb(search_paths=["test/types"], loader=front.FtnLoader())
#     x = handler.get("Common.TimeSlot")
#     print(x)
#     pprint(handler.dump("Common.TimeSlot"))
#     x = handler.get("Tst.ResData")
#     print(x)
#     pprint(handler.dump("Tst.ResData"))
#     x = handler.get(Uid("Tst.StreamData"))
#     print(x)
#     pprint(handler.dump("Tst.StreamData"))
#     for f in x.select_types(of_class=TypeRef):
#         print(f.derefer())
#     print(handler.loaded_types())
#     print("================================")
#     handler.load_module("Res", loader=front.FtnLoader())
#     x = handler.get(Uid("Res.InterSample"))
#     pprint(handler.dump("Res.InterSample"))
