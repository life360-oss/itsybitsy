import os
import pytest
import yaml
from dataclasses import replace

from itsybitsy import charlotte


# CrawlStrategy()
class TestCrawlStrategy:
    # def filter_service_name()
    @pytest.mark.parametrize('service_name,expected', [('foo', True), ('baz', False)])
    def test_filter_service_name_case_not_filter(self, crawl_strategy_fixture, service_name, expected):
        """Services are filtered if they are blacklisted by a 'not' filter"""
        # arrange
        sn_filter = {'not': ['foo']}
        crawl_strategy_fixture = replace(crawl_strategy_fixture, service_name_filter=sn_filter)

        # act/assert
        assert crawl_strategy_fixture.filter_service_name(service_name) == expected

    @pytest.mark.parametrize('service_name,expected', [('foo', False), ('bar', False), ('baz', True)])
    def test_filter_service_case_name_only_filter(self, crawl_strategy_fixture, service_name, expected):
        """Services are filtered if they are not whitelisted by an 'only' filter"""
        # arrange
        sn_filter = {'only': ['foo', 'bar']}
        crawl_strategy_fixture = replace(crawl_strategy_fixture, service_name_filter=sn_filter)

        # act/assert
        assert crawl_strategy_fixture.filter_service_name(service_name) == expected

    # determine_child_provider()
    def test_determine_child_provider_case_match_all(self, crawl_strategy_fixture):
        """Child provider determined correctly for type: 'matchAll'"""
        # arrange
        provider = 'foo'
        cp = {
            'type': 'matchAll',
            'provider': provider
        }
        crawl_strategy_fixture = replace(crawl_strategy_fixture, child_provider=cp)

        # act/assert
        assert crawl_strategy_fixture.determine_child_provider('dummy') == provider

    @pytest.mark.parametrize('port,provider', [('1234', 'abc'), (5678, 'efg')])
    def test_determine_child_provider_case_match_port(self, crawl_strategy_fixture, port, provider):
        """Child provider determined correctly per port for type: 'matchPort'"""
        # arrange
        cp = {
            'type': 'matchPort',
            'matches': {
                int(port): provider
            }
        }
        crawl_strategy_fixture = replace(crawl_strategy_fixture, child_provider=cp)

        # act/assert
        assert crawl_strategy_fixture.determine_child_provider(port) == provider

    @pytest.mark.parametrize('address, provider', [('foo', 'bar'), ('1.2.3.4', 'baz'),
                                                   ('asdf-a7h5f8cndfy-74hf6', 'buzz'), ('asdf', 'qux')])
    def test_determine_child_provider_case_match_address(self, crawl_strategy_fixture, address, provider):
        """Child provider determined correctly per address for type: 'matchAddress'"""
        # arrange
        cp = {
            'type': 'matchAddress',
            'matches': {
                '^foo$': 'bar',
                '^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$': 'baz',
                '^.*[0-9a-z]{10}-[0-9a-z]{5}$': 'buzz',
                '.*': 'qux'
            }
        }
        crawl_strategy_fixture = replace(crawl_strategy_fixture, child_provider=cp)

        # act/assert
        assert crawl_strategy_fixture.determine_child_provider('dummy_mux', address) == provider

    def test_determine_child_provider_case_null_address(self, crawl_strategy_fixture):
        """Child provider determined correctly for type: 'matchAddress' with address == None"""
        # arrange
        provider = 'foo'
        cp = {
            'type': 'matchAddress',
            'matches': {
                '.*': provider
            }
        }
        crawl_strategy_fixture = replace(crawl_strategy_fixture, child_provider=cp)

        # act/assert
        assert crawl_strategy_fixture.determine_child_provider('dummy_mux', None) == provider

    # rewrite_service_name()
    def test_rewrite_service_name_case_no_rewrite(self, crawl_strategy_fixture, node_fixture):
        """Do not rewrite service name if not configured as such"""
        # arrange
        crawl_strategy_fixture = replace(crawl_strategy_fixture, service_name_rewrites={})

        # act/assert
        assert 'foo' == crawl_strategy_fixture.rewrite_service_name('foo', node_fixture)

    def test_rewrite_service_name_case_noninterpolated_rewrite(self, crawl_strategy_fixture, node_fixture):
        """Rewrite service name - simple scenario with no interpolations"""
        # arrange
        rewrites = {'foo': 'bar'}
        crawl_strategy_fixture = replace(crawl_strategy_fixture, service_name_rewrites=rewrites)

        # act/assert
        assert 'bar' == crawl_strategy_fixture.rewrite_service_name('foo', node_fixture)

    def test_rewrite_service_name_case_interpolated_rewrite(self, crawl_strategy_fixture, node_fixture):
        """Rewrite service name with interpolations"""
        # arrange
        rewrites = {'foo': 'bar-$protocol_mux'}
        crawl_strategy_fixture = replace(crawl_strategy_fixture, service_name_rewrites=rewrites)
        node_fixture = replace(node_fixture, protocol_mux='baz')

        # act/assert
        assert 'bar-baz' == crawl_strategy_fixture.rewrite_service_name('foo', node_fixture)


