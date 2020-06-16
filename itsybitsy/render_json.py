import json
from dataclasses import asdict, is_dataclass
from typing import Dict

from . import constants
from .charlotte import CrawlStrategy
from .charlotte_web import Protocol
from .node import Node


class _EnhancedJSONEncoder(json.JSONEncoder):
    """Dataclass objects to not have native support for JSON serialization. This class allows for that"""
    def default(self, o):  # pylint: disable=method-hidden
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)


def _deserialize_object(dct: dict):
    """Used to json deserialization to our custom classes"""
    dct_type = dct.get('__type__')
    if not dct_type:
        return dct

    if 'Node' == dct_type:
        return Node(**dct)
    elif 'CrawlStrategy' == dct_type:
        return CrawlStrategy(**dct)
    elif 'Protocol' == dct_type:
        return Protocol(**dct)

    raise Exception(f"Unrecognized __type__: ({dct_type}) encountered during json deserialization")


def load(file):
    """
    load json rendering of tree from `file`, parse requisite outputs

    :param file:
    :return:
    """
    loaded = json.load(open(file), object_hook=_deserialize_object)
    constants.ARGS.max_depth = int(loaded['args']['max_depth'])
    constants.ARGS.skip_nonblocking_grandchildren = loaded['args']['skip_nonblocking_grandchildren']

    return loaded['tree']


def dump(tree: Dict[str, Node], file: str = None) -> None:
    """
    dump json of the tree to a file - includes globals.ARGS in the dump
    :param tree:
    :param file:
    :return:
    """
    tree_with_args = _add_cli_args_to_json_tree(tree)
    with open(file, 'w+') as file_handle:
        json.dump(tree_with_args, file_handle, cls=_EnhancedJSONEncoder)


def dumps(tree: Dict[str, Node]) -> None:
    """
    dump json of the tree to the screen
    :param tree:
    :return:
    """
    tree_with_args = _add_cli_args_to_json_tree(tree)
    print(json.dumps(tree_with_args, cls=_EnhancedJSONEncoder))


def _add_cli_args_to_json_tree(tree: Dict[str, Node]) -> dict:
    return {
        'args': vars(constants.ARGS),
        'tree': tree
    }
