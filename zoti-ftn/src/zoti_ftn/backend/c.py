#!/usr/bin/env python3

from typing import Dict, Union, Tuple, Optional, List, Set
from copy import deepcopy

import zoti_ftn.core as ftn
import zoti_ftn.tokens as tok
from zoti_ftn.exceptions import FtnError
from zoti_ftn.util import with_schema, post_load

INT_ATTRS_TABLE = [
    (0, 0xFF, (True, 8)),
    (-0x80, 0x7F, (False, 8)),
    (0, 0xFFFF, (True, 16)),
    (-0x8000, 0x7FFF, (False, 16)),
    (0, 0xFFFFFFFF, (True, 32)),
    (-0x80000000, 0x7FFFFFFF, (False, 32)),
    (0, 0xFFFFFFFFFFFFFFFF, (True, 64)),
    (-0x8000000000000000, 0x7FFFFFFFFFFFFFFF, (False, 64)),
]

INT_ATTRS_TO_STR = {
    (True, 8): "uint8_t",
    (False, 8): "int8_t",
    (True, 16): "uint16_t",
    (False, 16): "int16_t",
    (True, 32): "uint32_t",
    (False, 32): "int32_t",
    (True, 64): "uint64_t",
    (False, 64): "int64_t",
}

# Key is a tuple (reverse, unsigned, size). Result is tuple (prefix, suffix).
INT_SWAP_FUNCS = {
    (False, False, 8): ("", ""),
    (False, True, 8): ("", ""),
    (True, False, 8): ("", ""),
    (True, True, 8): ("", ""),
    (False, False, 16): ("", ""),
    (False, True, 16): ("", ""),
    (True, False, 16): ("DFL_swap_int16(", ")"),
    (True, True, 16): ("DFL_swap_uint16(", ")"),
    (False, False, 32): ("", ""),
    (False, True, 32): ("", ""),
    (True, False, 32): ("DFL_swap_int32(", ")"),
    (True, True, 32): ("DFL_swap_uint32(", ")"),
    (False, False, 64): ("", ""),
    (False, True, 64): ("", ""),
    (True, False, 64): ("DFL_swap_int64(", ")"),
    (True, True, 64): ("DFL_swap_uint64(", ")"),
}

TARGET_ENDIAN = "little"


def _mangle_to_C_name(uid: ftn.Uid):
    mangled = f"{uid.module}__{uid.name}"
    return mangled.replace("^", "_A_").replace("-", "_")


