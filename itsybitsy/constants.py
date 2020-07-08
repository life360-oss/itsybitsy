"""
Globals shared across modules
"""

import pprint

# independent constants
ARGS = None
CHARLOTTE_DIR = 'charlotte.d'
OUTPUTS_DIR = 'outputs'
GRAPHVIZ_RANKDIR_AUTO = 'auto'
GRAPHVIZ_RANKDIR_TOP_TO_BOTTOM = 'TB'
GRAPHVIZ_RANKDIR_LEFT_TO_RIGHT = 'LR'
PROVIDER_SSH = 'ssh'
PROVIDER_HINT = 'hnt'
PROVIDER_SEED = 'seed'
PP = pprint.PrettyPrinter(indent=4)

# dependent constants
LASTRUN_FILE = f"{OUTPUTS_DIR}/.lastrun.json"
