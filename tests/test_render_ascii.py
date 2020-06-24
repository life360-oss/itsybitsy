from itsybitsy import render_ascii
from itsybitsy.node import Node

from dataclasses import replace
from typing import Dict
import asyncio
import pytest
import sys


@pytest.fixture
def tree_stubbed(tree) -> Dict[str, Node]:
    """Tree with seed node having basic attributes stubbed"""
    list(tree.values())[0].service_name = 'foo'
    list(tree.values())[0].address = '1.2.3.4'

    return tree


@pytest.fixture
def tree_stubbed_with_child(tree_stubbed, node_fixture) -> Dict[str, Node]:
    """Stubbed tree, with 1 child added with basic characteristics stubbed"""
    # arrange
    seed = tree_stubbed[list(tree_stubbed)[0]]
    child = replace(node_fixture, service_name='bar')
    child.service_name = 'baz'
    child.children = {}
    child.address = '5.6.7.8'
    seed.children = {'child_node': child}

    return tree_stubbed


@pytest.fixture(autouse=True)
def set_default_cli_args(cli_args_mock):
    cli_args_mock.render_ascii_verbose = False
    cli_args_mock.debug = False


async def _helper_render_tree_with_timeout(tree: Dict[str, Node]) -> None:
    await asyncio.wait_for(render_ascii.render_tree(tree, [], sys.stdout), .1)


@pytest.mark.asyncio
async def test_render_tree_case_seed(tree_stubbed, capsys):
    """Test a single seed node is printed correctly - no errors or edge cases"""
    # arrange
    seed = tree_stubbed[list(tree_stubbed)[0]]
    seed.children = {}

    # act
    await _helper_render_tree_with_timeout(tree_stubbed)
    captured = capsys.readouterr()

    # assert
    assert f"\n{seed.service_name} [{seed.protocol_mux}]\n" == captured.out


@pytest.mark.asyncio
async def test_render_tree_case_child(tree_stubbed_with_child, capsys):
    """Test a single child node is printed correctly - no errors or edge cases"""
    # arrange
    seed = tree_stubbed_with_child[list(tree_stubbed_with_child)[0]]
    child = seed.children[list(seed.children)[0]]

    # act
    await _helper_render_tree_with_timeout(tree_stubbed_with_child)
    captured = capsys.readouterr()

    # assert
    expected = ("\n"
                f"{seed.service_name} [{seed.protocol_mux}]\n"
                f" └--{child.protocol.ref}--> {child.service_name} [port:{child.protocol_mux}]\n")
    assert expected == captured.out


# wait_for: wait for service name to print
@pytest.mark.asyncio
async def test_render_tree_case_crawl_not_complete(tree_stubbed, capsys, mocker):
    """Render should not happen for a node unless `crawl_complete()` returns True"""
    # arrange
    seed = tree_stubbed[list(tree_stubbed)[0]]
    mocker.patch.object(seed, 'crawl_complete', return_value=False)

    # act/assert
    with pytest.raises(asyncio.TimeoutError):
        await _helper_render_tree_with_timeout(tree_stubbed)
    captured = capsys.readouterr()
    assert seed.service_name not in captured


@pytest.mark.asyncio
async def test_render_tree_case_children_namelookup_incomplete(tree_stubbed_with_child, capsys, mocker):
    """Render should not happen for any children until all children names have been looked up"""
    # arrange
    seed = tree_stubbed_with_child[list(tree_stubbed_with_child)[0]]
    child = seed.children[list(seed.children)[0]]
    another_child = replace(child, service_name='another_child')
    seed.children['last_child'] = another_child
    mocker.patch.object(child, 'crawl_complete', return_value=True)
    mocker.patch.object(another_child, 'crawl_complete', return_value=True)
    mocker.patch.object(child, 'name_lookup_complete', return_value=True)
    mocker.patch.object(another_child, 'name_lookup_complete', return_value=False)

    # act/assert
    with pytest.raises(asyncio.TimeoutError):
        await _helper_render_tree_with_timeout(tree_stubbed_with_child)
    captured = capsys.readouterr()
    assert seed.service_name in captured.out
    assert child.service_name not in captured.out
    assert another_child.service_name not in captured.out


@pytest.mark.asyncio
@pytest.mark.parametrize('error', ['NULL_ADDRESS', 'TIMEOUT', 'AWS_LOOKUP_FAILED'])
async def test_render_tree_case_child_errors(error, tree_stubbed_with_child, capsys):
    """A node with errors and no service name is displayed correctly"""
    # arrange
    seed = tree_stubbed_with_child[list(tree_stubbed_with_child)[0]]
    child = seed.children[list(seed.children)[0]]

    child.service_name = None
    child.errors = {error: True}

    # act
    await _helper_render_tree_with_timeout(tree_stubbed_with_child)
    captured = capsys.readouterr()

    # assert
    assert f" └--{child.protocol.ref}--? \x1b[31m{{ERR:{error}}} \x1b[0mUNKNOWN [port:{child.protocol_mux}]" \
           in captured.out