class TypeABC(ftn.TypeABC):
    def has_subscript(self) -> bool:
        """Returns false this type does not need indexing."""
        return False

    def need_malloc(self) -> bool:
        """Returns false. This type does not need memory allocation."""
        return False

    def gen_length_expr(self, arr_expr: str) -> Tuple[Optional[str], Optional[bool]]:
        """Returns a tuple of None. This type does not have a length
        expression."""
        return (None, None)

    def gen_ctor(self, buf_var: str, acc_expr: str, ptr_fixup: bool = True) -> List[str]:
        """If the type needs memory allocation (see :meth:`need_malloc`) it
        generates the statements for a constructor and returns
        it. Otherwise it returns an empty list.

        :arg buf_var: name of the buffer variable.

        :arg acc_expr: access expression for data in *buf_var* (e.g.,
          pointer notation)

        :arg prt_fixup: true if it needs a pointer fixup expression
          after construction (i.e., update the pointer).

        """
        if not self.need_malloc():
            return []

        base_size_expr = self._gen_base_size_expr(acc_expr)
        arr_infos = self._gen_arr_infos(acc_expr)
        size_exprs = [base_size_expr] + [sz for _, sz, _ in arr_infos]
        # print(base_size_expr, size_exprs, arr_infos)
        ctor_lines = [f"{buf_var} = malloc({' + '.join(size_exprs)})"]
        if ptr_fixup:
            last_ptr = buf_var
            last_size = base_size_expr
            for arr_ptr, sz, elem_c_type in arr_infos:
                assign = (
                    f"{arr_ptr} = ({elem_c_type} *)((char *)({last_ptr}) + {last_size})"
                )
                ctor_lines.append(assign)
                last_ptr = arr_ptr
                last_size = sz
        return ctor_lines

    def gen_desctor(self, buf_var: str, buf_val: Optional[str]=None) -> List[str]:
        """If the type needs memory allocation (see :meth:`need_malloc`) it
        generates the statements for a destructor and returns
        it. Otherwise it returns an empty list.

        :arg buf_var: name of the buffer variable
        :arg buf_val: initial (reset) value for the buffer.

        """
        if not self.need_malloc():
            return []
        dctor = [f"free({buf_var})"]
        if buf_val is not None:
            dctor.append(f"{buf_var} = {buf_val}")
        return dctor

    def gen_copy(self, dst_ptr: str, dst_acc_expr: str, src_ptr: str, src_acc_expr: str
                 ) -> List[str]:
        """Generates the statements for a copy expressions.

        :arg dst_ptr: name of the destination buffer.

        :arg dst_acc_expr: access expression for the data in *dst_ptr* 

        :arg src_ptr: name of the source buffer.

        :arg src_acc_expr: access expression for the data in *src_ptr* 

        """
        base_size_expr = self._gen_base_size_expr(dst_acc_expr)
        dst_arr_infos = self._gen_arr_infos(dst_acc_expr)
        src_arr_infos = self._gen_arr_infos(src_acc_expr)
        size_exprs = [base_size_expr] + [sz for _, sz, _ in dst_arr_infos]
        tot_size = "(" + " + ".join(size_exprs) + ")"
        stmt = [f"memcpy({dst_ptr}, {src_ptr}, {tot_size})"]
        for dst_info, src_info in zip(dst_arr_infos, src_arr_infos):
            dst_arr_ptr, _, elem_c_type = dst_info
            src_arr_ptr, _, _ = src_info
            cpy = (
                f"{dst_arr_ptr} = ({elem_c_type}*)((char*)({dst_ptr})"
                f" + ((char*)({src_arr_ptr}) - (char*)({src_ptr})))"
            )
            stmt.append(cpy)
        return stmt

    def gen_size_expr(self, acc_expr: str) -> str:
        """Generates an expression that calculates the total size of the data
        contained by this type.

        :arg acc_expr: data access expression. 
        """
        base_size_expr = self._gen_base_size_expr(acc_expr)
        arr_infos = self._gen_arr_infos(acc_expr)
        size_exprs = [base_size_expr] + [sz for _, sz, _ in arr_infos]
        return "(" + " + ".join(size_exprs) + ")"

    # TODO: Making _gen_base_size_expr public as below is just a temporary hack
    #   to get marshalling working again. The type handling needs rethinking.
    def gen_base_size_expr(self, acc_expr: str) -> str:
        """Generates an expression that calculates the header size for this
        type (i.e., the first element)

        :arg acc_expr: data access expression.

        """
        return self._gen_base_size_expr(acc_expr)

    def gen_marshal(self, buf_ptr: str, acc_expr: str) -> List[str]:
        """Generates the statements for type marshalling.

        :arg buf_ptr: name of the destination buffer.

        :arg acc_expr: access expression for the data at *buf_ptr*

        """
        return self._gen_marshalling(buf_ptr, acc_expr, 0)

    def gen_unmarshal(self, buf_ptr: str, acc_expr: str) -> List[str]:
        """Generates the statements for type marshalling.

        :arg buf_ptr: name of the destination buffer.

        :arg acc_expr: access expression for the data at *buf_ptr*

        """
        return self._gen_marshalling(buf_ptr, acc_expr, 0, inverse=True)

    def requirements(self) -> Set[str]:
        """This type has no include requirement."""
        return []

    def _gen_arr_infos(self, acc_expr):
        return []


