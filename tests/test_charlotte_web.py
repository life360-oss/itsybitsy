import os
import pytest

from itsybitsy import charlotte_web


def _write_stub_web_yaml(charlotte_d: str, contents: str) -> None:
    """Helper method to write contents to the stub web.yaml file"""
    file = os.path.join(charlotte_d, 'web.yaml')
    with open(file, 'w') as f:
        f.write(contents)


def test_spin_up_case_malformed_web_yaml(charlotte_d):
    """Malformed yaml is caught in spinning up charlotte_web"""
    # arrange
    fake_protocol_web_yaml = f"""
 ---
 :!!#$T%!##
 protocols:
"""
    _write_stub_web_yaml(charlotte_d, fake_protocol_web_yaml)

    # act
    with pytest.raises(charlotte_web.WebYamlException) as e_info:
        charlotte_web.spin_up()

    # assert
    assert 'Unable to load' in str(e_info)


def test_spin_up_case_malformed_protocol(charlotte_d):
    """Well-formed yaml, malformed protocol schema is caught"""
    # arrange
    fake_protocol_web_yaml = f"""
---
protocols:
  FOO:
    nomnom: "bar"
"""
    _write_stub_web_yaml(charlotte_d, fake_protocol_web_yaml)

    # act
    with pytest.raises(charlotte_web.WebYamlException) as e_info:
        charlotte_web.spin_up()

    # assert
    assert 'protocols malformed' in str(e_info)


def test_spin_up_case_no_protocols(charlotte_d):
    """No user defined protocols is caught"""
    # arrange
    fake_protocol_web_yaml = f"""
---
foo: bar
"""
    _write_stub_web_yaml(charlotte_d, fake_protocol_web_yaml)

    # act
    with pytest.raises(SystemExit) as e_info:
        charlotte_web.spin_up()

    # assert
    assert e_info.type == SystemExit


@pytest.mark.parametrize('protocol_ref,blocking,is_database', [('FOO', True, True), ('BAR', True, False),
                                                               ('BAZ', False, False)])
def test_get_protocol(charlotte_d, protocol_ref, blocking, is_database):
    """We are able get a parsed protocol from charlotte which was loaded from disk"""
    # Technically an integration test that tests the interaction of spin_up() and get_protocol()
    # arrange
    fake_protocol_web_yaml = f"""
---
protocols:
  {protocol_ref}:
    name: "{protocol_ref.capitalize()}"
    blocking: {str(blocking).lower()}
    is_database: {str(is_database).lower()}
"""
    _write_stub_web_yaml(charlotte_d, fake_protocol_web_yaml)

    # act
    charlotte_web.spin_up()
    protocol = charlotte_web.get_protocol(protocol_ref)

    # assert
    assert protocol_ref == protocol.ref
    assert blocking == protocol.blocking
    assert is_database == protocol.is_database


def test_skip(charlotte_d, mocker):
    """We are able to correctly match a skip loaded from disk"""
    # Technically an integration test that tests the interaction of spin_up() and skip()
    # arrange
    mocker.patch('itsybitsy.charlotte_web._validate', return_value=None)
    hint_web_yaml = f"""
skips:
  service_names:
    - "foo"
    - "bar"
"""
    _write_stub_web_yaml(charlotte_d, hint_web_yaml)

    # act
    charlotte_web.spin_up()

    # assert
    assert charlotte_web.skip('bar')
    assert charlotte_web.skip('barf')
    assert charlotte_web.skip('foo')
    assert charlotte_web.skip('foo-service')
    assert charlotte_web.skip('food-service')
    assert charlotte_web.skip('a-fool-service')
    assert not charlotte_web.skip('oof-service')
    assert not charlotte_web.skip('fo')
    assert not charlotte_web.skip('cats')


def test_hints(charlotte_d, mocker):
    """We are able to correctly get hints that were parsed from disk"""
    # Technically an integration test that tests the interaction of spin_up() and hints()
    # arrange
    upstream, downstream, protocol, protocol_dummy, mux, provider, instance_provider = \
        ('foo-service', 'bar-service', 'BAZ', 'baz-dummy', 'buz', 'qux', 'quux')
    mocker.patch('itsybitsy.charlotte_web._validate', return_value=None)
    get_protocl_func = mocker.patch('itsybitsy.charlotte_web.get_protocol', return_value=protocol_dummy)
    hint_web_yaml = f"""
hints:
  {upstream}:
    - service_name: "{downstream}"
      protocol: "{protocol}"
      protocol_mux: "{mux}"
      provider: "{provider}"
      instance_provider: "{instance_provider}"
"""
    _write_stub_web_yaml(charlotte_d, hint_web_yaml)

    # act
    charlotte_web.spin_up()
    hints = charlotte_web.hints(upstream)

    # assert
    assert len(hints) == 1
    hint = hints[0]
    assert hint.service_name == downstream
    assert hint.protocol == protocol_dummy
    get_protocl_func.assert_called_once_with(protocol)
    assert hint.protocol_mux == mux
    assert hint.instance_provider == instance_provider