# init()
def test_init_case_spins_charlotte_web(charlotte_d, mocker):
    """Charlotte.init() spins up charlotte_web"""
    # `charlotte_d` referenced in test signature only for patching of the tmp dir - fixture unused in test function
    # arrange
    spin_up_func = mocker.patch('itsybitsy.charlotte.charlotte_web.spin_up')

    # act
    charlotte.init()

    # assert
    spin_up_func.assert_called()


def test_init_case_wellformed_crawlstrategy_yaml(charlotte_d, cli_args_mock, mocker):
    """Charlotte loads a well formed crawl_strategy from yaml into memory"""
    # `charlotte_d` referenced in test signature only for patching of the tmp dir - fixture unused in test function
    # arrange
    name, description, providers, protocol, provider_args, child_provider, filter, rewrites = (
        'Foo', 'Foo CrawlStrategy', ['bar'], 'BAZ', {'command': 'uptime'}, {'type': 'matchAll', 'provider': 'buz'},
        {'only': ['foo-service']}, {'ugly-foo': 'pretty-foo'}
    )
    cli_args_mock.skip_protocols = []
    stub_protocol = mocker.patch('itsybitsy.charlotte_web.Protocol', ref=protocol)
    mocker.patch('itsybitsy.charlotte.charlotte_web.spin_up')
    get_protocol_func = mocker.patch('itsybitsy.charlotte.charlotte_web.get_protocol', return_value=stub_protocol)
    fake_crawl_strategy_yaml = f"""
---
type: "CrawlStrategy"
name: "{name}"
description: "{description}"    
{yaml.dump({'providers': providers})}
protocol: "{protocol}"
{yaml.dump({'providerArgs': provider_args})}
{yaml.dump({'childProvider': child_provider})}
{yaml.dump({'serviceNameFilter': filter})}
{yaml.dump({'serviceNameRewrites': rewrites})}
"""
    fake_crawl_strategy_yaml_file = os.path.join(charlotte_d, 'Foo.yaml')
    with open(fake_crawl_strategy_yaml_file, 'w') as f:
        f.write(fake_crawl_strategy_yaml)

    # act
    charlotte.init()

    # assert
    assert 1 == len(charlotte.crawl_strategies)
    parsed_cs = charlotte.crawl_strategies[0]
    assert name == parsed_cs.name
    assert description == parsed_cs.description
    assert providers == parsed_cs.providers
    assert stub_protocol == parsed_cs.protocol
    assert provider_args == parsed_cs.provider_args
    assert child_provider == parsed_cs.child_provider
    assert filter == parsed_cs.service_name_filter
    assert rewrites == parsed_cs.service_name_rewrites
    get_protocol_func.assert_called_once_with('BAZ')
