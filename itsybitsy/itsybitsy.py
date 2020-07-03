__version__ = "0.0.3"

import asyncio
import argparse
import configargparse
import logging
import os
import signal
import sys
from contextlib import contextmanager
from termcolor import colored
from typing import Dict, Optional

from . import plugins
from . import charlotte, charlotte_web, constants, crawl, logs, node, providers, render_ascii, render_graphviz, \
    render_json


# module globals
command_spider = 'spider'
command_render = 'render'

# python3 check
REQUIRED_PYTHON_VERSION = (3, 8)
def tuple_join(the_tuple):
    return '.'.join(str(i) for i in the_tuple)


if sys.version_info[0] < REQUIRED_PYTHON_VERSION[0] or sys.version_info[1] < REQUIRED_PYTHON_VERSION[1]:
    print(f"Python version {tuple_join(sys.version_info[:2])} detected. This script requires Python version >= "
          f"{tuple_join(REQUIRED_PYTHON_VERSION)} available at `/usr/bin/env python3`")
    sys.exit(1)

# catch ctrl-c
signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))


argparser: Optional[configargparse.ArgParser] = None
spider_subparser: Optional[configargparse.ArgParser] = None


@contextmanager
def suppress_console_out():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def parse_builtin_args() -> (configargparse.Namespace, list):
    class ConciseHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
        """Custom formatter to reduce redundancy in Help Display Output"""
        def _format_action_invocation(self, action):
            if not action.option_strings or action.nargs == 0:
                return super()._format_action_invocation(action)
            # we only care about `-s ARGS, --long ARGS`
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            return ', '.join(action.option_strings) + ' ' + args_string
    formatter_class = lambda prog: ConciseHelpFormatter(prog, max_help_position=100, width=200)
    global argparser, spider_subparser
    argparser = configargparse.ArgumentParser(
        description=(
            "Give it (a) seed host(s).\n"
            "It will crawl them.\n"
            "And climb.\n"
            "The waterspout.\n\n"
        )
    )
    # subparsers
    subparsers = argparser.add_subparsers(
        help='Please select an acceptable command for itsybitsy: "spider" or "render"'
    )
    subparsers.required = True
    subparsers.dest = 'command'
    spider_p = subparsers.add_parser(command_spider, help='Crawl a network of services - given a seed',
                                     formatter_class=formatter_class, default_config_files=['./spider.conf'])
    render_p = subparsers.add_parser(command_render, help='Render results of a previous crawl',
                                     formatter_class=formatter_class)
    spider_subparser = spider_p

    render_choices = ['ascii', 'pprint', 'json', 'graphviz', 'graphviz_source']
    # add common opts to each sub parser
    for sub_p in subparsers.choices.values():
        # common args
        sub_p.add_argument('-D', '--hide-defunct', action='store_true', help='Hide defunct (unused) connections')
        sub_p.add_argument('-o', '--output', action='append', choices=render_choices,
                           help='Format in which to output the final graph.  Available options: '
                                f"[{','.join(render_choices)}]")
        sub_p.add_argument('--render-ascii-verbose', action='store_true', help='Verbose mode for ascii renderer')
        sub_p.add_argument('--render-graphviz-rankdir', choices=[constants.GRAPHVIZ_RANKDIR_LEFT_TO_RIGHT,
                                                                 constants.GRAPHVIZ_RANKDIR_TOP_TO_BOTTOM,
                                                                 constants.GRAPHVIZ_RANKDIR_AUTO],
                           default=constants.GRAPHVIZ_RANKDIR_AUTO,
                           help='Layout director, or "rankdir" for graphviz diagram.  '
                                f"{constants.GRAPHVIZ_RANKDIR_LEFT_TO_RIGHT} = \"Left-to-Right\", "
                                f"{constants.GRAPHVIZ_RANKDIR_TOP_TO_BOTTOM}=\"Top-to-Bottom\", "
                                f"\"{constants.GRAPHVIZ_RANKDIR_AUTO}\" automatically renders for best orientation")
        sub_p.add_argument('--render-graphviz-highlight-services', nargs='+', metavar='SERVICE',
                           help='A list of services to highlight in graphviz.')
        sub_p.add_argument('--debug', action='store_true', help='Log debug output to stderr')

    # crawl command args
    spider_p.add_argument('-s', '--seeds', required=True, nargs='+', metavar='SEED',
                          help='Seed host(s) to begin crawling viz. an IP address or hostname.  Must be in the format: '
                               '"provider:address".  e.g. "ssh:10.0.0.42" or "k8s:widget-machine-5b5bc8f67f-2qmkp')
    spider_p.add_argument('-d', '--max-depth', type=int, default=100, metavar='DEPTH', help='Max tree depth to crawl')
    spider_p.add_argument('-c', '--config-file', is_config_file=True, metavar='FILE', help='Specify a config file path')
    spider_p.add_argument('-X', '--disable-providers', nargs='+', default=[], metavar='PROVIDER',
                          help="Do not initialize or crawl with these providers")
    spider_p.add_argument('-P', '--skip-protocols', nargs='+', default=[], metavar='PROTOCOL',
                          help='A list of protocols to skip.  e.g. "NSQ PXY"')
    spider_p.add_argument('-M', '--skip-protocol-muxes', nargs='+', default=[], metavar='MUX',
                          help='Skip crawling for children on services with these '
                               'names (name lookup will still happen)')
    spider_p.add_argument('-G', '--skip-nonblocking-grandchildren', action='store_true',
                          help='Skip crawling of nonblocking children unless they '
                               'are direct children of the seed nodes')
    spider_p.add_argument('-x', '--obfuscate', action='store_true',
                          help="Obfuscate graph details.  Useful for sharing rendered output outside of "
                               "trusted organizations.")
    spider_p.add_argument('-q', '--quiet', action='store_true',
                          help='Do not render graph output to stdout while crawling')

    # render command args
    render_p.add_argument('-f', '--json-file', metavar='FILE',
                          help='Instead of crawling, load and render a json serialization of the tree')

    return argparser.parse_known_args()


