from enum import EnumMeta
from functools import update_wrapper, wraps
from marshmallow import post_load


def with_schema(schema_base_class):
    def Inner(cls):
        @wraps(cls, updated=())
        class Wrapper:
            
            def __init__(self, *args, **kwargs):
                self.wrap = cls(*args, **kwargs)
                self.cls = cls
                self.__doc__ = cls.__doc__
                self.__name__ = cls.__name__
                self.__bases__ = cls.__bases__
                
            class Schema(schema_base_class):
                @post_load
                def construct(self, data, **kwargs):
                    return cls(**data)
                
        # Wrapper.__doc__ = cls.__doc__
        return Wrapper

    return Inner



class SearchableEnum(EnumMeta):
    def __contains__(cls, item):
        try:
            cls[item.upper()]
        except KeyError:
            return False
        return True

    def __getitem__(cls, item):
        return super(SearchableEnum, cls).__getitem__(item.upper())


def uniqueName(name, namespace):
    if not namespace or name not in namespace:
        return name
    it = 0
    while f"name_{it}"  in namespace:
        it+=1
    return f"name_{it}"
