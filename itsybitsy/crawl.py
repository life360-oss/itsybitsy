# Copyright # Copyright 2020 Life360, Inc
# SPDX-License-Identifier: Apache-2.0

"""
The high level async, recursive crawling functionality of itsybitsy/spider.
"""
import asyncio
import sys
import traceback

from dataclasses import replace
from termcolor import colored
from typing import Dict, List, Optional, Tuple

from . import charlotte, charlotte_web, constants, logs, obfuscate, providers
from .charlotte import CrawlStrategy
from .node import Node, NodeTransport

service_name_cache: Dict[str, Optional[str]] = {}  # {address: service_name}
child_cache: Dict[str, Dict[str, Node]] = {}  # {service_name: {node_ref, Node}}


async def crawl(tree: Dict[str, Node], ancestors: list):
    depth = len(ancestors)
    logs.logger.debug(f"Found {str(len(tree))} nodes to crawl at depth: {depth}")

    conns, tree = await _open_connections(tree, ancestors)
    service_names, conns = await _lookup_service_names(tree, conns)
    await _assign_names_and_detect_cycles(tree, service_names, ancestors)

    if len(ancestors) > constants.ARGS.max_depth - 1:
        logs.logger.debug(f"Reached --max-depth of {constants.ARGS.max_depth} at depth: {depth}")
        return

    nodes_with_conns = [(item[0], item[1], conn) for item, conn in zip(tree.items(), conns)]
    crawlable_nodes = [(ref, node, conn) for ref, node, conn in nodes_with_conns if node.is_crawlable(depth)]
    await _find_children_and_recursively_crawl(tree, crawlable_nodes, depth, ancestors)


async def _find_children_and_recursively_crawl(tree: Dict[str, Node], crawlable_nodes: List[Tuple[str, Node, type]],
                                               depth: int, ancestors: list):
    crawl_tasks = [_crawl_with_hints(tree[ref].provider, ref, node.address, node.service_name, conn)
                   for ref, node, conn in crawlable_nodes]
    while len(crawl_tasks) > 0:
        children_results, children_pending_tasks = await asyncio.wait(crawl_tasks, return_when=asyncio.FIRST_COMPLETED)
        for future in children_results:
            node_ref, children = _get_crawl_result_with_exception_handling(future)
            child_depth = depth + 1
            nonexcluded_children = {ref: child for ref, child in children.items() if not child.is_excluded(child_depth)}
            tree[node_ref].children = nonexcluded_children
            children_with_address = {ref: child for ref, child in nonexcluded_children.items() if child.address}
            if children_with_address:
                asyncio.ensure_future(crawl(children_with_address, ancestors + [tree[node_ref].service_name]))
        crawl_tasks = children_pending_tasks


async def _assign_names_and_detect_cycles(tree: Dict[str, Node], service_names: str, ancestors: list):
    for node_ref, service_name in zip(list(tree), service_names):
        if not service_name:
            logs.logger.debug(f"Name lookup failed for {node_ref} with address: {tree[node_ref].address}")
            service_name_cache[tree[node_ref].address] = None
            tree[node_ref].errors['NAME_LOOKUP_FAILED'] = True
            continue
        service_name = tree[node_ref].crawl_strategy.rewrite_service_name(service_name, tree[node_ref])
        if constants.ARGS.obfuscate:
            service_name = obfuscate.obfuscate_service_name(service_name)
        if service_name in ancestors:
            tree[node_ref].warnings['CYCLE'] = True
        tree[node_ref].service_name = service_name


def _get_crawl_result_with_exception_handling(future: asyncio.Future) -> (str, Dict[str, Node]):
    try:
        return future.result()
    except TimeoutError:
        sys.exit(1)
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        sys.exit(1)


