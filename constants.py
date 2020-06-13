"""
Globals shared across modules
"""

import pprint

# independent constants
ARGS = None
CHARLOTTE_DIR = 'charlotte.d'
COMMAND_CRAWL = 'crawl'
COMMAND_LOAD_JSON = 'load-json'
CRAWL_TIMEOUT = 30
OUTPUTS_DIR = 'outputs'
PROVIDER_SSH = 'ssh'
PROVIDER_HINT = 'hnt'
PROVIDER_SEED = 'seed'
PP = pprint.PrettyPrinter(indent=4)
SAMPLES_DIR = 'sample_outputs'

# dependent constants
LASTRUN_FILE = f"{SAMPLES_DIR}/.lastrun.json"
