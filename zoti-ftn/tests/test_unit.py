import os
import sys
import yaml
from glob import glob
from pprint import pprint
import pytest
import logging

sys.path.insert(0, "src")

from zoti_ftn.lang import load_str, load_file
import zoti_ftn.core as core
import zoti_ftn.backend.c as c

from pprint import pformat

@pytest.fixture
def ftn(request):
    docs = [doc for f in glob("tests/inputs/*.ftn") for doc in load_file(open(f))]
    single = request.param.FtnDb({doc[0]["module"]: doc[1]["entries"] for doc in docs})
    return single


@pytest.mark.parametrize('ftn', [core], indirect=True)
def test_core(ftn) -> None:
    print("")
    try:
        struct_types = ftn.get("Tst.TypeOne").select_types(of_class="array")
        assert len(ftn.loaded_types()) == 2
        assert struct_types[0].element_type.bit_size.value == 8
        assert struct_types[0].element_type.normalize_value("TRUE")
        assert not struct_types[0].element_type.normalize_value(False)
        assert 10 in struct_types[0].range
        assert struct_types[0].range.size() == 100
        x = ftn.parse(load_str("integer(range: 1..100; bit-size: 16; endian: big)"))
        # pprint(x)
        x.set_readonly(True)
        assert x.readonly
        assert x.normalize_value(1000) is None
        assert x.normalize_value("asdf") is None
        assert x.normalize_value("10") == 10
        
        y = ftn.get("Tst.TypeTwo").derefer()
        assert 10 not in y.range
        assert ftn.dump("test_import.ArrId")
    except Exception as e:
        raise e
    finally:
        core.FtnDb.clear_instance()


@pytest.mark.parametrize('ftn', [c], indirect=True)
def test_c_backend(ftn) -> None:
    print("")
    try:
        # print(ftn)
        _ = ftn.get("Tst.TypeOne")
        _ = ftn.get("Tst.TypeTwo")
        assert ftn.gen_typename_expr(core.Uid("Tst.TypeOne")) == "Tst__TypeOne_t"
        assert ftn.gen_typename_expr(core.Uid("Tst.TypeTwo")) == "Tst__TypeTwo_t"
        assert ftn.requirements()
        for t in [core.Entry(uid, value="y")
                  for uid in ["Tst.TypeOne", "Tst.TypeTwo",
                              "test_import.TimeSlot", "test_import.ArrId"]]:
            assert ftn.gen_typedef(t, allow_void=True)
            assert ftn.gen_access_macros_expr(t)
            assert ftn.gen_access_macros_expr(t, read_only=True)
            assert ftn.access_dict(t)
            assert ftn.gen_decl(t, "x")
            assert ftn.gen_decl(t, "x", usage="z")
            if ftn.get(t).need_malloc():
                assert ftn.get(t).gen_ctor("x", "y", ptr_fixup=True)
                assert ftn.get(t).gen_desctor("x", "y")
                assert ftn.get(t).gen_marshal("x", "y")
                assert ftn.get(t).gen_unmarshal("x", "y")
            assert ftn.get(t).gen_copy("x", "y", "z", "q")
            assert ftn.get(t).gen_size_expr("x")
    except Exception as e:
        raise e
    finally:
        c.FtnDb.clear_instance()
