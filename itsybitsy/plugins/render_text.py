from itsybitsy import node, renderers
from typing import Dict

flat_relationships = {}


class RendererGraphvizSource(renderers.RendererInterface):
    @staticmethod
    def ref() -> str:
        return 'text'

    def render(self, tree: Dict[str, node.Node]):
        render_tree(tree)


def render_tree(tree: Dict[str, node.Node]) -> None:
    for tree_node in tree.values():
        build_flat_services(tree_node)

    for relationship in sorted(flat_relationships):
        print(relationship)


def build_flat_services(tree_node: node.Node) -> None:
    if not tree_node.children:
        return

    for child in tree_node.children.values():
        relationship = f"{tree_node.service_name or 'UNKNOWN'} --[{child.protocol.ref}]--> " \
                       f"{child.service_name or 'UNKNOWN'} ({child.protocol_mux})"
        if relationship not in flat_relationships:
            flat_relationships[relationship] = (tree_node, child)
        build_flat_services(child)