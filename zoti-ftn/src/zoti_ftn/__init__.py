from importlib.metadata import distribution

dist = distribution("zoti_ftn")

__version__ = dist.version
