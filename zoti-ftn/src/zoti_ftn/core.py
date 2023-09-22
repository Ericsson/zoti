#!/usr/bin/env python3

from copy import deepcopy
from dataclasses import dataclass, replace
from enum import Enum
from typing import Dict, Optional, Union, List

import marshmallow as mm
import networkx as nx
from zoti_yaml import get_pos

import zoti_ftn.lang as lang
import zoti_ftn.tokens as tok
import zoti_ftn.util as util
from zoti_ftn.exceptions import FtnError, PrettyValidationError


## Unique identifier ##


class Uid:
    """Unique identifier for a type name (binding). *qualified name* is a
    string of form

    - ``<module>.<name>`` in which case the components are extracted accordingly
    - ``<name>`` in which case *module* becomes ``__local__``.

    """

    name: str
    module: str

    def __init__(self, qualified_name):
        if "." in qualified_name:
            self.module, self.name = qualified_name.rsplit(".", 1)
        else:
            self.module = "__local__"
            self.name = qualified_name

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        return (
            isinstance(other, Uid)
            and self.name == other.name
            and self.module == other.module
        )

    def __repr__(self):
        return f"{self.module}.{self.name}"

    class Field(mm.fields.Field):
        def _serialize(self, uid, attr, obj, **kwargs):
            return{"module": self.module, "name": self.name}

        def _deserialize(self, val, attr, data, **kwargs):
            if "module" not in val or "name" not in val:
                msg = f"Uid arguments invalid: {val}"
                raise mm.ValidationError(msg)
            uid = Uid(".")
            uid.name = val["name"]
            uid.module = val["module"]
            return uid

        
class Entry(Uid):
    """Extension class for :class:`Uid`, associating an (usually)
    initialization value to a defined type.

    """
    
    value: Optional[str] = None
 
    def __init__(self, qualified_name, value: Optional[str] = None):
        if isinstance(qualified_name, Uid):
            self.name = qualified_name.name
            self.module = qualified_name.module
        else:
            super(Entry, self).__init__(qualified_name)
        self.value = value

    def __eq__(self, other):
        return super(Entry, self).__eq__(other)

    def __hash__(self):
        return hash(super(Entry, self).__repr__())
    
    def __repr__(self):
        return super(Entry, self).__repr__() + (f" = {self.value}" if self.value else "")

        
## Endian ##