async def _open_connections(tree: Dict[str, Node], ancestors: List[str]) -> (list, Dict[str, Node]):
    """
    We use sys.exit() to ensure the entire program is halted and not simply the individual task in which an exception
    was raised.
    """
    # open optional provider connections
    conns = await asyncio.gather(
        *[asyncio.wait_for(
            _open_connection(node.address, providers.get(node.provider)), constants.CRAWL_TIMEOUT
        ) for node_ref, node in tree.items()],
        return_exceptions=True
    )
    # handle exceptions
    exceptions = [(ref, e) for ref, e in zip(list(tree), conns) if isinstance(e, Exception)]
    for node_ref, e in exceptions:
        if isinstance(e, (providers.TimeoutException, asyncio.TimeoutError)):
            logs.logger.debug(f"Connection timeout when attempting to connect to {node_ref} with address: "
                              f"{tree[node_ref].address}")
            tree[node_ref].errors['TIMEOUT'] = True
        else:
            child_of = f"child of {ancestors[len(ancestors)-1]}" if len(ancestors) > 0 else ''
            print(colored(f"Exception {e.__class__.__name__} occurred opening connection for {node_ref}, "
                          f"{tree[node_ref].address} {child_of}", 'red'))
            traceback.print_tb(e.__traceback__)
            sys.exit(1)

    # reset conns/tree excluding TimeoutExceptions so that we can zip()
    clean_tree = {item[0]: item[1] for item, conn in zip(tree.items(), conns) if not isinstance(conn, Exception)}
    clean_conns = [conn for conn in conns if not isinstance(conn, Exception)]

    return clean_conns, clean_tree


async def _open_connection(address: str, provider: providers.ProviderInterface):
    if address in service_name_cache:
        if service_name_cache[address] is None:
            logs.logger.debug(f"Not opening connection: name is None ({address}")
            return None
        if charlotte_web.skip(service_name_cache[address]):
            logs.logger.debug(f"Not opening connection: skip ({service_name_cache[address]})")
            return None
        if service_name_cache[address] in child_cache:
            logs.logger.debug(f"Not opening connections: cached ({service_name_cache[address]})")
            return None

    logs.logger.debug(f"Opening connection: {address}")
    return await provider.open_connection(address)


async def _lookup_service_names(tree: Dict[str, Node], conns: list) -> (List[str], list):
    # lookup_name / detect cycles
    service_names = await asyncio.gather(
        *[asyncio.wait_for(
            _lookup_service_name(node.address, providers.get(node.provider), conn),
            constants.CRAWL_TIMEOUT) for node, conn in zip(tree.values(), conns)],
        return_exceptions=True
    )

    # handle exceptions
    exceptions = [(ref, e) for ref, e in zip(list(tree), service_names) if isinstance(e, Exception)]
    for node_ref, e in exceptions:
        if isinstance(e, asyncio.TimeoutError):
            print(colored(f"Timeout during name lookup for {node_ref}:", 'red'))
            print(colored({**vars(tree[node_ref]), 'crawl_strategy': tree[node_ref].crawl_strategy.name}, 'yellow'))
            traceback.print_tb(e.__traceback__)
            sys.exit(1)
        else:
            traceback.print_tb(e.__traceback__)
            sys.exit(1)

    return service_names, conns


async def _lookup_service_name(address: str, provider: providers.ProviderInterface,
                               connection: type) -> Optional[str]:
    if address in service_name_cache:
        logs.logger.debug(f"Using cached service name ({service_name_cache[address]} for: {address}")
        return service_name_cache[address]

    logs.logger.debug(f"Getting service name for address {address}")
    service_name = await provider.lookup_name(address, connection)
    logs.logger.debug(f"Discovered name: {service_name} for address {address}")
    service_name_cache[address] = service_name

    return service_name


