import configargparse
import re
import sys
from termcolor import colored
from typing import Dict, List, Optional

from . import constants
from .charlotte_web import Hint
from .node import NodeTransport


class ProviderRefNotImplemented(Exception):
    """Exception thrown if provider has not implemented ref() method"""


class TimeoutException(Exception):
    """Timeout occurred connecting to the provider"""


class ProviderClobberException(Exception):
    """An exception indicating a provider is clobbering the namespace of another provider"""


class ProviderArgParser:
    def __init__(self, prefix: str, argparser: configargparse.ArgParser):
        self._prefix = prefix
        self._argparser = argparser

    def add_argument(self, option_name: str, **kwargs):
        """
        A wrapper method on top of the classic ArgParse::add_argument().  All keyword arguments are supported, however
        only a single option_name is allowed, such as '--foo-argument'.  Argument registered here will be prepended
        with the ProviderInterface() ref in order to avoid namespace collisions between provider plugins.  For example
        '--foo-argument' registered by a ProviderInterface() with ref() = 'bar' will result in a CLI arg of
        '--bar-foo-argument'.

        :param option_name: such as '--foo-something'
        :param kwargs: pass through kwargs for ArgParse::add_argument, such as "required", "type", "nargs", etc.
        :return:
        """
        option_name = f"{self._prefix}-{option_name}"
        option_name_with_dashes_consoliated = re.sub('-+', '-', option_name)
        option_name_with_leading_dashes = f"--{option_name_with_dashes_consoliated}"
        self._argparser.add_argument(option_name_with_leading_dashes, **kwargs)


class ProviderInterface:
    @staticmethod
    def ref() -> str:
        """
        Every provider it identified by a unique "reference" or "ref" which much be declared by implemented this
        public abstract method.
        :return: the unique reference or "ref" of the provider.
        """
        raise ProviderRefNotImplemented()

    @staticmethod
    def register_cli_args(argparser: ProviderArgParser):
        """
        Each provider has a chance to register custom CLI args
        :param argparser:
        :return:
        """

    @staticmethod
    def is_container_platform() -> bool:
        """
        Optionally announce whether this provider is a container based platform (kubernetes, docker).  This is used to
        render container nodes differently than traditional servers systems.
        :return:
        """
        return False

    async def open_connection(self, address: str) -> Optional[type]:
        """
        Optionally open a connection which can then be passed into lookup_name() and crawl()

        :param address: for example, and ip address for which to open and ssh connection
        :return: mixed type object representing a connection to node in the provider
        :raises:
            TimeoutException - Timeout connecting to provider for name lookup
        """
        del address
        return None

    async def lookup_name(self, address: str, connection: Optional[type]) -> Optional[str]:
        """
        Takes and address and lookups up service name in provider.  Default response when subclassing
        will be a no-op, which allows provider subclasses to only implement aspects of this classes functionality
        a-la-cart style

        :param address: look up the name for this IP address
        :param connection: optional connection.  for example if an ssh connection was opened during
                                   lookup_name() it can be returned there and re-used here
        :return: the derived service name in string form
        :raises:
            NameLookupFailedException - Not able to find a name in the provider
        """
        del address, connection
        return None

    async def take_a_hint(self, hint: Hint) -> List[NodeTransport]:
        """
        Takes a hint, looks up an instance of service in the provider, and returns a NodeTransport representing the
        Node discovered in the Provider. Default response when subclassing will be a no-op, which allows provider
        subclasses to only implement aspects of this classes functionality a-la-cart style.
        Please return the NodeTransport object in the form of a List of 1 NodeTransport object!
        :param hint: take this hint
        :return:
        """
        del hint
        return []

    async def crawl_downstream(self, address: str, connection: Optional[type], **kwargs) -> List[NodeTransport]:
        """
        Crawl provider for downstream services using CrawlStrategy.  Default response when subclassing will be a no-op,
        which allows provider subclasses to only implement aspects of this classes functionality a-la-cart style.
        Please cache your results to improve system performance!

        :param address: address to crawl
        :param connection: optional connection.  for example if an ssh connection was opened during
                                   lookup_name() it can be returned there and re-used here
        :Keyword Arguments: extra arguments passed to provider from CrawlStrategy.provider_args

        :return: the children as a list of Node()s
        """
        del address, kwargs, connection
        return []


provider_registry:  Dict[str, ProviderInterface] = {}


def parse_provider_args(argparser: configargparse.ArgParser):
    """
    Providers are given an opportunity to register custom CLI arguments with this argparser

    :param argparser:
    :return:
    """
    for provider_class in ProviderInterface.__subclasses__():
        provider_argparser = ProviderArgParser(provider_class.ref(), argparser)
        provider_class.register_cli_args(provider_argparser)


def init():
    """
    Initialization registers each provider in the provider_registry

    :return:
    """
    for provider_class in _enabled_providers():
        if provider_class.ref() in provider_registry:
            raise ProviderClobberException(f"Provider {provider_class.ref()} already registered!")
        provider_registry[provider_class.ref()] = provider_class()


def _enabled_providers() -> List[ProviderInterface]:
    return [cls for cls in ProviderInterface.__subclasses__() if cls.ref() not in constants.ARGS.disable_providers]


def get(provider_ref: str) -> ProviderInterface:
    """
    Take a provider string reference and return a singleton instance of the provider

    :param provider_ref:
    :return:
    """
    try:
        return provider_registry[provider_ref]
    except KeyError as e:
        print(colored(f"Attempted to load invalid provider: {provider_ref}", 'red'))
        print(e, 'yellow')
        sys.exit(1)