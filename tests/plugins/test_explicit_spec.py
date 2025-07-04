# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# No need for os and tempfile anymore as we use support files

import pytest

from conda import plugins
from conda.env.specs.explicit import ExplicitSpec
from conda.exceptions import EnvironmentSpecPluginNotDetected
from conda.plugins.types import CondaEnvironmentSpecifier
from tests.env import support_file


@pytest.fixture(scope="module")
def support_explicit_file():
    """Path to the explicit environment file in the test support directory"""
    return support_file("explicit.txt")


@pytest.fixture(scope="module")
def support_non_explicit_file():
    """Path to a non-explicit environment file in the test support directory"""
    return support_file("requirements.txt")


def test_can_handle_explicit_file(support_explicit_file):
    """Ensures ExplicitSpec can handle a file with @EXPLICIT marker"""
    spec = ExplicitSpec(filename=support_explicit_file)
    assert spec.can_handle()


def test_explicit_file_spec_rejects_non_explicit_file(support_non_explicit_file):
    """Ensures ExplicitSpec does not handle non-explicit files"""
    spec = ExplicitSpec(filename=support_non_explicit_file)
    assert not spec.can_handle()


def test_environment_creation(support_explicit_file):
    """Test that environment is correctly created from explicit file"""
    spec = ExplicitSpec(filename=support_explicit_file)

    # Get the environment and check if it's detected as explicit
    env = spec.environment
    assert env.dependencies.explicit is True

    # Check raw dependencies - should include @EXPLICIT and package URLs
    raw_deps = env.dependencies.raw
    assert raw_deps is not None
    assert len(raw_deps) == 3  # @EXPLICIT + 2 package URLs

    # Verify environment dependencies include both packages
    env_pkgs = [str(dep).lower() for dep in raw_deps]
    assert any("python" in pkg for pkg in env_pkgs), "No Python package in environment"
    assert any("numpy" in pkg for pkg in env_pkgs), "No NumPy package in environment"


class ExplicitSpecPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="explicit-test",
            environment_spec=ExplicitSpec,
        )


@pytest.fixture()
def explicit_file_spec_plugin(plugin_manager):
    plugin = ExplicitSpecPlugin()
    plugin_manager.register(plugin)
    return plugin_manager


def test_explicit_file_spec_is_registered(
    explicit_file_spec_plugin, support_explicit_file
):
    """Ensures that the explicit spec has been registered and can handle explicit files"""
    # Verify plugin registration and correct name
    env_spec_backend = explicit_file_spec_plugin.get_environment_specifier(
        support_explicit_file
    )
    assert env_spec_backend.name == "explicit-test"

    # Test environment creation through the plugin
    env = env_spec_backend.environment_spec(support_explicit_file).environment

    # Check environment structure and content
    assert env.dependencies.explicit
    assert len(env.dependencies.raw or []) == 3  # @EXPLICIT + 2 package URLs

    # Verify expected packages are present
    raw_deps = env.dependencies.raw or []
    deps_str = [str(dep).lower() for dep in raw_deps]
    assert any("python" in pkg for pkg in deps_str), "No Python package found"
    assert any("numpy" in pkg for pkg in deps_str), "No NumPy package found"


def test_raises_error_if_not_explicit_file(
    explicit_file_spec_plugin, support_non_explicit_file
):
    """Ensures explicit spec plugin does not accept non-explicit files**"""
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        explicit_file_spec_plugin.get_environment_specifier(support_non_explicit_file)
