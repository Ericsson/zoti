from yaml import SafeDumper
from dataclasses import dataclass
from zoti_graph import Uid

class Ref:
    ref: str
    
    def __init__(self, ref):
        self.ref = {"name": f"{ref}"}

@dataclass
class PolInter:
    obj: list

@dataclass
class PolUnion:
    obj: list
    
@dataclass
class Default:
    obj: list

@dataclass
class Incl:
    incl: str
    
class SpecDumper(SafeDumper):
    # def represent_data(self, data):
    #     print(data)
    #     return super(SpecDumper, self).represent_data(data)
    
    def repr_ref(self, ref):
        return self.represent_mapping("!ref", ref.ref)

    def repr_default(self, df):
        return self.represent_sequence("!default", df.obj)
    
    def repr_policy_intersect(self, wc):
        return self.represent_sequence("!policy:intersect", wc.obj)

    def repr_policy_union(self, wc):
        return self.represent_sequence("!policy:union", wc.obj)
    
    def repr_incl(self, incl):
        return self.represent_scalar("!include", str(incl.incl))
    
    def repr_uid(self, uid):
        return self.represent_scalar("tag:yaml.org,2002:str", repr(uid))



SpecDumper.add_representer(Ref, SpecDumper.repr_ref)
SpecDumper.add_representer(Default, SpecDumper.repr_default)
SpecDumper.add_representer(Incl, SpecDumper.repr_incl)
SpecDumper.add_representer(PolInter, SpecDumper.repr_policy_intersect)
SpecDumper.add_representer(PolUnion, SpecDumper.repr_policy_union)
