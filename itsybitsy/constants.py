# Copyright # Copyright 2020 Life360, Inc
# SPDX-License-Identifier: Apache-2.0

"""
Globals shared across modules
"""

import pprint

# independent constants
ARGS = None
CHARLOTTE_DIR = 'charlotte.d'
CRAWL_TIMEOUT = 30
OUTPUTS_DIR = 'outputs'
PROVIDER_SSH = 'ssh'
PROVIDER_HINT = 'hnt'
PROVIDER_SEED = 'seed'
PP = pprint.PrettyPrinter(indent=4)

# dependent constants
LASTRUN_FILE = f"{OUTPUTS_DIR}/.lastrun.json"
