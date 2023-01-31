#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import distribution

from arpeggio import NoMatch, PTNodeVisitor, visit_parse_tree
from arpeggio.cleanpeg import ParserPEG
from zoti_yaml import Pos, attach_pos

import zoti_ftn.tokens as tok
from zoti_ftn.exceptions import ParseError

dist = distribution("zoti_ftn")
tool_name= f"{dist.name}-{dist.version}"


_FTN_EXPR_GRAMMAR = r"""
  typespec   =  (aggrspec / simplespec)
  aggrspec   =  aggrkind "{" binding* "}"
  aggrkind   =  "structure"
  binding    =  id ":" typespec ";"
  simplespec =  (arrspec / atomspec / intspec / boolspec / voidspec / typeref / attrref)
  arrspec    =  "array" attrspec typespec
  atomspec   =  "atom"
  intspec    =  "integer" attrspec
  boolspec   =  "boolean" attrspec?
  voidspec   =  "void"
  typeref    =  id "." id attrspec?
  attrref    = "constant" attrspec
  attrspec   =  "(" (attrs / attrval / constref)? ")"
  attrs      =  attr (";" attr)*
  attr       =  id ":" attrval
  attrval    =  id / rangeval / intliteral
  constref   =  id
  id         =  r'[A-Za-z_][A-Za-z0-9_-]*'
  rangeval   =  intliteral ".." intliteral
  intliteral =  "-"? radix_pfx? r'[0-9A-Za-f]+'
  radix_pfx  =  r'0[xXoObB]'
"""


_FTN_GRAMMAR = (
    r"""
  ftn        =  import* moddef
  import     =  "import" id ("as" id)? ";"
  moddef     =  moddecl modspec ";"
  moddecl    =  id ":" "module"
  modspec    =  "{" binding* "}"
"""
    + _FTN_EXPR_GRAMMAR
)


_ftn_parser = ParserPEG(_FTN_GRAMMAR, "ftn")
_ftn_expr_parser = ParserPEG(_FTN_EXPR_GRAMMAR, "typespec")
_ftn_bexpr_parser = ParserPEG(_FTN_EXPR_GRAMMAR, "binding")


(
    ASTTYPE_ID,
    ASTTYPE_INT,
    ASTTYPE_RANGE,
    ASTTYPE_ATTR,
    ASTTYPE_ATTRLIST,
    ASTTYPE_TYPESPEC,
    ASTTYPE_MODULESPEC,
    ASTTYPE_MODULEIMPORT,
    ASTTYPE_FTN,
    ASTTYPE_ATTRREF,
) = range(10)