#@with_schema(ftn.TypeRef.Schema)
class TypeRef(ftn.TypeRef, TypeABC):
    """Qualified reference to another (defined) type."""

    def requirements(self) -> Set[str]:
        """Returns the include requirements of the referred type"""
        return self.get_referred_type().requirements()

    def has_subscript(self) -> bool:
        """Checks if referred type needs to be indexed."""
        return self.get_referred_type().has_subscript()

    def gen_ctype_expr(self, name, allow_void=False) -> str:
        """Returns the name of the referred type.
        
        :return: (prefix, "")
        """
        ref = self.ref
        return (_mangle_to_C_name(ref) + "_t", "")

    def gen_access_expr(self, src_expr: str , iter_lvl: int
                        ) -> List[Tuple[List, List, str, str]]:
        """Returns the components to build the access expression for the
        referred type.

        :arg src_expr: arbitrary name for the variable in the access macro.

        :arg iter_lvl: how deep the current index level is.

        :return: list of 4-tuples (field-path, access-args, access-expr, read-only)
        """
        return self.get_referred_type().gen_access_expr(src_expr, iter_lvl)

    def gen_subscript_expr(self, arr_expr: str) -> Tuple[str, str]:
        """Returns the components for generating an eventual subscript
        expression for the referred type.

        :arg arr_expr: expression which evauates to an array type.

        """
        return self.get_referred_type().gen_subscript_expr(arr_expr)

    def gen_length_expr(self, arr_expr: str) -> Tuple[str, bool]:
        """Returns the components to build the length expression for the
        referred type

        :arg arr_expr: expression which evauates to an array type.

        """
        return self.get_referred_type().gen_length_expr(arr_expr)

    def need_malloc(self) -> bool:
        """Checks if the referred type needs memory allocation."""
        return self.get_referred_type().need_malloc()

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        return self.get_referred_type()._gen_marshalling(
            buf_ptr, acc_expr, iter_lvl, inverse
        )

    def _gen_base_size_expr(self, acc_expr):
        c_type, _ = self.gen_ctype_expr(None)
        return "sizeof({})".format(c_type)

    def _gen_arr_infos(self, acc_expr):
        return self.get_referred_type()._gen_arr_infos(acc_expr)

    class Schema(ftn.TypeRef.Schema):
        @post_load
        def construct(self, data, **kwargs):
            return TypeRef(**data)
    
class Structure(ftn.Structure, TypeABC):
    """A structure type is represented as a dictionary of other types."""

    def requirements(self) -> Set[str]:
        """Returns the set of include requirements for all fields."""
        return set().union(*[f.requirements() for f in self.field.values()])
    
    def gen_ctype_expr(self, name: str, allow_void: bool = False) -> Tuple[str, str]:
        """Generates the full C expression for defining this struct
        type. Structure definitions do not have a suffix, hence the
        second element of the tupe is an empty string.
        
        :return: (prefix, "")

        """
        spc = " " if name else ""
        type_str = f"struct{spc}{name} {{\n"
        for n, t in self.field.items():
            prefix, suffix = t.gen_ctype_expr("", allow_void=allow_void)
            prefix = " ".join([ln for ln in prefix.splitlines(keepends=True)])
            type_str += f" {prefix} {n}{suffix};\n"
        type_str += "}"
        return (type_str, "")

    def gen_access_expr(self, src_expr: str , iter_lvl: int
                        ) -> List[Tuple[List, List, str, str]]:
        """Returns the components to build the access expression every field
        in this structure.

        :arg src_expr: arbitrary name for the variable in the access macro.

        :arg iter_lvl: how deep the current index level is.

        :return: list of 4-tuples (field-path, access-args, access-expr, read-only)
        """
        new_exprs = []
        for k, v in self.field.items():
            sub_exprs = v.gen_access_expr(f"{src_expr}.{k}", iter_lvl)
            ext_names = [([k] + n, a, e, ro) for n, a, e, ro in sub_exprs]
            new_exprs.extend(ext_names)
        return new_exprs

    def need_malloc(self) -> bool:
        """Checks if any of the fields needs memory allocation"""
        for v in self.field.values():
            if v.need_malloc():
                return True
        return False

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        new_stmts = []
        for k, v in self.field.items():
            sub_stmts = v._gen_marshalling(
                buf_ptr, f"{acc_expr}.{k}", iter_lvl, inverse
            )
            new_stmts.extend(sub_stmts)
        return new_stmts

    def _gen_base_size_expr(self, acc_expr):
        return "sizeof({})".format(acc_expr)

    def _gen_arr_infos(self, acc_expr):
        size_exprs = []
        for k, v in self.field.items():
            size_exprs.extend(v._gen_arr_infos(f"{acc_expr}.{k}"))
        return size_exprs

    class Schema(ftn.Structure.Schema):
        @post_load
        def construct(self, data, **kwargs):
            return Structure(**data)

    
