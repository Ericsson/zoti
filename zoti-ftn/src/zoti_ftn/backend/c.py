#!/usr/bin/env python3

from typing import Dict, Union

import zoti_ftn.core as ftn
import zoti_ftn.tokens as tok
from zoti_ftn.exceptions import FtnError
from zoti_ftn.util import with_schema

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
    def has_subscript(self):
        return False

    def need_malloc(self):
        return False

    def gen_length_expr(self, arr_expr):
        return (None, None)

    def gen_ctor(self, buf_var, acc_expr, ptr_fixup=True):
        if not self.need_malloc():
            return ""

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
        return ";\n".join(ctor_lines) + ";\n"

    def gen_desctor(self, buf_var, buf_val=None):
        if not self.need_malloc():
            return ""
        dctor = f"free({buf_var});"
        if buf_val is not None:
            dctor += f"\n{buf_var} = {buf_val};"
        return dctor

    def gen_copy_stmt(self, dst_ptr, dst_acc_expr, src_ptr, src_acc_expr):
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
        return ";\n".join(stmt)

    def gen_size_expr(self, acc_expr):
        base_size_expr = self._gen_base_size_expr(acc_expr)
        arr_infos = self._gen_arr_infos(acc_expr)
        size_exprs = [base_size_expr] + [sz for _, sz, _ in arr_infos]
        return "(" + " + ".join(size_exprs) + ")"

    def gen_marshal(self, buf_ptr, acc_expr):
        return ";\n".join(self.gen_marshal_stmts(buf_ptr, acc_expr)) + ";"

    def gen_unmarshal(self, buf_ptr, acc_expr):
        return ";\n".join(self.gen_unmarshal_stmts(buf_ptr, acc_expr)) + ";"

    def gen_marshal_stmts(self, buf_ptr, acc_expr):
        return self._gen_marshalling(buf_ptr, acc_expr, 0)

    def gen_unmarshal_stmts(self, buf_ptr, acc_expr):
        return self._gen_marshalling(buf_ptr, acc_expr, 0, inverse=True)

    def _gen_arr_infos(self, acc_expr):
        return []

    # TODO: Making _gen_arr_infos public as below is just a temporary hack to
    #   get marshalling working again. The type handling needs rethinking.
    def gen_arr_infos(self, acc_expr):
        return self._gen_arr_infos(acc_expr)

    # TODO: Making _gen_base_size_expr public as below is just a temporary hack
    #   to get marshalling working again. The type handling needs rethinking.
    def gen_base_sze_expr(self, acc_expr):
        return self._gen_base_size_expr(acc_expr)


@with_schema(ftn.TypeRef.Schema)
class TypeRef(ftn.TypeRef, TypeABC):
    def has_subscript(self):
        return self.get_referred_type().has_subscript()

    def gen_c_type(self, name, allow_void=False):
        ref = self.ref
        return (_mangle_to_C_name(ref) + "_t", "")

    def gen_access_expr(self, src_expr, iter_lvl):
        return self.get_referred_type().gen_access_expr(src_expr, iter_lvl)

    def gen_subscript_expr(self, arr_expr):
        return self.get_referred_type().gen_subscript_expr(arr_expr)

    def gen_length_expr(self, arr_expr):
        return self.get_referred_type().gen_length_expr(arr_expr)

    def need_malloc(self):
        return self.get_referred_type().need_malloc()

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        return self.get_referred_type()._gen_marshalling(
            buf_ptr, acc_expr, iter_lvl, inverse
        )

    def _gen_base_size_expr(self, acc_expr):
        c_type, _ = self.gen_c_type(None)
        return "sizeof({})".format(c_type)

    def _gen_arr_infos(self, acc_expr):
        return self.get_referred_type()._gen_arr_infos(acc_expr)


@with_schema(ftn.Structure.Schema)
class Structure(ftn.Structure, TypeABC):
    def gen_c_type(self, name, allow_void=False):
        spc = " " if name else ""
        type_str = f"struct{spc}{name} {{\n"
        for n, t in self.field.items():
            prefix, suffix = t.gen_c_type("", allow_void=allow_void)
            prefix = " ".join([ln for ln in prefix.splitlines(keepends=True)])
            type_str += f" {prefix} {n}{suffix};\n"
        type_str += "}"
        return (type_str, "")

    def gen_access_expr(self, src_expr, iter_lvl):
        new_exprs = []
        for k, v in self.field.items():
            sub_exprs = v.gen_access_expr(f"{src_expr}.{k}", iter_lvl)
            ext_names = [([k] + n, a, e, ro) for n, a, e, ro in sub_exprs]
            new_exprs.extend(ext_names)
        return new_exprs

    def need_malloc(self):
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