class FtnVisitor(PTNodeVisitor):
    TRANSIENT_ATTR_MODULE = object()
    TRANSIENT_ATTR_MODULE_NAME = object()
    TRANSIENT_ATTR_STRUCTURE = object()

    def __init__(self, global_env, path, to_linecol, **kwargs):
        super().__init__(**kwargs)
        self._path = path
        self._to_linecol = to_linecol
        self._global_env = global_env
        self._namespace_stack = [global_env]
        self._aliases = {}
        self._constants = {}

    def _push_namespace(self, ns):
        self._namespace_stack.append(ns)

    def _pop_namespace(self):
        return self._namespace_stack.pop()

    def _current_namespace(self):
        return self._namespace_stack[-1]

    def visit_ftn(self, node, children):
        imports = []
        for asttype, module_name in getattr(children, "import"):
            assert asttype == ASTTYPE_MODULEIMPORT
            imports.append(module_name)
        # TODO: returns only first module. Change if we want more modules per file
        asttype, module_specs = children.moddef[0]
        assert asttype == ASTTYPE_MODULESPEC
        file_spec = {tok.ATTR_IMPORTS: imports, tok.ATTR_MODULES: module_specs}
        return (ASTTYPE_FTN, file_spec)

    def visit_import(self, node, children):
        asttype, module_name = children.id[0]
        assert asttype == ASTTYPE_ID
        spec = {tok.ATTR_IMPORTS_MODULE: module_name}
        if len(children.id) == 2:
            asttype, alias_name = children.id[1]
            assert asttype == ASTTYPE_ID
            assert alias_name not in self._aliases
            self._aliases[alias_name] = module_name
        return (ASTTYPE_MODULEIMPORT, spec)

    def visit_moddecl(self, node, children):
        asttype, mod_name = children.id[0]
        assert asttype == ASTTYPE_ID
        module_collector = {}
        module_spec = {
            self.TRANSIENT_ATTR_MODULE_NAME: mod_name,
            tok.ATTR_TYPE: tok.TYPE_MODULE,
            tok.ATTR_ENTRIES: module_collector,
        }
        module_collector[self.TRANSIENT_ATTR_MODULE] = module_spec
        self._push_namespace(module_collector)

    def visit_modspec(self, node, children):
        module_collector = self._pop_namespace()
        module_spec = module_collector.pop(self.TRANSIENT_ATTR_MODULE)
        mod_name = module_spec.pop(self.TRANSIENT_ATTR_MODULE_NAME)
        self._current_namespace()[mod_name] = module_spec
        return (ASTTYPE_MODULESPEC, self._current_namespace())

    def visit_binding(self, node, children):
        asttype, type_name = children.id[0]
        assert asttype == ASTTYPE_ID
        asttype, type_spec = children.typespec[0]
        if asttype == ASTTYPE_ATTRREF:
            self._constants[type_name] = type_spec
            return
        
        assert asttype == ASTTYPE_TYPESPEC

        # Inject position information into the spec
        line, column = self._to_linecol(node.position)
        attach_pos(type_spec, Pos(line, column, path=self._path, who=tool_name))

        self._current_namespace()[type_name] = type_spec

    def visit_aggrspec(self, node, children):
        fields_collector = self._pop_namespace()
        structure_spec = fields_collector.pop(self.TRANSIENT_ATTR_STRUCTURE)
        return (ASTTYPE_TYPESPEC, structure_spec)

    def visit_aggrkind(self, node, children):
        fields_collector = {}
        structure_spec = {
            tok.ATTR_TYPE: tok.TYPE_STRUCTURE,
            tok.ATTR_FIELDS: fields_collector,
        }
        fields_collector[self.TRANSIENT_ATTR_STRUCTURE] = structure_spec
        self._push_namespace(fields_collector)

    def visit_arrspec(self, node, children):
        attrspec = children.attrspec[0]
        asttype, val = attrspec
        if asttype == ASTTYPE_ATTRLIST:
            attrs = val
        elif asttype == ASTTYPE_ID:
            assert val in self._constants
            attrs = self._constants[val]
        else:
            assert asttype in [ASTTYPE_RANGE, ASTTYPE_INT]
            attrs = [("range", attrspec)]
        spec = {tok.ATTR_TYPE: tok.TYPE_ARRAY}
        spec.update([(a, v[1]) for a, v in attrs])

        asttype, subtype = children.typespec[0]
        assert asttype == ASTTYPE_TYPESPEC
        spec[tok.ATTR_ELEMENT_TYPE] = subtype

        return (ASTTYPE_TYPESPEC, spec)

    def visit_atomspec(self, node, children):
        spec = {tok.ATTR_TYPE: tok.TYPE_ATOM}
        return (ASTTYPE_TYPESPEC, spec)

    def visit_intspec(self, node, children):
        astval = children.attrspec[0]
        asttype, val = astval
        if asttype == ASTTYPE_ATTRLIST:
            attrs = val
        else:
            assert asttype == ASTTYPE_RANGE
            attrs = [("range", astval)]
        spec = {tok.ATTR_TYPE: tok.TYPE_INTEGER}
        spec.update([(a, v[1]) for a, v in attrs])
        return (ASTTYPE_TYPESPEC, spec)

    def visit_boolspec(self, node, children):
        spec = {tok.ATTR_TYPE: tok.TYPE_BOOLEAN}
        if len(children.attrspec) > 0:
            asttype, attrs = children.attrspec[0]
            assert asttype == ASTTYPE_ATTRLIST
            spec.update([(a, v[1]) for a, v in attrs])
        return (ASTTYPE_TYPESPEC, spec)

    def visit_voidspec(self, node, children):
        spec = {tok.ATTR_TYPE: tok.TYPE_VOID}
        return (ASTTYPE_TYPESPEC, spec)

    def visit_typeref(self, node, children):
        asttype, mod_name = children.id[0]
        assert asttype == ASTTYPE_ID
        asttype, type_name = children.id[1]
        assert asttype == ASTTYPE_ID
        if mod_name in self._aliases:
            mod_name = self._aliases[mod_name]
        ref = {"module": mod_name, "name": type_name}

        spec = {tok.ATTR_TYPE: tok.TYPE_REF, tok.ATTR_REF: ref}
        if len(children.attrspec) > 0:
            asttype, attrs = children.attrspec[0]
            if asttype != ASTTYPE_ATTRLIST:
                assert asttype == ASTTYPE_RANGE
                attrs = [("range", attrs)]
            spec.update([(a, v[1]) for a, v in attrs])

        return (ASTTYPE_TYPESPEC, spec)

    def visit_attrref(self, node, children):
        astval = children.attrspec[0]
        asttype, val = astval
        if asttype == ASTTYPE_ATTRLIST:
            attrs = val
        else:
            assert asttype in [ASTTYPE_RANGE, ASTTYPE_INT]
            attrs = [("range", astval)]
        # spec = {tok.ATTR_TYPE: tok.TYPE_CONSTANT}
        # spec.update([(a, v[1]) for a, v in attrs])
        return(ASTTYPE_ATTRREF, attrs)

    def visit_attrs(self, node, children):
        attrlist = []
        for e in children:
            asttype, attr = e
            assert asttype == ASTTYPE_ATTR
            attrlist.append(attr)
        return (ASTTYPE_ATTRLIST, attrlist)

    def visit_attr(self, node, children):
        asttype, name = children.id[0]
        assert asttype == ASTTYPE_ID
        val = children.attrval[0]
        return (ASTTYPE_ATTR, (name, val))

    def visit_id(self, node, children):
        id_name = str(node)
        return (ASTTYPE_ID, id_name)

    def visit_rangeval(self, node, children):
        asttype, low = children.intliteral[0]
        assert asttype == ASTTYPE_INT
        asttype, high = children.intliteral[1]
        assert asttype == ASTTYPE_INT
        return (ASTTYPE_RANGE, [low, high])

    def visit_intliteral(self, node, children):
        int_str = "".join(children)
        return (ASTTYPE_INT, int_str)


