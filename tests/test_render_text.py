from itsybitsy import render_text


def test_render_tree(tree_stubbed_with_child, capsys):
    # arrange/act
    render_text.render_tree(tree_stubbed_with_child)
    captured = capsys.readouterr()
    parent = list(tree_stubbed_with_child.values())[0]
    child = list(parent.children.values())[0]

    # assert
    'foo -> baz (dummy_mux)'
    assert f"{parent.service_name} -> {child.service_name} ({parent.protocol_mux})" in captured.out
