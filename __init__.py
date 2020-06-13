import importlib
import pkgutil

from .node import Node
from .charlotte import CS_SEED as CRAWL_STRATEGY_SEED
from .charlotte_web import PROTOCOL_SEED
from itsybitsy import itsybitsy_plugins

__all__ = ['Node', 'CRAWL_STRATEGY_SEED', 'PROTOCOL_SEED']

# load plugins
for finder, name, ispkg in pkgutil.iter_modules(itsybitsy_plugins.__path__, itsybitsy_plugins.__name__ + "."):
    importlib.import_module(name)