@with_schema(ftn.Array.Schema)
class Array(ftn.Array, TypeABC):
    def has_subscript(self):
        return True

    def gen_c_type(self, name, allow_void=False):
        # TODO: This blindly does a memory layout to work with 64-bit machines
        #   and that works with 32-bits as well. It does not take into account
        #   byte ordering. It should all be handled in a different way, and
        #   probably be a transformation at the model level (e.g. FTN or JSFTN)
        #   so that the code gen is straight-forward.
        range_low, range_high = self.range.values()
        elem_type = self.element_type
        prefix, suffix = elem_type.gen_c_type(name, allow_void=allow_void)
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

    def gen_access_expr(self, src_expr, iter_lvl):
        # print(vars(self))
        iter_lvl += 1
        iter_var = f"i{iter_lvl}"
        # len_field = f"{src_expr}.len" if self.len_field is None else str(
        #     self.len_field)
        len_field, len_readonly = (
            (f"{self.range.low}", True)
            if self.range.low == self.range.high
            else (f"{src_expr}.len", False)
        )
        new_src = (
            f"{src_expr}[{iter_var}]"
            if self.range.low == self.range.high
            else f"{src_expr}.arr[{iter_var}]"
        )
        # print(len_field, len_readonly)
        sub_exprs = self.element_type.gen_access_expr(new_src, iter_lvl)
        new_exprs = [(n, [iter_var] + a, e, ro) for n, a, e, ro in sub_exprs]
        new_exprs.append((["LEN"], [], len_field, len_readonly))
        return new_exprs

    def gen_subscript_expr(self, arr_expr):
        rlow, rhigh = self.range.values()
        prefix = (
            f"{arr_expr}[" if self.range.low == self.range.high else f"{arr_expr}.arr["
        )
        suffix = "]"
        return prefix, suffix

    def gen_length_expr(self, arr_expr):
        if self.range.low == self.range.high:
            return (str(self.range.high), True)
        if self.len_field is not None:
            assert False, "TODO: This needs to refer to the surrounding Structure."
        return (f"{arr_expr}.len", False)

    def need_malloc(self):
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
            prefix, suffix = self.element_type.gen_c_type("")
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
        et_prefix, et_suffix = self.element_type.gen_c_type("")
        element_c_type = et_prefix + et_suffix
        return [
            (
                f"{acc_expr}.arr",
                f"{self.range.high} * ({'+'.join(elem_exprs)})",
                element_c_type,
            )
        ]


@with_schema(ftn.Void.Schema)
class Void(ftn.Void, TypeABC):
    def gen_c_type(self, name, allow_void=False):
        if not allow_void:
            msg = "Void not allowed"
            raise FtnError(msg, **vars(self))
        return ("void", "")

    def gen_access_expr(self, src_expr, iter_lvl):
        return None

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        return []


@with_schema(ftn.Atom.Schema)
class Atom(ftn.Atom, TypeABC):
    def gen_c_type(self, name, allow_void=False):
        return ("DFL_atom_t", "")

    def gen_access_expr(self, src_expr, iter_lvl):
        # TODO: Something more is probably needed here to manage byte order
        #   differences when transferring atoms, probably the same as integer
        #   needs.
        return [([], [], src_expr, self.readonly)]

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        return []


@with_schema(ftn.Integer.Schema)
class Integer(ftn.Integer, TypeABC):
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

    def gen_c_type(self, name, allow_void=False):
        # TODO: Something needs to be done to support more fine-grained bit-
        #   sizes for integers (and other types), for instance if we want to
        #   transmit a large array with values that would fit into 4 bits each.
        #   This then involves interaction between the Array and Integer types.
        #   The same with Structure which should result in bit-fields.
        return (self._choose_repr(), "")

    def gen_c_value(self, value):
        internal_value = super().normalize_value(value)
        if internal_value is None:
            msg = f"Could not normalize value '{value}'"
            raise FtnError(msg, **vars(self))
        return str(internal_value)

    def gen_access_expr(self, src_expr, iter_lvl):
        prefix, suffix = INT_SWAP_FUNCS[self._type_attrs()]
        return [([], [], prefix + src_expr + suffix, self.readonly)]

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        return []

    def _gen_base_size_expr(self, acc_expr):
        return f"sizeof({self._choose_repr()})"