class Endian(Enum, metaclass=util.SearchableEnum):
    """Encode endianness"""
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
    """Represents an integer in an arbitrary base. Its parser can read:
    
    - binary numbers, e.g., ``0b1100``
    - base 8 numbers, e.g., ``0o1147``
    - base 16 numbers, e.g., ``0x11FF``
    - base 10 numbers, e.g., ``1100``
    - arbitrary base numbers from a tuple, e.g., ``(<value>, <base>)``

    """
    
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
    single value.  

    """

    low: IntBase
    high: IntBase

    def __repr__(self):
        return "({}..{})".format(self.low.value, self.high.value)

    def __contains__(self, item):
        return self.low.value <= item <= self.high.value

    def values(self):
        """Returns the range as a tuple of numbers."""
        return (self.low.value, self.high.value)

    def size(self):
        """Calculates the number of elements contained in this range."""
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
    """Marks the contained value as being a constant."""
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
    """Abstract base class for all type representations."""
    type: str
    readonly: bool
    _info: Optional[dict]

    class Schema(mm.Schema):
        class Meta:
            strict = True

        type = mm.fields.String()
        readonly = mm.fields.Bool(load_default=False)
        _info = mm.fields.Raw(data_key=tok.ATTR_INFO, load_default=None)

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

    def derefer(self) -> "TypeABC":
        """Returns 'self'. Possibly overloaded by instances.

        """
        return self

    def set_readonly(self, value: bool):
        new = replace(self, readonly=value)
        self.__dict__ = deepcopy(new.__dict__)


class Void(TypeABC):
    """Void type."""
    class Schema(TypeABC.Schema):
        @mm.post_load
        def construct(self, data, **kwargs):
            return Void(**data)

    def select_types(self, of_class=None) -> List[TypeABC]:
        """Predicate selection function."""
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
    """Boolean type."""
    bit_size: Optional[IntBase] = None

    class Schema(TypeABC.Schema):
        bit_size = IntBase.Field(data_key=tok.ATTR_BIT_SIZE, load_default=None)

        @mm.post_load
        def construct(self, data, **kwargs):
            return Boolean(**data)

    def select_types(self, of_class=None) -> List[TypeABC]:
        """Predicate selection function."""
        return [self] if of_class == tok.TYPE_BOOLEAN else []

    def normalize_value(self, value) -> Optional[bool]:
        """Tries to convert a value to a Python bool. Returns None if
        unsuccessful.

        """
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
    """Integer type. *OBS:* *range* attribute is mandatory."""
    range: Range
    endian: Optional[Endian] = None
    bit_size: Optional[IntBase] = None

    class Schema(TypeABC.Schema):
        range = Range.Field(data_key=tok.ATTR_RANGE)
        endian = EndianField(data_key=tok.ATTR_ENDIAN, load_default=None)
        bit_size = IntBase.Field(data_key=tok.ATTR_BIT_SIZE, load_default=None)

        @mm.post_load
        def construct(self, data, **kwargs):
            return Integer(**data)

    def select_types(self, of_class=None) -> List[TypeABC]:
        """Predicate selection function."""
        return [self] if of_class == tok.TYPE_INTEGER else []

    def normalize_value(self, value) -> Optional[int]:
        """Tries to convert a value to a Python int. Returns None if
        unsuccessful.

        """
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
    """Array type. *OBS:* *range* and *element_type* attributes are
    mandatory.

    """

    range: Range
    element_type: TypeABC
    len_field: Optional[str] = None

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

    def select_types(self, of_class=None) -> List[TypeABC]:
        """Predicate selection function. Recurs into the contained type."""
        return (
            [self]
            if of_class == tok.TYPE_ARRAY
            else [] + self.element_type.select_types(of_class=of_class)
        )


@dataclass
class Structure(TypeABC):
    """A structure type is represented as a dictionary of other types."""
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

    def select_types(self, of_class=None) -> List[TypeABC]:
        """Predicate selection function. Recurs into all contained types."""
        res = [self] if of_class == tok.TYPE_STRUCTURE else []
        for field_type in self.field.values():
            sub_res = field_type.select_types(of_class=of_class)
            res.extend(sub_res)
        return res


@dataclass(eq=False)
class TypeRef(TypeABC):
    """Qualified reference to another (defined) type."""
    ref: Uid
    range_mod: Optional[Range] = None
    endian_mod: Optional[Endian] = None
    bit_size: Optional[IntBase] = None

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

    def derefer(self) -> TypeABC:
        """Overloads the base method. Recurs into the referenced type."""
        return self.get_referred_type().derefer()

    def get_referred_type(self) -> TypeABC:
        """Retrieves the (previously loaded) referenced type from the current
        :class:`FtnDb` singleton."""
        try:
            return FtnDb.instance().get(self.ref)
        except Exception as e:
            raise FtnError(e, **vars(self))

    def select_types(self, of_class=None) -> List[TypeABC]:
        """Predicate selection function. Recurs into the referenced type."""
        referred_type = self.derefer()
        return (
            [self]
            if of_class == tok.TYPE_REF
            else [] + referred_type.select_types(of_class=of_class)
        )


## FtnDb ##

class FtnDb:
    """This is a singleton handler that takes care of loading and
    constructing the module dictionaries, populating them with FTN
    type definitions, and retrieving various information. Its
    constructor should be called exactly once at the beginning of the
    program.

    :arg srcs: dictionaries of modules with raw type definitions in
        AST format (e.g., JSON).

    """
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
        """Static destructor. Allows the subsequent creation of a new handler."""
        FtnDb.__instance = None

    def to_raw(self):
        """Returns the dictionaries of raw JSON/AST sources."""
        return self._srcs
        
    def __init__(self, srcs={}):
        if FtnDb.__instance is not None:
            raise Exception("FtnDb has already been initialized.")
        else:
            FtnDb.__instance = self

        self._srcs = srcs
        self._defs = {}

    def add_source(self, module: str, name: str, src: Dict) -> None:
        """Adds a user-provided raw source in the database."""
        if module in self._srcs and name in self._srcs[module]:
            msg = f"Type '{module}.{name}' already exists."
            raise Exception(msg)
        if module not in self._srcs:
            self._srcs[module] = {}
        self._srcs[module][name] = src

    def parse(self, src) -> TypeABC:
        """Returns a base FTN type from a raw source expression without adding
        it to the database.

        """
        return TypeABC.Field().deserialize(src)

    def schema(self, base_type_name: str) -> mm.Schema:
        """Returns the JSON schema used to parse a raw source expression into
        a base type.

        """
        
        if base_type_name not in self.__specs:
            msg = f"No schema found for base type '{base_type_name}'"
            raise Exception(msg)
        return self.__specs[base_type_name]

    def get(self, what: Union[Uid, str, TypeABC]) -> TypeABC:
        """Returns a fully-built and loaded type definition. If not found it
        searches for its source module, deserializes using a
        corresponding base type schema and stores it in the database
        for future use.

        """
        if isinstance(what, TypeABC):
            return what
        elif isinstance(what, Uid):
            uid = what
        else:
            uid = Entry(what)
            
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

    def make_entry(self, name: str = None, from_ftn: str = None, from_spec: Dict = None,
                   value: str = None) -> Entry:
        """(Possibly constructs and) stores a FTN data type into the current
        database and returns an :class:`Entry` object pointing to it.

        :arg name: (mutually exclusive with *from_ftn*, *from_spec*)
            qualified name to previously loaded type (calls
            :meth:`get` for good measure)

        :arg from_ftn: (mutually exclusive with *name*, *from_spec*)
            string with binding or expression in the FTN language.

        :arg from_spec: (mutually exclusive with *name*, *from_ftn*)
            string with binding or expression in raw format.

        :arg value: initialization value.

        """
        def _newsource(assignment):
            qual = next(iter(assignment))
            newid = Uid(qual)
            self.add_source(newid.module, newid.name, assignment[qual])
            return newid

        ndefs = len(
            [x for x in [name, from_ftn, from_spec] if x is not None])
        if ndefs == 0:
            raise FtnError("No data type definition provided.")
        if ndefs != 1:
            raise FtnError("Too many definitions provided.")
        
        if name is not None:
            self.get(name)
            return Entry(name, value=value)
        
        if from_ftn is not None:
            try:
                bind = lang.load_binding(from_ftn)
                return Entry(_newsource(bind), value=value)
            except Exception:
                spec = lang.load_str(from_ftn)
                qual = util.uniqueName("loctype", self._srcs.get("__local__"))
                uid  = _newsource({f"__local__.{qual}": spec})
                return Entry(uid, value=value)
        if from_spec is not None:
            try:
                return Entry(_newsource(from_spec), value=value)
            except Exception:
                qual = util.uniqueName("loctype", self._srcs.get("__local__"))
                uid  = _newsource({f"__local__.{qual}": from_spec})
                return Entry(uid, value=value)

    def dump(self, uid: Union[Uid, str]) -> Dict:
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

    def loaded_types(self) -> List[Uid]:
        """ Returns UIDs of all constructed and stored types """
        return list(self._defs.keys())

    def type_dependency_graph(self) -> nx.DiGraph:
        """Builds a NetworkX graph representing the type dependencies of all
        constructed and stored types.

        """
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