async def crawl_water_spout():
    """Crawl all the services.  It will render live ascii to stderr as it crawls unless --quiet is specified"""
    # --quiet
    outfile = open(os.devnull, 'w') if constants.ARGS.quiet else sys.stderr

    # build the tree of seeds
    tree = {
        f"SEED:{address}":
            node.Node(
                crawl_strategy=charlotte.SEED_CRAWL_STRATEGY,
                protocol=charlotte_web.PROTOCOL_SEED,
                protocol_mux='seed',
                provider=provider,
                containerized=providers.get(provider).is_container_platform(),
                from_hint=False,
                address=address
            )
        for provider, address in [seed.split(':') for seed in constants.ARGS.seeds]
    }

    # compile async tasks
    tasks = [
        crawl.crawl(tree, []),
        render_ascii.render_tree(tree, [], out=outfile, print_slowly_for_humans=True)
    ]
    # NOTE: render_tree must be run to /dev/null even on --quiet
    #  in order to wait for crawl to complete before returning

    await asyncio.gather(*tasks)

    return tree


def _create_outputs_directory_if_absent():
    if not os.path.exists(constants.OUTPUTS_DIR):
        os.makedirs(constants.OUTPUTS_DIR)


def render(tree: Dict[str, node.Node]) -> None:
    if constants.ARGS.output:
        if 'pprint' in constants.ARGS.output:
            constants.PP.pprint(tree)
        if 'ascii' in constants.ARGS.output:
            asyncio.get_event_loop().run_until_complete(render_ascii.render_tree(tree, [], sys.stdout))
        if 'json' in constants.ARGS.output:
            render_json.dumps(tree)
        if 'graphviz' in constants.ARGS.output:
            render_graphviz.render_tree(tree)
        if 'graphviz_source' in constants.ARGS.output:
            render_graphviz.render_tree(tree, True)


def main():
    # plugins
    plugins.load_plugins()

    # args
    try:
        with suppress_console_out():
            constants.ARGS, _ = parse_builtin_args()
    except SystemExit:
        # this is done in order to display custom plugin level arguments in --help script output
        providers.parse_provider_args(spider_subparser)
        argparser.parse_known_args()

    # --debug
    if constants.ARGS.debug:
        logs.logger.setLevel(logging.DEBUG)

    # initialize charlotte
    charlotte.init()

    # hello
    print(f"Hello, {os.getlogin()}", file=sys.stderr)

    # render OR spider
    _create_outputs_directory_if_absent()
    if command_render == constants.ARGS.command:
        constants.ARGS = argparser.parse_args()
        if not constants.ARGS.output:
            constants.ARGS.output = ['ascii']
        tree = render_json.load(constants.ARGS.json_file or constants.LASTRUN_FILE)
        render(tree)
    elif command_spider == constants.ARGS.command:
        providers.parse_provider_args(spider_subparser)
        constants.ARGS = argparser.parse_args()
        providers.init()
        tree = asyncio.get_event_loop().run_until_complete(crawl_water_spout())
        render_json.dump(tree, constants.LASTRUN_FILE)
        render(tree)
    else:
        # This code path should be unreachable since argparse will constrain which command can be executed
        print(colored(f"Invalid command: {constants.ARGS.command}.  Please file bug with maintainer.", 'red'))
        sys.exit(1)

    # g'bye
    print(f"\nGoodbye, {os.getlogin()}\n", file=sys.stderr)
