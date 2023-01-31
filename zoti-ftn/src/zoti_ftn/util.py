from enum import EnumMeta

from marshmallow import post_load


def with_schema(schema_base_class):
    def Inner(cls):
        class Wrapper:
            def __init__(self, *args, **kwargs):
                self.wrap = cls(*args, **kwargs)

            class Schema(schema_base_class):
                @post_load
                def construct(self, data, **kwargs):
                    return cls(**data)

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