class Array(ftn.Array, TypeABC):
    """Array type."""
    def requirements(self) -> Set[str]:
        """Returns the requirements of the base type."""
        return self.element_type.requirements()
    
    def has_subscript(self) -> bool:
        """Returns true. An array needs indexing."""
        return True

    def gen_ctype_expr(self, name, allow_void=False) -> Tuple[str, str]:
        """Generates the C expression defining this array. If its range is
        fixed (i.e., *range.low* = *range.high*) then it is defined as
        a statically-allocated C array. Otherwise, it is defined as a
        structure with inferred elements such as pointer, offset and
        length.
        
        :return: (prefix, suffix)

        """
        
        # TODO: This blindly does a memory layout to work with 64-bit machines
        #   and that works with 32-bits as well. It does not take into account
        #   byte ordering. It should all be handled in a different way, and
        #   probably be a transformation at the model level (e.g. FTN or JSFTN)
        #   so that the code gen is straight-forward.
        range_low, range_high = self.range.values()
        elem_type = self.element_type
        prefix, suffix = elem_type.gen_ctype_expr(name, allow_void=allow_void)
        if range_low == range_high:
            return (prefix, f"{suffix}[{range_high}]")
        elif self.len_field is not None:
            new_prefix = (
                f"union {{\n"
                f"  {prefix} *arr{suffix};\n"
                f"  uint64_t offset;\n"
                f"}}"
            )
            return (new_prefix, "")
        else:
            len_type_strs = [
                INT_ATTRS_TO_STR[attrs]
                for attrs_low, attrs_high, attrs in INT_ATTRS_TABLE
                if range_low >= attrs_low and range_high <= attrs_high
            ]
            if not len(len_type_strs) > 0:
                msg = "could not deduce array length"
                raise FtnError(msg, **vars(self))
            new_prefix = (
                f"struct {{\n"
                f"  union {{\n"
                f"    {prefix} *arr{suffix};\n"
                f"    uint64_t offset;\n"
                f"  }};\n"
                f"  {len_type_strs[0]} len;\n"
                f"}}"
            )
            return (new_prefix, "")

    def gen_access_expr(self, src_expr: str , iter_lvl: int
                        ) -> List[Tuple[List, List, str, str]]:
        """Returns the components to build the access expression for
        everything contained in the element with an appended static
        LEN field.

        :arg src_expr: arbitrary name for the variable in the access macro.

        :arg iter_lvl: how deep the current index level is.

        :return: list of 4-tuples (field-path, access-args, access-expr, read-only)

        """
        # print(vars(self))
        iter_lvl += 1
        iter_var = f"i{iter_lvl}"
        # len_field = f"{src_expr}.len" if self.len_field is None else str(
        #     self.len_field)
        if self.range.low == self.range.high:
            len_field = f"{self.range.low}"
            len_readonly = True
            new_src_expr = f"{src_expr}[{iter_var}]"
        else:
            len_field = f"{src_expr}.len"
            len_readonly = False
            new_src_expr = f"{src_expr}.arr[{iter_var}]"
            
        # print(len_field, len_readonly)
        sub_exprs = self.element_type.gen_access_expr(new_src_expr, iter_lvl)
        new_exprs = [(n, [iter_var] + a, e, ro) for n, a, e, ro in sub_exprs]
        new_exprs.append((["LEN"], [], len_field, len_readonly))
        return new_exprs

    def gen_subscript_expr(self, arr_expr: str) -> Tuple[str, str]:
        """Generates an indexing expression.

        :return: ("<expr>[", "]")
        """
        rlow, rhigh = self.range.values()
        prefix = (
            f"{arr_expr}[" if self.range.low == self.range.high else f"{arr_expr}.arr["
        )
        suffix = "]"
        return prefix, suffix

    def gen_length_expr(self, arr_expr: str) -> Tuple[str, bool]:
        """Generates a lenghth expression, together with a bool representing
        whether the length is fixed or not."""
        if self.range.low == self.range.high:
            return (str(self.range.high), True)
        if self.len_field is not None:
            assert False, "TODO: This needs to refer to the surrounding Structure."
        return (f"{arr_expr}.len", False)

    def need_malloc(self) -> bool:
        """Returns true if the length is not fixed or if the element needs
        memory allocation; otherwise false.

        """
        if self.range.low != self.range.high:
            return True
        return self.element_type.need_malloc()

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        iter_lvl += 1
        iter_var = f"i{iter_lvl}"
        stmts = []
        if self.range.low == self.range.high:
            new_acc = f"{acc_expr}[{iter_var}]"
        else:
            if not iter_lvl < 2:
                msg = "Cannot currently handle nested dynamic arrays."
                raise FtnError(msg, **vars(self))
            new_acc = "{acc_expr}.arr[{iter_var}]"
            prefix, suffix = self.element_type.gen_ctype_expr("")
            elem_type = prefix + suffix
            if inverse:
                stmts.append(
                    f"{acc_expr}.arr = ({elem_type}*)((char*){buf_ptr} + {acc_expr}.offset)"
                )
            else:
                stmts.append(
                    f"{acc_expr}.offset = (char*)({acc_expr}.arr) - (char*)({buf_ptr})"
                )
        sub_stmts = self.element_type._gen_marshalling(
            new_acc, iter_lvl, inverse)
        stmts.extend(sub_stmts)
        return stmts

    def _gen_base_size_expr(self, acc_expr):
        return f"sizeof({acc_expr})"

    def _gen_arr_infos(self, acc_expr):
        # TODO: This only handles the case when the array entry is a pointer and
        #   the actual array needs to be malloced. The case when the array is of
        #   static size should also be handled.
        sub_acc = f"{acc_expr}[0]"
        elem_exprs = [self.element_type._gen_base_size_expr(sub_acc)]
        elem_exprs.extend(self.element_type._gen_arr_infos(sub_acc))
        et_prefix, et_suffix = self.element_type.gen_ctype_expr("")
        element_c_type = et_prefix + et_suffix
        return [
            (
                f"{acc_expr}.arr",
                f"{self.range.high} * ({'+'.join(elem_exprs)})",
                element_c_type,
            )
        ]

    class Schema(ftn.Array.Schema):
        @post_load
        def construct(self, data, **kwargs):
            return Array(**data)


