import pytest

from itsybitsy import providers, node


@pytest.fixture(autouse=True)
def disable_builtin_providers(builtin_providers, cli_args_mock):
    cli_args_mock.disable_providers=builtin_providers


@pytest.fixture
def provider_interface():
    return providers.ProviderInterface()


class TestProviderInterface:
    @pytest.mark.asyncio
    async def test_open_connection(self, provider_interface):
        """Default behavior of provider is an acceptable return of None for connection.  It is optional"""
        # arrange/act/assert
        assert await provider_interface.open_connection('dummy') is None

    @pytest.mark.asyncio
    async def test_lookup_name(self, provider_interface):
        """Default behavior of provider is an acceptable return of None for name lookup.  It is optional"""
        # arrange/act/assert
        assert await provider_interface.lookup_name('dummy', None) is None

    @pytest.mark.asyncio
    async def test_take_a_hint(self, provider_interface, mocker):
        """Default behavior of provider is an acceptable return of [] for hint taking.  It is optional"""
        # arrange
        mock_hint = mocker.patch('itsybitsy.charlotte_web.Hint')

        # act/assert
        assert [] == await provider_interface.take_a_hint(mock_hint)

    @pytest.mark.asyncio
    async def test_crawl_downstream(self, provider_interface):
        """Default behavior of provider is an acceptable return of [] for crawling.  It is optional"""

        # arrange/act/assert
        assert [] == await provider_interface.crawl_downstream('dummy', None)


def test_init_case_builtin_providers_disableable(cli_args_mock, builtin_providers, mocker):
    # arrange
    cli_args_mock.disable_providers = builtin_providers

    # act/assert
    providers.register_providers()
    for provider in builtin_providers:
        with pytest.raises(SystemExit) as e_info:
            providers.get_provider_by_ref(provider)
        assert 1 == e_info.value.code


@pytest.mark.parametrize('crawl_strategy_response', ['', 'foo bar'])
def test_parse_crawl_strategy_response_case_no_data_lines(crawl_strategy_response):
    # arrange/act/assert
    assert providers.parse_crawl_strategy_response(crawl_strategy_response, '', '') == []


def test_parse_crawl_strategy_response_case_no_mux():
    # arrange
    protocol_mux = 'foo'
    crawl_strategy_response = f"address\n{protocol_mux}"
    expected = [node.NodeTransport(protocol_mux)]

    # act/assert
    with pytest.raises(providers.CreateNodeTransportException):
        providers.parse_crawl_strategy_response(crawl_strategy_response, '', '')


def test_parse_crawl_strategy_response_case_mux_only():
    # arrange
    protocol_mux = 'foo'
    crawl_strategy_response = f"mux\n{protocol_mux}"
    expected = [node.NodeTransport(protocol_mux)]

    # act/assert
    assert providers.parse_crawl_strategy_response(crawl_strategy_response, '', '') == expected


def test_parse_crawl_strategy_response_case_all_fields():
    # arrange
    metadata_1_key, metadata_1_val = 'pet', 'dog'
    mux, address, id, conns, metadata = 'foo', 'bar', 'baz', '100', f'{metadata_1_key}={metadata_1_val}'
    crawl_strategy_response = f"mux address id conns metadata\n" \
                              f"{mux} {address} {id} {conns} {metadata}"
    expected = [node.NodeTransport(mux, address, id, int(conns), {metadata_1_key: metadata_1_val})]

    # act/assert
    assert providers.parse_crawl_strategy_response(crawl_strategy_response, '', '') == expected























