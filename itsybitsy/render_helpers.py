from typing import Dict

from itsybitsy.node import Node


def merge_hints(nodes: Dict[str, Node]) -> Dict[str, Node]:
    """
    Merge a regular nodes and hint nodes by protocol and protocol mux (multiplexer).  If there are 2 nodes in the input
    that have share the same protocol and protocol_mux, and one is from a Hint - merge them together so that they are
    displayed as one edge.

    :param nodes:
    :return:
    """
    hints = {_protocol_and_mux(node): (node_ref, node)
             for node_ref, node in nodes.items() if node.from_hint}
    if 0 == len(hints):
        return nodes

    not_hints = {node_ref: node for node_ref, node in nodes.items() if not node.from_hint}
    used_hints = []
    merged_nodes = {ref: node for ref, node in not_hints.items() if _protocol_and_mux(node) not in hints}
    mergeable_nodes = {ref: node for ref, node in not_hints.items() if _protocol_and_mux(node) in hints}
    for node_ref, node in mergeable_nodes.items():
        protocol_and_mux = _protocol_and_mux(node)
        merged_node = _merge_node_and_hint(node, hints[protocol_and_mux][1])
        merged_nodes[node_ref] = merged_node
        used_hints.append(protocol_and_mux)
    unused_hints = {ref: node for ref, node in nodes.items() if f"{node.protocol.ref}.{node.protocol_mux}"
                    not in used_hints}
    merged_nodes.update(unused_hints)

    return merged_nodes


def _merge_node_and_hint(node: Node, hint: Node) -> Node:
    node.from_hint = True
    node.address = node.address or hint.address
    node.containerized = node.containerized or hint.containerized
    node.service_name = node.service_name or hint.service_name
    node.warnings = {**node.warnings, **hint.warnings}
    node.errors = {**node.errors, **hint.errors}
    node_children = node.children or {}
    hint_children = hint.children or {}
    node.children = {**hint_children, **node_children}

    return node


def _protocol_and_mux(node: Node) -> str:
    return f"{node.protocol.ref}.{node.protocol_mux}"


def clean_service_name(name: str) -> str:
    return name.replace('"', '').replace(':', '_').replace('#', '_')