import pytest
from dataclasses import replace

from itsybitsy import constants
from itsybitsy.plugins import render_graphviz


@pytest.fixture(autouse=True)
def set_default_rankdir(cli_args_mock):
    cli_args_mock.render_graphviz_rankdir = constants.GRAPHVIZ_RANKDIR_LEFT_TO_RIGHT


@pytest.mark.parametrize('rankdir', [constants.GRAPHVIZ_RANKDIR_LEFT_TO_RIGHT,
                                     constants.GRAPHVIZ_RANKDIR_TOP_TO_BOTTOM])
def test_render_tree_case_respect_cli_rankdir_options(cli_args_mock, rankdir, tree_named, capsys):
    # arrange
    cli_args_mock.render_graphviz_rankdir = rankdir

    # act
    render_graphviz.render_tree(tree_named, True)
    captured = capsys.readouterr()

    # assert
    assert f"graph [dpi=300 rankdir={rankdir}]" in captured.out


@pytest.mark.parametrize('skip_nonblocking_grandchildren,expected_rankdir',
                         [(False, constants.GRAPHVIZ_RANKDIR_TOP_TO_BOTTOM),
                          (True, constants.GRAPHVIZ_RANKDIR_LEFT_TO_RIGHT)])
def test_render_tree_case_respect_cli_rankdir_auto(skip_nonblocking_grandchildren, expected_rankdir, cli_args_mock,
                                                   tree_named, capsys):
    # arrange
    cli_args_mock.render_graphviz_rankdir = constants.GRAPHVIZ_RANKDIR_AUTO
    cli_args_mock.skip_nonblocking_grandchildren = skip_nonblocking_grandchildren

    # act
    render_graphviz.render_tree(tree_named, True)
    captured = capsys.readouterr()

    # assert
    assert f"graph [dpi=300 rankdir={expected_rankdir}]" in captured.out


@pytest.mark.parametrize('highlighted_service', ['child_service_name', 'parent_service_name'])
def test_render_tree_case_respect_cli_highlight_services(highlighted_service, tree, node_fixture_factory, cli_args_mock,
                                                         capsys):
    """Validate blocking child shows regular nondashed, non bold line when it is not blocking from top"""
    # arrange
    cli_args_mock.render_graphviz_highlight_services = [highlighted_service]
    child = replace(node_fixture_factory(), service_name='child_service_name')
    parent = list(tree.values())[0]
    parent.service_name = 'parent_service_name'
    parent.children = {'bar_service_ref': child}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()
    print(captured)

    # assert
    assert f"color=\"yellow:black:yellow\"" in captured.out


def test_render_tree_case_node_has_service_name(tree_named, capsys):
    """single node - not from hint, with service name, no children, no errs/warns"""
    # arrange/act
    render_graphviz.render_tree(tree_named, True)
    captured = capsys.readouterr()

    # assert
    assert f"{tree_named[list(tree_named)[0]].service_name} [style=bold]" in captured.out


def test_render_tree_case_node_no_service_name(tree, capsys):
    """single node - not from hint, no service name, no children, no errs/warns"""
    # arrange/act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"UNKNOWN\n({list(tree)[0]})\" [style=bold]" in captured.out


def test_render_tree_case_node_is_database(tree_named, capsys):
    """Database node rendered as such"""
    # arrange
    tree = tree_named
    list(tree.values())[0].protocol = replace(list(tree.values())[0].protocol, is_database=True)

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{list(tree.values())[0].service_name} [shape=cylinder style=bold]" in captured.out


def test_render_tree_case_node_is_containerized(tree_named, capsys):
    """Containerized node rendered as such"""
    # arrange
    tree = tree_named
    list(tree.values())[0].containerized = True

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{list(tree.values())[0].service_name} [shape=septagon style=bold]" in captured.out


def test_render_tree_case_node_errors(tree_named, capsys):
    """Node with errors rendered as such"""
    # arrange
    tree = tree_named
    list(tree.values())[0].errors = {'FOO': True}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{list(tree.values())[0].service_name} [color=red style=bold]" in captured.out


def test_render_tree_case_node_warnings(tree_named, capsys):
    """Node with warnings rendered as such"""
    # arrange
    tree = tree_named
    list(tree.values())[0].warnings = {'FOO': True}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{list(tree.values())[0].service_name} [color=darkorange style=bold]" in captured.out


