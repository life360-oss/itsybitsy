from itsybitsy import constants, node, renderers
from typing import Dict


class RendererPPrint(renderers.RendererInterface):
    @staticmethod
    def ref() -> str:
        return 'pprint'

    def render(self, tree: Dict[str, node.Node]):
        constants.PP.pprint(tree)