@with_schema(ftn.Boolean.Schema)
class Boolean(ftn.Boolean, TypeABC):
    def gen_c_type(self, name, allow_void=False):
        return ("bool", "")

    def gen_c_value(self, value):
        internal_value = super().normalize_value(value)
        if internal_value is None:
            msg = f"Could not normalize value '{value}'"
            raise FtnError(msg, **vars(self))
        return "true" if internal_value else "false"

    def gen_access_expr(self, src_expr, iter_lvl):
        return [([], [], src_expr, self.readonly)]

    def _gen_marshalling(self, buf_ptr, acc_expr, iter_lvl, inverse=False):
        return []

    def _gen_base_size_expr(self, acc_expr):
        return "sizeof(bool)"


class FtnDb(ftn.FtnDb):
    __specs = {
        tok.TYPE_ATOM: Atom.Schema(),
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

    def c_name(self, uid: Union[ftn.Uid, str, TypeABC]):
        if isinstance(uid, TypeABC):
            return uid.gen_c_type("", allow_void=True)[0]
        uid = uid if isinstance(uid, ftn.Uid) else ftn.Uid(uid)
        return _mangle_to_C_name(uid) + "_t"

    def requirements(self):
        return ["<stdlib.h>", "<stdbool.h>", "<inttypes.h>", "<string.h>"]

    def gen_c_typedef(self, uid: Union[ftn.Uid, str], allow_void=False):
        uid = uid if isinstance(uid, ftn.Uid) else ftn.Uid(uid)
        qname = _mangle_to_C_name(uid)
        prefix, suffix = self.get(uid).gen_c_type(qname, allow_void=allow_void)

        # print(uid, [t.ref for t in self.get(
        #     uid).select_types(of_class=tok.TYPE_REF)])
        typedef = f'/* FTN: Type definition for "{qname}_t" */\n'
        typedef += f"typedef {prefix} {qname}_t{suffix};\n"
        return typedef

    def gen_access_macros(self, uid: Union[ftn.Uid, str], read_only: bool = False):
        uid = uid if isinstance(uid, ftn.Uid) else ftn.Uid(uid)
        qname = _mangle_to_C_name(uid)
        hdr_lines = [f'/* FTN: Access macros for type "{qname}_t" */\n']
        for expr_info in self.get(uid).gen_access_expr("(x)", 0):
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

    def gen_access_dict(self, uid: Union[ftn.Uid, str], read_only: bool = False):
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

        if not (isinstance(uid, ftn.Uid) or isinstance(uid, str)):
            return None
        access_dict: Dict = {}
        uid = uid if isinstance(uid, ftn.Uid) else ftn.Uid(uid)
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

    # def gen_decl(self, var, name=None, usage=None, value=None, static=False):
    #     if usage is not None:
    #         ty_str = usage
    #     elif name is not None:
    #         ty_str = _mangle_to_C_name(ftn.Uid(name)) + "_t"
    #     else:
    #         raise ValueError("Cannot generate type declaration")
    #     static_str = "static " if static else ""
    #     value_str = f" = {value}" if value else ""
    #     return f"{static_str}{ty_str} {var}{value_str};"
    def gen_decl(self, var, type=None, value=None, usage=None, static=False, allow_void=False):
        if usage is not None:
            ty_str = usage
        elif isinstance(type, ftn.Uid):
            ty_str = _mangle_to_C_name(type) + "_t"
            # ty_str, _ = self.get(type).gen_c_type("", allow_void=allow_void)
        elif isinstance(type, str):
            ty_str = _mangle_to_C_name(ftn.Uid(type)) + "_t"
            # ty_str, _ = self.get(ftn.Uid(type)).gen_c_type("", allow_void=allow_void)
        elif isinstance(type, TypeABC):
            ty_str, _ = type.gen_c_type("", allow_void=allow_void)
        else:
            raise ValueError("Cannot generate type declaration")
        static_str = "static " if static else ""
        value_str = f" = {value}" if value else ""
        return f"{static_str}{ty_str} {var}{value_str};"