def test_render_tree_case_node_name_cleaned(tree, capsys):
    """Test that the node name is cleaned during render"""
    # arrange
    list(tree.values())[0].service_name = '"foo:bar#baz"'

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert 'foo_bar_baz [style=bold]' in captured.out


def test_render_tree_case_edge_blocking_child(tree, node_fixture_factory, dummy_protocol_ref, capsys):
    """Validate blocking child shows regular nondashed, non bold line when it is not blocking from top"""
    # arrange
    parent = list(tree.values())[0]
    child = replace(node_fixture_factory(), service_name='intermediary_child')
    child.protocol = replace(child.protocol, blocking=False)
    parent.children = {'intermediary_child': child}
    final_child = replace(node_fixture_factory(), service_name='final_child')
    final_child.protocol = replace(child.protocol, blocking=True)
    child.children = {'final_child': final_child}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{child.service_name} -> {final_child.service_name} [label={dummy_protocol_ref} color=\"\" style=\"\"]"\
           in captured.out


def test_render_tree_case_edge_blocking_from_top_child(tree, node_fixture, capsys):
    """Validate attributes for a blocking from top child/edge in the graph"""
    # arrange
    parent = list(tree.values())[0]
    parent.service_name = 'foo'
    child = replace(node_fixture, service_name='bar')
    child.protocol = replace(child.protocol, ref='BAZ')
    parent.children = {'buzz': child}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{parent.service_name} [style=bold]" in captured.out
    assert f"{child.service_name} [style=bold]" in captured.out
    assert f"{parent.service_name} -> {child.service_name} [label={child.protocol.ref} color=\"\" style=bold]"\
           in captured.out


def test_render_tree_case_edge_blocking_from_top_once_child(tree_named, node_fixture_factory, dummy_protocol_ref, capsys):
    """
    Case where a child is blocking, but it shows up twice in the graph and is only annotated as blocking
    from top in the 1 scenario where it is - and regular blocking (but not from top) in the other
    """
    # arrange
    tree = tree_named
    parent, blocking_service_name, nonblocking_service_name = (list(tree.values())[0], 'foo', 'bar')
    blocking_child = replace(node_fixture_factory(), service_name=blocking_service_name)
    blocking_child.protocol = replace(blocking_child.protocol, blocking=True)
    nonblocking_child = replace(node_fixture_factory(), service_name=nonblocking_service_name)
    nonblocking_child.protocol = replace(blocking_child.protocol, blocking=False)
    parent.children = {'blocking_child': blocking_child, 'nonblocking_child': nonblocking_child}
    nonblocking_child.children = {'blocking_child': blocking_child}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{parent.service_name} -> {blocking_service_name} [label={dummy_protocol_ref} color=\"\" style=bold]"\
           in captured.out
    assert f"{nonblocking_service_name} -> {blocking_service_name} [label={dummy_protocol_ref} color=\"\" style=\"\"]"\
           in captured.out


def test_render_tree_case_edge_child_nonblocking(tree_named, node_fixture, capsys):
    """Nonblocking chihld shown as dashed edge"""
    # arrange
    child_node, child_protocol_ref = (replace(node_fixture, service_name='dummy_child'), 'DUM')
    child_node.protocol = replace(child_node.protocol, ref=child_protocol_ref, blocking=False)
    tree = tree_named
    list(tree.values())[0].children = {'child_service_ref': child_node}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{list(tree.values())[0].service_name} -> {child_node.service_name} [label={child_protocol_ref} " \
           f'color="" style=",dashed"]' in captured.out


def test_render_tree_case_edge_child_defunct_hidden(tree, node_fixture, cli_args_mock, capsys):
    """Defunct child hidden per ARGS"""
    # arrange
    cli_args_mock.hide_defunct = True
    child_node = replace(node_fixture, service_name='child_service', warnings={'DEFUNCT': True})
    list(tree.values())[0].children = {'child_service_ref': child_node}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert child_node.service_name not in captured.out
    assert f" -> {child_node.service_name}" not in captured.out


def test_render_tree_case_edge_child_defunct_shown(tree_named, node_fixture, cli_args_mock, capsys):
    """Defunct child shown correctly - also validates `warnings` are shown correctly"""
    # arrange
    cli_args_mock.hide_defunct = False
    child_node = replace(node_fixture, service_name='child_service', warnings={'DEFUNCT': True})
    tree = tree_named
    list(tree.values())[0].children = {'child_service_ref': child_node}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{list(tree.values())[0].service_name} -> {child_node.service_name} [label=\"{child_node.protocol.ref} " \
           f'(DEFUNCT)" color=darkorange penwidth=3 style="bold,dotted,filled"]' in captured.out


def test_render_tree_case_edge_child_errors(tree_named, node_fixture, capsys):
    """Child with errors shown correctly"""
    # arrange
    child_node = replace(node_fixture, service_name='child_service', errors={'FOO': True})
    tree = tree_named
    list(tree.values())[0].children = {'child_service_ref': child_node}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert f"{child_node.service_name} [color=red style=bold]" in captured.out
    assert f"{list(tree.values())[0].service_name} -> {child_node.service_name} [label=\"{child_node.protocol.ref} " \
           f'(FOO)" color=red style=bold]' in captured.out


def test_render_tree_case_edge_child_hint(tree_named, node_fixture, capsys):
    """Child from_hint shown correctly"""
    # arrange
    child_node = replace(node_fixture, service_name='child_service', from_hint=True)
    tree = tree_named
    list(tree.values())[0].children = {'child_service_ref': child_node}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert child_node.service_name in captured.out
    assert f"{list(tree.values())[0].service_name} -> {child_node.service_name} [label=\"{child_node.protocol.ref} " \
           f'(HINT)" color=":blue" penwidth=3 style=bold]' in captured.out


@pytest.mark.parametrize('containerized,shape_string', [(False, ''), (True, 'shape=septagon ')])
def test_render_tree_case_node_hint_merged(containerized, shape_string, tree_named, protocol_fixture,
                                           node_fixture_factory, capsys):
    """Tests that two child nodes which are on the same protocol/mux are merged together if 1 is a hint"""
    # arrange
    protocol_ref, protocol_mux, error, service_name = ('FOO', 'barbaz', 'BUZZ', 'qux')
    protocol_fixture = replace(protocol_fixture, ref=protocol_ref)
    child_node_crawled = replace(node_fixture_factory(), service_name=None, errors={error: True})
    child_node_crawled.protocol = protocol_fixture
    child_node_crawled.protocol_mux = protocol_mux
    child_node_hint = replace(node_fixture_factory(), service_name=service_name, from_hint=True)
    child_node_hint.protocol = protocol_fixture
    child_node_hint.protocol_mux = protocol_mux
    child_node_hint.containerized = containerized
    tree = tree_named
    list(tree.values())[0].children = {'crawled': child_node_crawled, 'hinted': child_node_hint}

    # act
    render_graphviz.render_tree(tree, True)
    captured = capsys.readouterr()

    # assert
    assert 'UNKNOWN' not in captured.out
    assert f"{child_node_hint.service_name} [color=red {shape_string}style=bold]" in captured.out
    assert f"{list(tree.values())[0].service_name} -> {child_node_hint.service_name} [label=\"{protocol_ref} " \
           f"({error},HINT)\" color=\"red:blue\" penwidth=3 style=bold]" in captured.out


def test_render_tree_case_node_nonhint_not_merged(tree_named, protocol_fixture, node_fixture_factory, capsys):
    """
    Ensures that 2 children on the same protocol/mux are not accidentally merged into one
    Ensures that 2 children not on the same protocol/mux are not accidentally merged into one
    """
    # arrange
    protocol_ref, protocol_mux_1, protocol_mux_2, child_1_name, child_2_name, child_3_name = \
        ('FOO', 'barbaz', 'buzzqux', 'quxx', 'quz', 'clorge')
    protocol_fixture = replace(protocol_fixture, ref=protocol_ref)
    child_1 = replace(node_fixture_factory(), service_name=child_1_name)
    child_1.protocol = protocol_fixture
    child_1.protocol_mux = protocol_mux_1
    child_2 = replace(node_fixture_factory(), service_name=child_2_name)
    child_2.protocol = protocol_fixture
    child_2.protocol_mux = protocol_mux_1
    child_3 = replace(node_fixture_factory(), service_name=child_3_name)
    child_3.protocol = protocol_fixture
    child_3.protocol_mux = protocol_mux_2

    list(tree_named.values())[0].children = {'child1': child_1, 'child2': child_2, 'child3': child_3}

    # act
    render_graphviz.render_tree(tree_named, True)
    captured = capsys.readouterr()

    # assert
    assert child_1_name in captured.out
    assert child_2_name in captured.out
    assert child_3_name in captured.out