class Void(ftn.Void, TypeABC):
    def gen_ctype_expr(self, name, allow_void=False) -> Tuple[str, str]:
        """If *allow_void* is false, throws an error.

        :return: ("void", "")
        """
        if not allow_void:
            msg = "Void not allowed"
            raise FtnError(msg, **vars(self))
        return ("void", "")

    def gen_access_expr(self, src_expr, iter_lvl) -> None:
        """A void element has no access expresison."""
        return None

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        return []

    class Schema(ftn.Void.Schema):
        @post_load
        def construct(self, data, **kwargs):
            return Void(**data)

# @with_schema(ftn.Atom.Schema)
# class Atom(ftn.Atom, TypeABC):
#     def gen_ctype_expr(self, name, allow_void=False):
#         return ("DFL_atom_t", "")

#     def gen_access_expr(self, src_expr, iter_lvl):
#         # TODO: Something more is probably needed here to manage byte order
#         #   differences when transferring atoms, probably the same as integer
#         #   needs.
#         return [([], [], src_expr, self.readonly)]

#     def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
#         return []


# @with_schema(ftn.Integer.Schema)
class Integer(ftn.Integer, TypeABC):
    """C integer type."""
    
    def requirements(self) -> Set[str]:
        """This representation uses explicit integer types as defined in
        <inttypes.h>. Bit-swap functions are defined in the in-house
        header file 'DFL_util.h' found in the 'assets' folder.

        """
        return set(["<inttypes.h>", '"DFL_util.h"'])
    
    def _range_type_attrs(self):
        rl, rh = self.range.values()
        for low, high, attrs in INT_ATTRS_TABLE:
            if rl >= low and rh <= high:
                return attrs
        raise FtnError(f"Invalid range specified: {self.range}", **vars(self))

    def _type_attrs(self):
        unsigned, size = self._range_type_attrs()
        if self.bit_size:
            if self.bit_size.value < size:
                msg = f"Range {self.range} does not fit in bit_size {self.bit_size}"
                raise FtnError(msg, **vars(self))
            size = self.bit_size.value
        endian = self.endian
        reverse = bool(endian and endian != TARGET_ENDIAN)
        return (reverse, unsigned, size)

    def _choose_repr(self):
        reverse, unsigned, size = self._type_attrs()
        hwi_type = INT_ATTRS_TO_STR[(unsigned, size)]
        if reverse and size > 8:
            repr_type = INT_ATTRS_TO_STR[(True, size)]
            sign_cmt = "" if unsigned else f"represents {hwi_type},"
            return f"{repr_type}/*{sign_cmt}reverse byteorder*/"
            # return REVERSE_INT_TO_STR[(unsigned, size)]
        else:
            return hwi_type

    def gen_ctype_expr(self, name: str, allow_void=False) -> Tuple[str, str]:
        """Chooses an appropriate type representation for this integer based
        on its properties.

        :return: ("<expr>", "")
        """
        
        # TODO: Something needs to be done to support more fine-grained bit-
        #   sizes for integers (and other types), for instance if we want to
        #   transmit a large array with values that would fit into 4 bits each.
        #   This then involves interaction between the Array and Integer types.
        #   The same with Structure which should result in bit-fields.
        return (self._choose_repr(), "")

    def gen_c_value(self, value) -> str:
        """Normalizes a given value to a C integer value representation."""
        internal_value = super().normalize_value(value)
        if internal_value is None:
            msg = f"Could not normalize value '{value}'"
            raise FtnError(msg, **vars(self))
        return str(internal_value)

    def gen_access_expr(self, src_expr: str , iter_lvl: int
                        ) -> List[Tuple[List, List, str, str]]:
        """Generates the appropriate access expression for this integer based
        on its properties (e.g., endianness).

        :arg src_expr: arbitrary name for the variable in the access macro.

        :arg iter_lvl: how deep the current index level is.

        :return: singleton list witn a 4-tuple ([], [], access-expr, read-only)

        """
        prefix, suffix = INT_SWAP_FUNCS[self._type_attrs()]
        return [([], [], prefix + src_expr + suffix, self.readonly)]

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        return []

    def _gen_base_size_expr(self, acc_expr):
        return f"sizeof({self._choose_repr()})"

    class Schema(ftn.Integer.Schema):
        @post_load
        def construct(self, data, **kwargs):
            return Integer(**data)

        