def _load_str(expr_str, parser, path, to_linecol):
    try:
        parse_tree = parser.parse(expr_str)
        spec = {}
        ast, expspec = visit_parse_tree(parse_tree, FtnVisitor(spec, path, to_linecol))
    except NoMatch as e:
        raise ParseError(e, path=path)
    return ast, expspec, spec

def load_str(expr_str):
    asttype, spec, _ = _load_str(
        expr_str, _ftn_expr_parser, "<user input>", _ftn_expr_parser.pos_to_linecol
    )
    assert asttype == ASTTYPE_TYPESPEC
    return spec

def load_binding(expr_str):
    _, _, spec = _load_str(
        expr_str, _ftn_bexpr_parser, "<user input>", _ftn_bexpr_parser.pos_to_linecol
    )
    return spec

def load_file(f):
    def _skip_comments(s):
        return s.partition("#")[0]
    
    # with open(path) as f:
    spec_str = "".join([_skip_comments(ln) for ln in f.readlines()])
    asttype, file_spec, _ = _load_str(
        spec_str, _ftn_parser, f.name, _ftn_parser.pos_to_linecol
    )
    def preamble(name): return {
        "module": name,
        "path": f.name,
        "import": file_spec[tok.ATTR_IMPORTS],
        "tool-log": [[str(datetime.now()), tool_name]]
    }
    # TODO: add package metadata in preamble
    assert asttype == ASTTYPE_FTN
    return [[preamble(name), module]
            for name, module in file_spec[tok.ATTR_MODULES].items()]

# if __name__ == "__main__":
#     import pprint

#     doc = load_file('../test/typelib/Tst.ftn')
#     pprint.pprint(doc)