@pytest.mark.asyncio
async def test_render_tree_case_child_warning_cycle(tree_stubbed_with_child, capsys):
    """A node with a CYCLE warning is displayed correctly"""
    # arrange
    seed = tree_stubbed_with_child[list(tree_stubbed_with_child)[0]]
    child = seed.children[list(seed.children)[0]]
    child.warnings = {'CYCLE': True}

    # act
    await _helper_render_tree_with_timeout(tree_stubbed_with_child)
    captured = capsys.readouterr()

    # assert
    assert f" <--{child.protocol.ref}--> \x1b[33m{{WARN:CYCLE}} \x1b[0m{child.service_name}" in captured.out


@pytest.mark.asyncio
async def test_render_tree_case_child_warning_defunct(cli_args_mock, tree_stubbed_with_child, capsys):
    """A node with a DEFUNCT warning is displayed correctly"""
    # arrange
    cli_args_mock.hide_defunct = False
    seed = tree_stubbed_with_child[list(tree_stubbed_with_child)[0]]
    child = seed.children[list(seed.children)[0]]
    child.warnings = {'DEFUNCT': True}

    # act
    await _helper_render_tree_with_timeout(tree_stubbed_with_child)
    captured = capsys.readouterr()

    # assert
    assert f" └--{child.protocol.ref}--x \x1b[33m{{WARN:DEFUNCT}} \x1b[0m{child.service_name}" in captured.out


@pytest.mark.asyncio
async def test_render_tree_case_hide_defunct(cli_args_mock, tree_stubbed_with_child, capsys):
    """A node with a DEFUNCT warning is displayed correctly"""
    # arrange
    cli_args_mock.hide_defunct = True
    seed = tree_stubbed_with_child[list(tree_stubbed_with_child)[0]]
    child = seed.children[list(seed.children)[0]]
    child.warnings = {'DEFUNCT': True}

    # act
    await _helper_render_tree_with_timeout(tree_stubbed_with_child)
    captured = capsys.readouterr()

    # assert
    assert 'DEFUNCT' not in captured.out


@pytest.mark.asyncio
async def test_render_tree_case_respect_cli_max_depth(cli_args_mock, tree_stubbed_with_child, capsys):
    """--max-depth arg is respected"""
    # arrange
    cli_args_mock.max_depth = 0
    seed = tree_stubbed_with_child[list(tree_stubbed_with_child)[0]]
    child = seed.children[list(seed.children)[0]]
    child.service_name = 'DEPTH_1'

    # act
    await _helper_render_tree_with_timeout(tree_stubbed_with_child)
    captured = capsys.readouterr()

    # assert
    assert child.service_name not in captured.out


@pytest.mark.asyncio
async def test_render_tree_case_last_child(tree_stubbed_with_child, node_fixture, capsys):
    """A single node with multiple children, the last child printed is slightly different"""
    # arrange
    seed = tree_stubbed_with_child[list(tree_stubbed_with_child)[0]]
    child = seed.children[list(seed.children)[0]]
    last_child = replace(node_fixture, service_name='last_child_service', address='last_child_address', children={})
    seed.children['last_child'] = last_child

    # act
    await _helper_render_tree_with_timeout(tree_stubbed_with_child)
    captured = capsys.readouterr()

    # assert
    assert f"|--{child.protocol.ref}--> {child.service_name}" in captured.out
    assert f"└--{last_child.protocol.ref}--> {last_child.service_name} " in captured.out


@pytest.mark.asyncio
async def test_render_tree_case_merged_nodes(tree_stubbed_with_child, capsys):
    """A single node with multiple children, the last child printed is slightly different"""
    # arrange
    seed = tree_stubbed_with_child[list(tree_stubbed_with_child)[0]]
    child = seed.children[list(seed.children)[0]]
    redundant_child = replace(child, protocol_mux='some_other_mux')
    seed.children['redundant_child'] = redundant_child
    # - we have to capture this now because render_tree will mutate these objects!
    expected_merged_mux = f"{child.protocol_mux},{redundant_child.protocol_mux}"

    # act
    await _helper_render_tree_with_timeout(tree_stubbed_with_child)
    captured = capsys.readouterr()
    print(captured)

    # assert
    assert f"--> {child.service_name} [port:{expected_merged_mux}]" in captured.out