# @with_schema(ftn.Boolean.Schema)
class Boolean(ftn.Boolean, TypeABC):
    """Boolean C type."""
    
    def requirements(self) -> Set[str]:
        """This representation uses the "bool" type as defined in <stdbool.h>

        """
        return set(["<stdbool.h>"])
    
    def gen_ctype_expr(self, name, allow_void=False) -> Tuple[str, str]:
        """:return: ("bool", "")"""
        return ("bool", "")

    def gen_c_value(self, value) -> str:
        """Normalizes a given value to a C bool representation."""
        internal_value = super().normalize_value(value)
        if internal_value is None:
            msg = f"Could not normalize value '{value}'"
            raise FtnError(msg, **vars(self))
        return "true" if internal_value else "false"

    def gen_access_expr(self, src_expr: str , iter_lvl: int
                        ) -> List[Tuple[List, List, str, str]]:
        """Returns access expression. Relevant for complex caller types."""
        return [([], [], src_expr, self.readonly)]

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        return []

    def _gen_base_size_expr(self, acc_expr):
        return "sizeof(bool)"

    class Schema(ftn.Boolean.Schema):
        @post_load
        def construct(self, data, **kwargs):
            return Boolean(**data)


class FtnDb(ftn.FtnDb):
    __specs = {
        # tok.TYPE_ATOM: Atom.Schema(),
        tok.TYPE_VOID: Void.Schema(),
        tok.TYPE_BOOLEAN: Boolean.Schema(),
        tok.TYPE_INTEGER: Integer.Schema(),
        tok.TYPE_ARRAY: Array.Schema(),
        tok.TYPE_STRUCTURE: Structure.Schema(),
        tok.TYPE_REF: TypeRef.Schema(),
    }

    FTN_GETTER_PREFIX = "FTNC_get__"
    FTN_SETTER_PREFIX = "FTNC_put__"

    def __init__(self, *args, **kwargs):
        super(FtnDb, self).__init__(*args, **kwargs)

    def requirements(self, types: List[ftn.Uid] = []) -> List[str]:
        """Parses through a list of given *types* and returns a set of their
        include requirements. If *types* not provided it searches
        through all defined types.
        """
        if not types:
            types = self.loaded_types()
        requs = [self.get(ty).requirements() for ty in types]
        ret = set().union(*requs)
        ret.add("<stdlib.h>")
        return list(ret)

    def gen_typename_expr(self, entry: ftn.Uid) -> str:
        """Generates the (prefix) type name for a loaded type. If the type is
        local, generates the C expression for that type."""
        name = _mangle_to_C_name(entry) + "_t"
        if entry.module == "__local__":
            return self.get(entry).gen_ctype_expr(name, allow_void=True)[0]
        return name
    
    def gen_decl(self, entry: ftn.Entry, var: str,
                 usage=None, static=False) -> List[str]:
        """Generates the statements for declaring (and eventually
        initializing) a type.

        :arg usage: overrides the generated expression
        :arg static: prefixes the definition with the 'static' keyword
        """
        name = _mangle_to_C_name(entry) + "_t"
        if usage is not None:
            ty_str, suffix = (usage, "")
        elif entry is not None and entry.module == "__local__":
            ty_str, suffix = self.get(entry).gen_ctype_expr(name, allow_void=True)
        elif entry is not None:
            ty_str = self.gen_typename_expr(entry)
            suffix = self.get(entry).gen_ctype_expr(ty_str, allow_void=True)[1]
        else:
            raise ValueError("Cannot generate type declaration")
        static_str = "static " if static else ""
        value_str = f" = {entry.value}" if entry.value else ""
        return [f"{static_str}{ty_str} {var}{suffix}{value_str}"]

    def gen_typedef(self, entry: ftn.Uid, allow_void=False):
        """Generates a statement for a typedef expression."""
        qname = _mangle_to_C_name(entry)
        prefix, suffix = self.get(entry).gen_ctype_expr(qname, allow_void=allow_void)
        
        typedef = f'/* FTN: Type definition for "{qname}_t" */\n'
        typedef += f"typedef {prefix} {qname}_t{suffix}"
        return [typedef]
    
    def gen_access_macros_expr(self, entry: ftn.Uid, read_only: bool = False) -> List[str]:
        """Generates access macros for all elements of this type as
        newline-separated expressions (not statements)."""
        qname = _mangle_to_C_name(entry)
        hdr_lines = [f'/* FTN: Access macros for type "{qname}_t" */\n']
        for expr_info in self.get(entry).gen_access_expr("(x)", 0):
            getset_names, getset_args, getset_expr, read_only_expr = expr_info
            name_components = [qname] + getset_names
            getter_args = ["x"] + getset_args
            getter_name = self.FTN_GETTER_PREFIX + "__".join(name_components)
            hdr_lines.append(
                f"#define {getter_name}({', '.join(getter_args)}) ({getset_expr})\n"
            )
            if read_only or read_only_expr:
                continue
            setter_args = getter_args + ["v"]
            setter_name = self.FTN_SETTER_PREFIX + "__".join(name_components)
            hdr_lines.append(
                f"#define {setter_name}({', '.join(setter_args)}) ({getset_expr}=(v))\n"
            )
        return hdr_lines

    def access_dict(self, uid: Union[TypeABC, ftn.Uid], read_only: bool = False) -> Dict:
        """Returns the access expressions for each element in this type as a
        dictionary tree (i.e., JSON object) accessible, e.g., from
        within a template expander.

        """
        def _recursive_dict(what, dct, lst, accessor):
            if not lst:
                return
            if len(lst) == 1:
                dct[lst[0]] = dct.get(lst[0], {})
                dct[lst[0]][what] = accessor
                return
            dct[lst[0]] = dct.get(lst[0], {})
            _recursive_dict(what, dct[lst[0]], lst[1:], accessor)

        if isinstance(uid, TypeABC):
            return {"_get": "", "_set": "FTNC_ASSIGN"}
        assert isinstance(uid, ftn.Uid)

        access_dict: Dict = {}
        qname = _mangle_to_C_name(uid)
        for getset_names, _, _, read_only_expr in self.get(uid).gen_access_expr("(x)", 0):
            name_components = [qname] + getset_names
            getter_name = self.FTN_GETTER_PREFIX + "__".join(name_components)
            if not getset_names:
                access_dict["_get"] = getter_name
            else:
                _recursive_dict("_get", access_dict, getset_names, getter_name)
            if read_only or read_only_expr:
                continue
            setter_name = self.FTN_SETTER_PREFIX + "__".join(name_components)
            if not getset_names:
                access_dict["_set"] = setter_name
            else:
                _recursive_dict("_set", access_dict, getset_names, setter_name)
        return access_dict

