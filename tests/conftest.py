import os
import pytest
from dataclasses import replace
from typing import Dict, List

from itsybitsy.charlotte import CrawlStrategy
from itsybitsy.charlotte_web import Protocol
from itsybitsy.node import Node


@pytest.fixture
def args_mock(mocker):
    return mocker.patch('itsybitsy.constants.ARGS', autospec=True)


@pytest.fixture
def dummy_protocol_ref():
    return 'DUM'


@pytest.fixture
def crawl_strategy_fixture() -> CrawlStrategy:
    return CrawlStrategy('', '', None, '', {}, {}, {}, {})


@pytest.fixture
def protocol_fixture(dummy_protocol_ref) -> Protocol:
    return Protocol(dummy_protocol_ref, '', True, False)


@pytest.fixture
def node_fixture_factory(crawl_strategy_fixture, protocol_fixture) -> callable:
    def _factory() -> Node:
        nonlocal crawl_strategy_fixture, protocol_fixture
        crawl_strategy_fixture = replace(crawl_strategy_fixture, protocol=protocol_fixture)
        return Node(
            address='1.2.3.4',
            crawl_strategy=crawl_strategy_fixture,
            protocol=protocol_fixture,
            protocol_mux='dummy_mux',
            provider='dummy_provider',
            from_hint=False
        )
    return _factory


@pytest.fixture
def node_fixture(node_fixture_factory) -> Node:
    return node_fixture_factory()


@pytest.fixture
def tree(node_fixture, args_mock) -> Dict[str, Node]:
    seed_noderef = 'dummy'
    tree = {seed_noderef: node_fixture}
    args_mock.seeds = [seed_noderef]

    return tree


@pytest.fixture()
def charlotte_d(tmp_path, mocker) -> str:
    """Return temp charlotte dir {str}, also making tmp dir on the filesystem and patching globals.CHARLOTTE_DIR
    autouse=True so that this is mocked out for all module tests
    """
    charlotte_d = os.path.join(tmp_path, 'charlotte.d')
    os.mkdir(charlotte_d)
    mocker.patch('itsybitsy.charlotte.constants.CHARLOTTE_DIR', charlotte_d)

    return charlotte_d


@pytest.fixture
def builtin_providers() -> List[str]:
    return ['ssh', 'k8s', 'aws']
