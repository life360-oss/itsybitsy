# Copyright # Copyright 2020 Life360, Inc
# SPDX-License-Identifier: Apache-2.0

from graphviz import Digraph
from typing import Dict

from . import constants, render_helpers
from .node import Node

nodes_compiled = {}
edges_compiled = []
dot = None


def render_tree(tree: Dict[str, Node], source: bool = False) -> None:
    """
    Render tree in graphviz.  Will write an image file to disk and then open it.  Optionally write dot source

    :param tree:
    :param source: render output as graphviz source code (dot)
    :return:
    """
    global dot
    dot = Digraph()
    dot.node_attr['shape'] = 'box'
    dot.graph_attr['dpi'] = '300'
    dot.graph_attr['rankdir'] = _determine_rankdir()
    for node_ref, node in tree.items():
        _compile_digraph(node_ref, node)
    if source:
        print(dot.source)
    else:
        dot.subgraph()
        seed_names = ','.join([node.service_name for node in tree.values() if node.service_name is not None])
        seeds = seed_names or ','.join(constants.ARGS.seeds).replace('.', '-')
        dot.render(f"itsy-prettsy_{seeds}", directory=constants.OUTPUTS_DIR, view=True, format='png', cleanup=True)

    # clear cache - i am not sure if this is needed any more and was likely due to a user error on my part - pk
    global nodes_compiled, edges_compiled
    nodes_compiled = {}
    edges_compiled = []


def _determine_rankdir() -> str:
    if constants.GRAPHVIZ_RANKDIR_AUTO != constants.ARGS.render_graphviz_rankdir:
        return constants.ARGS.render_graphviz_rankdir

    return _determine_auto_rankdir()


def _determine_auto_rankdir() -> str:
    if constants.ARGS.skip_nonblocking_grandchildren:
        return constants.GRAPHVIZ_RANKDIR_LEFT_TO_RIGHT

    return constants.GRAPHVIZ_RANKDIR_TOP_TO_BOTTOM


def _compile_digraph(node_ref: str, node: Node, blocking_from_top: bool = True) -> None:
    node_name = _node_name(node, node_ref)
    _compile_node(node, node_name, blocking_from_top)
    # child
    if node.children:
        merged_children = render_helpers.merge_hints(node.children)
        for child_ref, child in merged_children.items():
            child: Node
            # defunct
            if child.warnings.get('DEFUNCT') and constants.ARGS.hide_defunct:
                continue
            # child blocking, name
            child_blocking_from_top = blocking_from_top and child.protocol.blocking
            child_name = _node_name(child, child_ref)
            # child node
            _compile_node(child, child_name, child_blocking_from_top)
            # child edge
            _compile_edge(node_name, child, child_name, child_blocking_from_top)
            # recurse
            _compile_digraph(child_ref, child, child_blocking_from_top)


def _compile_edge(parent_name: str, child: Node, child_name: str, child_blocking_from_top: bool) -> None:
    parent_or_child_is_highlighted = constants.ARGS.render_graphviz_highlight_services and \
                                     True in [name in [parent_name, child_name] for
                                              name in constants.ARGS.render_graphviz_highlight_services]
    edge_str = f"{parent_name}.{child.protocol.ref}.{child_name}"
    if edge_str not in edges_compiled:
        defunct = child.warnings.get('DEFUNCT')
        edge_style = 'bold' if child_blocking_from_top else ''
        edge_style += ',dashed' if not child.protocol.blocking else ''
        edge_style += ',dotted,filled' if defunct else ''
        edge_color = 'red' if child.errors else 'darkorange' if defunct else ''
        edge_color += ':blue' if child.from_hint else ''
        edge_color += 'yellow:black:yellow' if parent_or_child_is_highlighted else ''
        edge_weight = '3' if defunct or child.from_hint else None
        errs_warns = ','.join({**child.errors, **child.warnings, **({'HINT': True} if child.from_hint else {})})
        label = f"{child.protocol.ref}{' (' + errs_warns + ')' if errs_warns else ''}"
        dot.edge(parent_name, child_name, label, style=edge_style, color=edge_color,
                 penwidth=edge_weight)
        edges_compiled.append(edge_str)


def _compile_node(node: Node, name: str, blocking_from_top: bool) -> None:
    if name not in nodes_compiled or blocking_from_top and not nodes_compiled[name].get('blocking_from_top'):
        style = 'bold' if blocking_from_top else None
        shape = 'cylinder' if node.is_database() else 'septagon' if node.containerized else None
        color = 'red' if node.errors else 'darkorange' if node.warnings else None
        dot.node(name, shape=shape, style=style, color=color)
        nodes_compiled[name] = {'blocking_from_top': blocking_from_top}


def _node_name(node: Node, node_ref: str) -> str:
    name = node.service_name or f"UNKNOWN\n({node_ref})"
    return render_helpers.clean_service_name(name)