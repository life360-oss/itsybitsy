import importlib
import pkgutil
from . import itsybitsy_plugins


def load_plugins():
    for _, name, _ in pkgutil.iter_modules(itsybitsy_plugins.__path__, itsybitsy_plugins.__name__ + "."):
        importlib.import_module(name)