async def _crawl_with_hints(provider_ref: str, node_ref: str, address: str, service_name: str,
                            connection: type) -> (str, Dict[str, Node]):
    if service_name in child_cache:
        logs.logger.debug(f"Found {len(child_cache[service_name])} children in cache for:{service_name}")
        # we must to this copy to avoid various contention and infinite recursion bugs
        return node_ref, {r: replace(n, children={}, warnings=n.warnings.copy(), errors=n.errors.copy())
                          for r, n in child_cache[service_name].items()}

    logs.logger.debug(f"Crawling with charlotte/web for {node_ref}")
    tasks, crawl_strategies = _compile_crawl_tasks_and_crawl_strategies(address, service_name,
                                                                        providers.get(provider_ref), connection)

    # if there are any timeouts or exceptions, panic and run away! we don't want an incomplete graph to look complete
    crawl_results = await asyncio.gather(*tasks, return_exceptions=True)
    crawl_exceptions = [e for e in crawl_results if isinstance(e, Exception)]
    if crawl_exceptions:
        if isinstance(crawl_exceptions[0], asyncio.TimeoutError):
            print(colored(f"Timeout when attempting to crawl service: {service_name}, node_ref: {node_ref}", 'red'))
            print(colored(f"Connection object: {connection}:", 'yellow'))
            print(colored(vars(connection), 'yellow'))
        raise crawl_exceptions[0]

    # parse returned NodeTransport objects to Node objects
    children = {}
    for node_transports, crawl_strategy in [(nts, cs) for nts, cs in zip(crawl_results, crawl_strategies) if nts]:
        for node_transport in node_transports:
            # skip if configured
            if _skip_protocol_mux(node_transport.protocol_mux):
                continue
            child_ref, child = _create_node(crawl_strategy, node_transport)
            children[child_ref] = child
    logs.logger.debug(f"Found {len(children)} children for {service_name}")
    child_cache[service_name] = children

    return node_ref, children


def _compile_crawl_tasks_and_crawl_strategies(address: str, service_name: str, provider: providers.ProviderInterface,
                                              connection: type) -> (List[callable], List[CrawlStrategy]):
    tasks = []
    crawl_strategies: List[CrawlStrategy] = []

    # charlotte
    for cs in charlotte.crawl_strategies:
        if cs.protocol.ref in constants.ARGS.skip_protocols or cs.filter_service_name(service_name) \
                or provider.ref() not in cs.providers:
            continue
        crawl_strategies.append(cs)
        tasks.append(asyncio.wait_for(
            provider.crawl_downstream(address, connection, **cs.provider_args),
            timeout=constants.CRAWL_TIMEOUT
        ))

    # take hints
    for hint in [hint for hint in charlotte_web.hints(service_name)
                 if hint.instance_provider not in constants.ARGS.disable_providers]:
        hint_provider = providers.get(hint.instance_provider)
        tasks.append(asyncio.wait_for(hint_provider.take_a_hint(hint), timeout=constants.CRAWL_TIMEOUT))
        crawl_strategies.append(
            replace(
                charlotte.HINT_CRAWL_STRATEGY,
                child_provider={'type': 'matchAll', 'provider': hint.provider},
                protocol=hint.protocol
            )
        )

    return tasks, crawl_strategies


def _skip_protocol_mux(mux: str):
    for skip in constants.ARGS.skip_protocol_muxes:
        if skip in mux:
            return True

    return False


def _create_node(cs_used: CrawlStrategy, node_transport: NodeTransport) -> (str, Node):
    provider = cs_used.determine_child_provider(node_transport.protocol_mux, node_transport.address)
    from_hint = constants.PROVIDER_HINT in cs_used.providers
    if constants.ARGS.obfuscate:
        node_transport = obfuscate.obfuscate_node_transport(node_transport)
    node = Node(
        crawl_strategy=cs_used,
        protocol=cs_used.protocol,
        protocol_mux=node_transport.protocol_mux,
        provider=provider,
        containerized=providers.get(provider).is_container_platform(),
        from_hint=from_hint,
        address=node_transport.address,
        service_name=node_transport.debug_identifier if from_hint else None
    )

    # warnings/errors
    if not node_transport.address or 'null' == node_transport.address:
        node.errors['NULL_ADDRESS'] = True
    if 0 == node_transport.num_connections:
        node.warnings['DEFUNCT'] = True

    node_ref = '_'.join(x for x in [cs_used.protocol.ref, node_transport.protocol_mux, node_transport.debug_identifier]
                        if x is not None)
    return node_ref, node
