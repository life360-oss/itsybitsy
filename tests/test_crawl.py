"""
Notes:
    - `lookup_name` is stubbed with a dummy return value for many tests - because `crawl` will not (should not) proceed
        to the `crawl_downstream` portion of crawling if a name is not returned by `lookup_name`
    - "cs_mock" fixture is passed to many tests here and appears unused.  however it is a required fixture for tests
        to be valid since the fixture code itself will patch the crawl_strategy object into the code flow in the test
"""
from itsybitsy import crawl, node
from itsybitsy.providers import TimeoutException

import asyncio
import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear crawl.py caches between tests - otherwise our asserts for function calls may not pass"""
    crawl.service_name_cache = {}
    crawl.child_cache = {}


@pytest.fixture(autouse=True)
def set_default_timeout(builtin_providers, cli_args_mock):
    cli_args_mock.timeout = 30


@pytest.fixture
def mock_provider_ref() -> str:
    return 'mock_provider'


@pytest.fixture
def provider_mock(mocker, mock_provider_ref) -> MagicMock:
    provider_mock = mocker.patch('itsybitsy.providers.ProviderInterface', autospec=True)
    provider_mock.ref.return_value = mock_provider_ref
    mocker.patch('itsybitsy.providers.get', return_value=provider_mock)

    return provider_mock


@pytest.fixture
def cs_mock(protocol_fixture, mocker, mock_provider_ref) -> MagicMock:
    """it is a required fixture to include, whether or not it is used explicitly, in or to mock crawl_downstream"""
    cs_mock = mocker.patch('itsybitsy.charlotte.CrawlStrategy', autospec=True)
    mocker.patch('itsybitsy.charlotte.crawl_strategies', [cs_mock])
    cs_mock.rewrite_service_name.side_effect = lambda x, y: x
    cs_mock.filter_service_name.return_value = False
    cs_mock.protocol = protocol_fixture
    cs_mock.provider_args = {}
    cs_mock.providers = [mock_provider_ref]

    return cs_mock


@pytest.fixture
def protocol_mock(mocker, dummy_protocol_ref) -> MagicMock:
    protocol_mock = mocker.patch('itsybitsy.charlotte_web.Protocol')
    protocol_mock.ref = dummy_protocol_ref

    return protocol_mock


@pytest.fixture
def hint_mock(protocol_fixture, mocker) -> MagicMock:
    hint_mock = mocker.patch('itsybitsy.charlotte_web.Hint', autospec=True)
    hint_mock.instance_provider = 'dummy_hint_provider'
    hint_mock.protocol = protocol_fixture
    mocker.patch('itsybitsy.charlotte_web.hints', [hint_mock])

    return hint_mock


@pytest.fixture(autouse=True)
def set_default_cli_args(cli_args_mock):
    cli_args_mock.obfuscate = False


# helpers
async def _wait_for_all_tasks_to_complete(event_loop):
    """Wait for all tasks to complete in the event loop. Assumes that 1 task will remain incomplete - and that
    is the task for the async `test_...` function itself"""
    while len(asyncio.all_tasks(event_loop)) > 1:
        await asyncio.sleep(0.1)  # we "fire and forget" in crawl() and so have to "manually" "wait"


# Calls to ProviderInterface::open_connection
@pytest.mark.asyncio
async def test_crawl_case_connection_opened_and_passed(tree, provider_mock, cs_mock):
    """Crawling a single node tree - connection is opened and passed to both lookup_name and crawl_downstream"""
    # arrange
    # mock provider
    stub_connection = 'foo_connection'
    provider_mock.open_connection.return_value = stub_connection
    provider_mock.lookup_name.return_value = 'bar_name'
    # mock crawl strategy
    stub_provider_args = {'baz': 'buz'}
    cs_mock.provider_args = stub_provider_args
    cs_mock.providers = [provider_mock.ref()]

    # act
    await crawl.crawl(tree, [])

    # assert
    provider_mock.open_connection.assert_called_once_with(list(tree.values())[0].address)
    provider_mock.lookup_name.assert_called_once_with(list(tree.values())[0].address, stub_connection)
    provider_mock.crawl_downstream.assert_called_once_with(list(tree.values())[0].address, stub_connection,
                                                           **stub_provider_args)


@pytest.mark.asyncio
async def test_crawl_case_open_connection_handles_timeout_exception(tree, provider_mock, cs_mock):
    """Respects the contractual TimeoutException or ProviderInterface.  If thrown we set TIMEOUT error
    but do not stop crawling"""
    # arrange
    provider_mock.open_connection.side_effect = TimeoutException

    # act
    await crawl.crawl(tree, [])

    assert 'TIMEOUT' in list(tree.values())[0].errors
    provider_mock.lookup_name.assert_not_called()
    provider_mock.crawl_downstream.assert_not_called()


@pytest.mark.asyncio
async def test_crawl_case_open_connection_handles_timeout(tree, provider_mock, cs_mock, cli_args_mock, mocker):
    """A natural timeout during ProviderInterface::open_connections is also handled by setting TIMEOUT error"""
    # arrange
    cli_args_mock.timeout = .1

    async def slow_open_connection(address):
        await asyncio.sleep(1)
    provider_mock.open_connection.side_effect = slow_open_connection

    # act
    await crawl.crawl(tree, [])

    assert 'TIMEOUT' in list(tree.values())[0].errors
    provider_mock.lookup_name.assert_not_called()
    provider_mock.crawl_downstream.assert_not_called()


@pytest.mark.asyncio
async def test_crawl_case_open_connection_handles_exceptions(tree, provider_mock, cs_mock):
    """Handle any other exceptions thrown by ProviderInterface::open_connection by exiting the program"""
    # arrange
    provider_mock.open_connection.side_effect = Exception('BOOM')

    # act/assert
    with pytest.raises(SystemExit):
        await crawl.crawl(tree, [])


# Calls to ProviderInterface::lookup_name
@pytest.mark.asyncio
async def test_crawl_case_lookup_name_uses_cache(tree, node_fixture_factory, provider_mock):
    """Validate the calls to lookup_name for the same address are cached"""
    # arrange
    address = 'use_this_address_twice'
    node2 = node_fixture_factory()
    node2.address = address
    tree['dummy2'] = node2
    list(tree.values())[0].address = address

    # act
    await crawl.crawl(tree, [])

    # assert
    provider_mock.lookup_name.assert_called_once()


@pytest.mark.asyncio
async def test_crawl_case_lookup_name_handles_timeout(tree, provider_mock, cs_mock, cli_args_mock, mocker):
    """Timeout is handled during lookup_name and results in a sys.exit"""
    # arrange
    cli_args_mock.timeout = .1

    async def slow_lookup_name(address):
        await asyncio.sleep(1)
    provider_mock.lookup_name = slow_lookup_name

    # act/assert
    with pytest.raises(SystemExit):
        await crawl.crawl(tree, [])


@pytest.mark.asyncio
async def test_crawl_case_lookup_name_handles_exceptions(tree, provider_mock, cs_mock):
    """Any exceptions thrown by lookup_name are handled by exiting the program"""
    # arrange
    provider_mock.lookup_name.side_effect = Exception('BOOM')

    # act/assert
    with pytest.raises(SystemExit):
        await crawl.crawl(tree, [])


# Calls to ProviderInterface::crawl_downstream
@pytest.mark.asyncio
@pytest.mark.parametrize('name,crawl_expected,error', [(None, False, 'NAME_LOOKUP_FAILED'), ('foo', True, None)])
async def test_crawl_case_crawl_downstream_based_on_name(name, crawl_expected, error, tree, provider_mock, cs_mock):
    """Depending on whether provider.name_lookup() returns a name - we should or should not crawl_downstream()"""
    # arrange
    provider_mock.lookup_name.return_value = name
    cs_mock.providers = [provider_mock.ref()]

    # act
    await crawl.crawl(tree, [])

    # assert
    assert provider_mock.crawl_downstream.called == crawl_expected
    if error:
        assert error in list(tree.values())[0].errors


@pytest.mark.asyncio
@pytest.mark.parametrize('attr', ['warnings', 'errors'])
async def test_crawl_case_do_not_crawl_downstream_node_with_warns_errors(attr, tree, provider_mock, cs_mock):
    """We should not crawl_downstream for node with any arbitrary warning or error"""
    # arrange
    provider_mock.lookup_name.return_value = 'dummy_name'
    setattr(list(tree.values())[0], attr, {'DUMMY': True})

    # act
    await crawl.crawl(tree, [])

    # assert
    provider_mock.crawl_downstream.assert_not_called()


@pytest.mark.asyncio
async def test_crawl_case_crawl_downstream_uses_cache(tree, node_fixture_factory, provider_mock, cs_mock, event_loop):
    """Validate the calls to crawl_downstream for the same address are cached.  Caching is only guaranteed for
    different branches in the tree since siblings execute concurrently - and so we have to test a tree with more
    depth > 1"""
    # arrange
    repeated_service_name = 'double_name'
    singleton_service_name = 'single_name'
    node2 = node_fixture_factory()
    node2.address = 'foo'  # must be different than list(tree.values())[0].address to avoid caching
    node2_child = node.NodeTransport('foo_mux', 'bar_address')
    tree['dummy2'] = node2
    provider_mock.lookup_name.side_effect = [repeated_service_name, singleton_service_name, repeated_service_name]
    provider_mock.crawl_downstream.side_effect = [[], [node2_child], []]
    cs_mock.providers = [provider_mock.ref()]

    # act
    await crawl.crawl(tree, [])
    await _wait_for_all_tasks_to_complete(event_loop)

    # assert
    assert 2 == provider_mock.crawl_downstream.call_count


@pytest.mark.asyncio
async def test_crawl_case_crawl_downstream_handles_timeout(tree, provider_mock, cs_mock, cli_args_mock, mocker):
    """Timeout is respected during crawl_downstream and results in a sys.exit"""
    # arrange
    cli_args_mock.timeout = .1

    async def slow_crawl_downstream(address, connection):
        await asyncio.sleep(1)
    provider_mock.lookup_name.return_value = 'dummy'
    provider_mock.crawl_downstream.side_effect = slow_crawl_downstream
    cs_mock.providers = [provider_mock.ref()]

    # act/assert
    with pytest.raises(SystemExit) as e:
        await crawl.crawl(tree, [])

    assert True


@pytest.mark.asyncio
async def test_crawl_case_crawl_downstream_handles_exceptions(tree, provider_mock, cs_mock, cli_args_mock, mocker):
    """Any exceptions thrown by crawl_downstream are handled by exiting the program"""
    # arrange
    cli_args_mock.timeout = .1
    provider_mock.lookup_name.return_value = 'dummy'
    provider_mock.open_connection.side_effect = Exception('BOOM')

    # act/assert
    with pytest.raises(SystemExit):
        await crawl.crawl(tree, [])


# handle Cycles
@pytest.mark.asyncio
async def test_crawl_case_cycle(tree, provider_mock, cs_mock):
    """Cycles should be detected, name lookup should still happen for them, but crawl_downstream should not"""
    # arrange
    cycle_service_name = 'foops_i_did_it_again'
    provider_mock.lookup_name.return_value = cycle_service_name

    # act
    await crawl.crawl(tree, [cycle_service_name])

    # assert
    assert 'CYCLE' in list(tree.values())[0].warnings
    provider_mock.lookup_name.assert_called_once()
    provider_mock.crawl_downstream.assert_not_called()


@pytest.mark.asyncio
async def test_crawl_case_service_name_rewrite_cycle_detected(tree, provider_mock, cs_mock):
    """Validate cycles are detected for rewritten service names"""
    # arrange
    cycle_service_name = 'foops_i_did_it_again'
    provider_mock.lookup_name.return_value = 'original_service_name'
    list(tree.values())[0].crawl_strategy = cs_mock
    cs_mock.rewrite_service_name.side_effect = None
    cs_mock.rewrite_service_name.return_value = cycle_service_name

    # act
    await crawl.crawl(tree, [cycle_service_name])

    # assert
    assert 'CYCLE' in list(tree.values())[0].warnings


# Parsing of ProviderInterface::crawl_downstream
@pytest.mark.asyncio
@pytest.mark.parametrize('protocol_mux,address,debug_identifier,num_connections,warnings,errors', [
    ('foo_mux', 'bar_address', 'baz_name', 100, [], []),
    ('foo_mux', 'bar_address', 'baz_name', None, [], []),
    ('foo_mux', 'bar_address', None, None, [], []),
    ('foo_mux', 'bar_address', 'baz_name', 0, ['DEFUNCT'], []),
    ('foo_mux', None, None, None, [], ['NULL_ADDRESS']),
])
async def test_crawl_case_crawl_results_parsed(protocol_mux, address, debug_identifier, num_connections, warnings, errors,
                                               tree, provider_mock, cs_mock, event_loop):
    """Crawl results are parsed into Node objects.  We detect 0 connections as a "DEFUNCT" node.  `None` address
    is acceptable, but is detected as a "NULL_ADDRESS" node"""
    # arrange
    seed = list(tree.values())[0]
    child_nt = node.NodeTransport(protocol_mux, address, debug_identifier, num_connections)
    provider_mock.lookup_name.side_effect = ['seed_name', 'child_name']
    provider_mock.crawl_downstream.side_effect = [[child_nt], []]
    cs_mock.providers = [provider_mock.ref()]

    # act
    await crawl.crawl(tree, [])
    await _wait_for_all_tasks_to_complete(event_loop)

    # assert
    assert 1 == len(seed.children)
    child: node.Node = seed.children[list(seed.children)[0]]
    assert protocol_mux == child.protocol_mux
    assert address == child.address
    for warning in warnings:
        assert warning in child.warnings
    for error in errors:
        assert error in child.errors


# Recursive calls to crawl::crawl()
@pytest.mark.asyncio
async def test_crawl_case_children_with_address_crawled(tree, provider_mock, cs_mock, event_loop, mocker):
    """Discovered children with an address are recursively crawled """
    # arrange
    child_nt = node.NodeTransport('dummy_protocol_mux', 'dummy_address')
    provider_mock.lookup_name.side_effect = ['seed_name', 'child_name']
    provider_mock.crawl_downstream.side_effect = [[child_nt], []]
    cs_mock.providers = [provider_mock.ref()]
    crawl_spy = mocker.patch('itsybitsy.crawl.crawl', side_effect=crawl.crawl)

    # act
    await crawl.crawl(tree, [])
    await _wait_for_all_tasks_to_complete(event_loop)

    # assert
    assert 2 == crawl_spy.call_count
    child_node = crawl_spy.await_args.args[0][list(crawl_spy.await_args.args[0])[0]]
    assert 'dummy_address' == child_node.address
    assert list(tree.values())[0].service_name == crawl_spy.await_args.args[1][0]


@pytest.mark.asyncio
async def test_crawl_case_children_without_address_not_crawled(tree, provider_mock, cs_mock, event_loop,
                                                               mocker):
    """Discovered children without an address are not recursively crawled """
    # arrange
    child_nt = node.NodeTransport('dummy_protocol_mux', None)
    provider_mock.lookup_name.return_value = 'dummy'
    provider_mock.crawl_downstream.return_value = [child_nt]
    crawl_spy = mocker.patch('itsybitsy.crawl.crawl', side_effect=crawl.crawl)

    # act
    await crawl.crawl(tree, [])
    await _wait_for_all_tasks_to_complete(event_loop)

    # assert
    assert 1 == crawl_spy.call_count


# Hints
@pytest.mark.asyncio
async def test_crawl_case_hint_attributes_set(tree, provider_mock, hint_mock, mocker, event_loop):
    """For hints used in crawling... attributes are correctly translated from the Hint the Node"""
    # arrange
    mocker.patch('itsybitsy.charlotte_web.hints', return_value=[hint_mock])
    hint_nt = node.NodeTransport('dummy_protocol_mux', 'dummy_address', 'dummy_debug_id')
    provider_mock.take_a_hint.return_value = [hint_nt]
    provider_mock.lookup_name.side_effect = ['dummy', None]
    providers_get_mock = mocker.patch('itsybitsy.providers.get', return_value=provider_mock)

    # act
    await crawl.crawl(tree, [])
    await _wait_for_all_tasks_to_complete(event_loop)

    # assert
    assert list(list(tree.values())[0].children.values())[0].from_hint
    assert list(list(tree.values())[0].children.values())[0].protocol == hint_mock.protocol
    assert list(list(tree.values())[0].children.values())[0].service_name == hint_nt.debug_identifier
    providers_get_mock.assert_any_call(hint_mock.instance_provider)


@pytest.mark.asyncio
async def test_crawl_case_hint_name_used(tree, provider_mock, hint_mock, mocker, event_loop):
    """Hint `debug_identifier` field is respected in crawling (and overwritten by new name, not overwritten by None)"""
    # arrange
    mocker.patch('itsybitsy.charlotte_web.hints', return_value=[hint_mock])
    hint_nt = node.NodeTransport('dummy_protocol_mux', 'dummy_address', 'dummy_debug_id')
    provider_mock.take_a_hint.return_value = [hint_nt]
    provider_mock.lookup_name.side_effect = ['dummy', None]

    # act
    await crawl.crawl(tree, [])
    await _wait_for_all_tasks_to_complete(event_loop)

    # assert
    assert list(list(tree.values())[0].children.values())[0].service_name == hint_nt.debug_identifier


# respect CLI args
@pytest.mark.asyncio
async def test_crawl_case_respect_cli_skip_protocol_mux(tree, provider_mock, cs_mock, cli_args_mock,
                                                        mocker, event_loop):
    """Children discovered on these muxes are neither included in the tree - nor crawled"""
    # arrange
    skip_this_protocol_mux = 'foo_mux'
    cli_args_mock.skip_protocol_muxes = [skip_this_protocol_mux]
    child_nt = node.NodeTransport(skip_this_protocol_mux, 'dummy_address')
    provider_mock.lookup_name.return_value = 'bar_name'
    provider_mock.crawl_downstream.return_value = [child_nt]
    crawl_spy = mocker.patch('itsybitsy.crawl.crawl', side_effect=crawl.crawl)

    # act
    await crawl.crawl(tree, [])
    await _wait_for_all_tasks_to_complete(event_loop)

    # assert
    assert 0 == len(list(tree.values())[0].children)
    assert 1 == crawl_spy.call_count


@pytest.mark.asyncio
async def test_crawl_case_respect_cli_skip_protocols(tree, provider_mock, cs_mock, cli_args_mock, mocker):
    """Crawling of protocols configured to be "skipped" does not happen at all."""
    # arrange
    skip_this_protocol = 'FOO'
    cli_args_mock.skip_protocols = [skip_this_protocol]
    cs_mock.protocol = mocker.patch('itsybitsy.charlotte_web.Protocol', autospec=True)
    cs_mock.protocol.ref = skip_this_protocol
    provider_mock.lookup_name.return_value = 'bar_name'

    # act
    await crawl.crawl(tree, [])
    # assert
    provider_mock.crawl_downstream.assert_not_called()


@pytest.mark.asyncio
async def test_crawl_case_respect_cli_disable_providers(tree, provider_mock, cs_mock, cli_args_mock, mocker,
                                                        event_loop):
    """Children discovered which have been determined to use disabled providers - are neither included in the tree
    nor crawled"""
    # arrange
    disable_this_provider = 'foo_provider'
    cli_args_mock.disable_providers = [disable_this_provider]
    child_nt = node.NodeTransport('dummy_mux', 'dummy_address')
    provider_mock.lookup_name.return_value = 'bar_name'
    provider_mock.crawl_downstream.return_value = [child_nt]
    cs_mock.determine_child_provider.return_value = disable_this_provider
    crawl_spy = mocker.patch('itsybitsy.crawl.crawl', side_effect=crawl.crawl)

    # act
    await crawl.crawl(tree, [])
    await _wait_for_all_tasks_to_complete(event_loop)

    # assert
    assert 0 == len(list(tree.values())[0].children)
    assert 1 == crawl_spy.call_count


@pytest.mark.asyncio
@pytest.mark.parametrize('child_blocking,grandchild_blocking,crawls_expected,downstream_crawls_expected',
                         [(False, False, 2, 1), (True, False, 2, 2)])
async def test_crawl_case_respect_cli_skip_nonblocking_grandchildren(child_blocking, grandchild_blocking,
                                                                     crawls_expected, downstream_crawls_expected,
                                                                     tree, provider_mock, protocol_mock, cs_mock,
                                                                     cli_args_mock, mocker, event_loop):
    """When --skip-nonblocking-grandchildren is specified, include nonblocking children of the seed, but nowhere else"""
    # arrange
    cli_args_mock.skip_nonblocking_grandchildren = True
    child_nt = node.NodeTransport('dummy_protocol_mux', 'dummy_address')
    grandchild_nt = node.NodeTransport('dummy_protocol_mux_gc', 'dummy_address_gc')
    provider_mock.lookup_name.side_effect = ['seed_name', 'child_name', 'grandchild_name']
    provider_mock.crawl_downstream.side_effect = [[child_nt], [grandchild_nt], []]
    type(protocol_mock).blocking = mocker.PropertyMock(side_effect=[True, child_blocking, grandchild_blocking])
    cs_mock.protocol = protocol_mock
    crawl_spy = mocker.patch('itsybitsy.crawl.crawl', side_effect=crawl.crawl)

    # act
    await crawl.crawl(tree, [])
    await _wait_for_all_tasks_to_complete(event_loop)

    # assert
    assert crawl_spy.call_count == crawls_expected
    assert provider_mock.crawl_downstream.call_count == downstream_crawls_expected


@pytest.mark.asyncio
async def test_crawl_case_respect_cli_max_depth(tree, node_fixture, provider_mock, cs_mock, cli_args_mock):
    """We should not crawl_downstream if max-depth is exceeded"""
    # arrange
    cli_args_mock.max_depth = 0
    provider_mock.lookup_name.return_value = 'dummy_name'

    # act
    await crawl.crawl(tree, [])

    # assert
    provider_mock.crawl_downstream.assert_not_called()


@pytest.mark.asyncio
async def test_crawl_case_respect_cli_obfuscate(tree, node_fixture, cs_mock, provider_mock, cli_args_mock):
    """We need to test a child for protocol mux obfuscation since the tree is already populated with a fully hydrated
        Node - which is past the point of obfuscation"""
    # arrange
    cli_args_mock.obfuscate = True
    seed_service_name = 'actual_service_name_foo'
    child_protocol_mux = 'child_actual_protocol_mux'
    child_nt = node.NodeTransport(child_protocol_mux)
    provider_mock.lookup_name.return_value = seed_service_name
    provider_mock.lookup_name.return_value = 'dummy_service_name'
    provider_mock.crawl_downstream.side_effect = [[child_nt], []]
    cs_mock.providers = [provider_mock.ref()]

    # act
    await crawl.crawl(tree, [])

    # assert
    seed: node.Node = list(tree.values())[0]
    child: node.Node = seed.children[list(seed.children)[0]]
    assert seed.service_name != seed_service_name
    assert child.protocol_mux != child_protocol_mux


# respect charlotte / charlotte_web configurations
@pytest.mark.asyncio
async def test_crawl_case_respect_cs_filter_service_name(tree, provider_mock, cs_mock):
    """We respect when a service name is configured to be skipped by a specific crawl strategy"""
    # arrange
    cs_mock.filter_service_name.return_value = True
    provider_mock.lookup_name.return_value = 'bar_name'

    # act
    await crawl.crawl(tree, [])

    # assert
    cs_mock.filter_service_name.assert_called_once_with(list(tree.values())[0].service_name)
    provider_mock.crawl_downstream.assert_not_called()


@pytest.mark.asyncio
async def test_crawl_case_respect_cs_service_name_rewrite(tree, provider_mock, cs_mock):
    """Validate service_name_rewrites are called and used"""
    # arrange
    service_name = 'foo_name'
    rewritten_service_name = 'bar_name'
    provider_mock.lookup_name.return_value = service_name
    list(tree.values())[0].crawl_strategy = cs_mock
    cs_mock.rewrite_service_name.side_effect = None
    cs_mock.rewrite_service_name.return_value = rewritten_service_name

    # act
    await crawl.crawl(tree, [])

    # assert
    assert list(tree.values())[0].service_name == rewritten_service_name


@pytest.mark.asyncio
async def test_crawl_case_respect_charlotte_web_skip(tree, provider_mock, cs_mock, mocker):
    """Skip service name is respected for charlotte_web"""
    # arrange
    service_name = 'foo_name'
    provider_mock.lookup_name.return_value = service_name
    skip_function = mocker.patch('itsybitsy.charlotte_web.skip', return_value=True)

    # act
    await crawl.crawl(tree, [])

    # assert
    provider_mock.lookup_name.assert_called_once()
    provider_mock.crawl_downstream.assert_not_called()
    skip_function.assert_called_once_with(service_name)
