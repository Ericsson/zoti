from json import JSONEncoder

from yaml import Dumper

from zoml.core import Pos, Ref, TreePath


class ZotiDumper(Dumper):
    def repr_pos(self, pos):
        rep = [
            pos.start_line,
            pos.start_column,
            pos.start_index,
            pos.end_index,
            pos.path,
        ]
        return self.represent_sequence("tag:yaml.org,2002:seq", rep)

    def repr_ref(self, refpath):
        rep = {"module": refpath.module}
        if isinstance(refpath.path, TreePath):
            rep["path"] = str(refpath.path)
        else:
            rep["name"] = refpath.path
        return self.represent_mapping("tag:yaml.org,2002:map", rep)

    def repr_str(self, data):
        if "\n" in data:
            return self.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return self.represent_scalar("tag:yaml.org,2002:str", data)


ZotiDumper.add_representer(Pos, ZotiDumper.repr_pos)
ZotiDumper.add_representer(Ref, ZotiDumper.repr_ref)
ZotiDumper.add_representer(str, ZotiDumper.repr_str)


class ZotiEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Pos):
            return [obj.start_line, obj.start_column, obj.start_index,
                    obj.end_index, obj.path,]
        elif isinstance(obj, Ref):
            if isinstance(obj.path, TreePath):
                return {"module": obj.module, "path": str(obj.path)}
            else:
                return {"module": obj.module, "name": obj.path}
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, obj)
