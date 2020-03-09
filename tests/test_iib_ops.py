import contextlib
import mock
import pkg_resources
import pytest
import os

from pubtools.iib.utils import setup_entry_point_cli
from pubtools.iib.iib_ops import _iib_op_main

import pushcollector


from iiblib.iibclient import IIBBuildDetailsModel
from pubtools.pulplib import ContainerImageRepository
from more_executors.futures import f_return

from utils import FakeTaskManager, FakeCollector


fake_tm = FakeTaskManager()


@contextlib.contextmanager
def setup_entry_point_py(entry_tuple, environ_vars):
    orig_environ = os.environ.copy()
    try:
        for key in environ_vars:
            os.environ[key] = environ_vars[key]
        entry_point_func = pkg_resources.load_entry_point(*entry_tuple)
        yield entry_point_func
    finally:
        os.environ.update(orig_environ)


@pytest.fixture
def fixture_iib_client():
    with mock.patch("iiblib.iibclient.IIBClient") as iibc_patched:
        iibc_patched.return_value.add_bundles.side_effect = lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
            fake_tm.setup_task(*args, **kwargs)
        )
        iibc_patched.return_value.remove_operators.side_effect = lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
            fake_tm.setup_task(*args, **kwargs)
        )
        iibc_patched.return_value.get_build.side_effect = fake_tm.get_task
        iibc_patched.return_value.wait_for_build.side_effect = lambda build_details: IIBBuildDetailsModel.from_dict(
            fake_tm.get_task(build_details.id)
        )
        yield iibc_patched


@pytest.fixture
def fixture_pushcollector():
    fake_collector = FakeCollector()
    pushcollector.Collector.register_backend(
        "pubtools-ibb-test", lambda: fake_collector
    )
    pushcollector.Collector.set_default_backend("pubtools-ibb-test")
    yield fake_collector


@pytest.fixture
def fixture_iib_krb_auth():
    with mock.patch("iiblib.iibclient.IIBKrbAuth") as iib_krbauth_patched:
        iib_krbauth_patched.return_value = mock.MagicMock(name="MockedIIBKrbAuth")
        yield iib_krbauth_patched


@pytest.fixture
def fixture_pulp_client():
    with mock.patch("pubtools.pulplib.Client") as pulpc_patched:
        yield pulpc_patched


@pytest.fixture
def fixture_pulplib_repo_publish():
    with mock.patch(
        "pubtools.pulplib.ContainerImageRepository.publish"
    ) as repo_publish_patched:
        repo_publish_patched.return_value = f_return()
        yield repo_publish_patched


@pytest.fixture
def fixture_pulplib_repo_sync():
    with mock.patch(
        "pubtools.pulplib.ContainerImageRepository.sync"
    ) as repo_sync_patched:
        yield repo_sync_patched


@pytest.fixture
def fixture_container_image_repo():
    repo = ContainerImageRepository(id="redhat-operators")
    repo.__dict__["_client"] = fixture_pulp_client
    return repo


@pytest.fixture
def fixture_common_iib_op_args():
    return [
        "--pulp-url",
        "pulp-url",
        "--pulp-user",
        "pulp-user",
        "--pulp-insecure",
        "--iib-server",
        "iib-server",
        "--index-image",
        "index-image",
        "--binary-image",
        "binary-image",
        "--arch",
        "arch",
        "--iib-krb-principal",
        "example@REALM",
        "--iib-insecure",
    ]


def test_add_bundles_cli(
    fixture_iib_client,
    fixture_pulp_client,
    fixture_iib_krb_auth,
    fixture_pulplib_repo_publish,
    fixture_pulplib_repo_sync,
    fixture_container_image_repo,
    fixture_common_iib_op_args,
    fixture_pushcollector,
):

    repo = fixture_container_image_repo
    fixture_pulp_client.return_value.search_repository.return_value = [repo]
    fixture_pulp_client.return_value.get_repository.return_value = repo

    with setup_entry_point_cli(
        ("pubtools_iib", "console_scripts", "pubtools-iib-add-bundles"),
        "pubtools-iib-add-bundle",
        fixture_common_iib_op_args
        + ["--bundle", "bundle1", "--iib-legacy-org", "legacy-org"],
        {"PULP_PASSWORD": "pulp-password", "CNR_TOKEN": "cnr_token"},
    ) as entry_func:
        entry_func()
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        "binary-image",
        ["bundle1"],
        ["arch"],
        cnr_token="cnr_token",
        organization="legacy-org",
    )
    fixture_pulplib_repo_sync.assert_called_once()
    assert fixture_pulplib_repo_sync.mock_calls[0].args[0].feed == "https://feed.com"

    fixture_pulplib_repo_publish.assert_called_once()

    assert fixture_pushcollector.items == [
        {
            "state": "PENDING",
            "origin": "index-image",
            "filename": "operator-1",
            "build": "feed.com/index/image:tag",
            "dest": "redhat-operators",
            "signing_key": None,
            "checksums": None,
            "src": "bundle1",
        },
        {
            "state": "PUSHED",
            "origin": "index-image",
            "filename": "operator-1",
            "build": "feed.com/index/image:tag",
            "dest": "redhat-operators",
            "signing_key": None,
            "checksums": None,
            "src": "bundle1",
        },
    ]


def test_add_bundles_cli_error(
    fixture_iib_client,
    fixture_pulp_client,
    fixture_iib_krb_auth,
    fixture_pulplib_repo_publish,
    fixture_pulplib_repo_sync,
    fixture_container_image_repo,
    fixture_common_iib_op_args,
    fixture_pushcollector,
):

    repo = fixture_container_image_repo
    fixture_pulp_client.return_value.search_repository.return_value = [repo]
    fixture_pulp_client.return_value.get_repository.return_value = repo
    fixture_iib_client.return_value.add_bundles.side_effect = lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
        fake_tm.setup_task(
            *args,
            **dict(list(kwargs.items()) + [("state_seq", ("in_progress", "failed"))])
        )
    )

    with setup_entry_point_cli(
        ("pubtools_iib", "console_scripts", "pubtools-iib-add-bundles"),
        "pubtools-iib-add-bundle",
        fixture_common_iib_op_args + ["--bundle", "bundle1"],
        {"PULP_PASSWORD": "pulp-password", "CNR_TOKEN": "cnr_token"},
    ) as entry_func:
        try:
            entry_func()
            assert False, "Should have raised SystemError"
        except SystemExit:
            pass

    assert fixture_pushcollector.items == [
        {
            "state": "PENDING",
            "origin": "index-image",
            "filename": "operator-1",
            "build": "feed.com/index/image:tag",
            "dest": "redhat-operators",
            "signing_key": None,
            "checksums": None,
            "src": "bundle1",
        },
        {
            "state": "NOTPUSHED",
            "origin": "index-image",
            "filename": "operator-1",
            "build": "feed.com/index/image:tag",
            "dest": "redhat-operators",
            "signing_key": None,
            "checksums": None,
            "src": "bundle1",
        },
    ]


def test_add_bundles_py(
    fixture_iib_client,
    fixture_pulp_client,
    fixture_iib_krb_auth,
    fixture_pulplib_repo_publish,
    fixture_pulplib_repo_sync,
    fixture_container_image_repo,
    fixture_common_iib_op_args,
):

    repo = fixture_container_image_repo
    fixture_pulp_client.return_value.search_repository.return_value = [repo]
    fixture_pulp_client.return_value.get_repository.return_value = repo
    with setup_entry_point_py(
        ("pubtools_iib", "console_scripts", "pubtools-iib-add-bundles"),
        {"PULP_PASSWORD": "pulp-password", "CNR_TOKEN": "cnr_token"},
    ) as entry_func:
        retval = entry_func(
            ["cmd"] + fixture_common_iib_op_args + ["--bundle", "bundle1"]
        )

    assert isinstance(retval, IIBBuildDetailsModel)

    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image", "binary-image", ["bundle1"], ["arch"], cnr_token="cnr_token"
    )
    fixture_pulplib_repo_sync.assert_called_once()
    assert fixture_pulplib_repo_sync.mock_calls[0].args[0].feed == "https://feed.com"

    fixture_pulplib_repo_publish.assert_called_once()


def test_remove_operators_cli(
    fixture_iib_client,
    fixture_pulp_client,
    fixture_iib_krb_auth,
    fixture_pulplib_repo_publish,
    fixture_pulplib_repo_sync,
    fixture_container_image_repo,
    fixture_common_iib_op_args,
    fixture_pushcollector,
):

    repo = fixture_container_image_repo
    fixture_pulp_client.return_value.search_repository.return_value = [repo]
    fixture_pulp_client.return_value.get_repository.return_value = repo
    fixture_iib_client.return_value.remove_operators.side_effect = lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
        fake_tm.setup_task(*args, **dict(list(kwargs.items()) + [("op_type", "rm")]))
    )
    with setup_entry_point_cli(
        ("pubtools_iib", "console_scripts", "pubtools-iib-remove-operators"),
        "pubtools-iib-remove-operators",
        fixture_common_iib_op_args + ["--operator", "op1"],
        {"PULP_PASSWORD": "pulp-password"},
    ) as entry_func:
        entry_func()
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.remove_operators.assert_called_once_with(
        "index-image", "binary-image", ["op1"], ["arch"]
    )
    fixture_pulplib_repo_sync.assert_called_once()
    assert fixture_pulplib_repo_sync.mock_calls[0].args[0].feed == "https://feed.com"

    fixture_pulplib_repo_publish.assert_called_once()

    assert fixture_pushcollector.items == [
        {
            "state": "PENDING",
            "origin": "index-image",
            "filename": "operator-op1",
            "dest": "redhat-operators",
            "build": "feed.com/index/image:tag",
            "signing_key": None,
            "checksums": None,
            "src": None,
        },
        {
            "state": "DELETED",
            "origin": "index-image",
            "filename": "operator-op1",
            "dest": "redhat-operators",
            "build": "feed.com/index/image:tag",
            "signing_key": None,
            "checksums": None,
            "src": None,
        },
    ]


def test_remove_operators_cli_error(
    fixture_iib_client,
    fixture_pulp_client,
    fixture_iib_krb_auth,
    fixture_pulplib_repo_publish,
    fixture_pulplib_repo_sync,
    fixture_container_image_repo,
    fixture_common_iib_op_args,
    fixture_pushcollector,
):

    repo = fixture_container_image_repo
    fixture_pulp_client.return_value.search_repository.return_value = [repo]
    fixture_pulp_client.return_value.get_repository.return_value = repo
    fixture_iib_client.return_value.remove_operators.side_effect = lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
        fake_tm.setup_task(
            *args,
            **dict(
                list(kwargs.items())
                + [("state_seq", ("in_progress", "failed")), ("op_type", "rm")]
            )
        )
    )
    with setup_entry_point_cli(
        ("pubtools_iib", "console_scripts", "pubtools-iib-remove-operators"),
        "pubtools-iib-remove-operators",
        fixture_common_iib_op_args + ["--operator", "op1"],
        {"PULP_PASSWORD": "pulp-password"},
    ) as entry_func:
        try:
            entry_func()
            assert False, "Should have raised SystemError"
        except SystemExit:
            pass

    assert fixture_pushcollector.items == [
        {
            "state": "PENDING",
            "origin": "index-image",
            "filename": "operator-op1",
            "dest": "redhat-operators",
            "build": "feed.com/index/image:tag",
            "signing_key": None,
            "checksums": None,
            "src": None,
        },
        {
            "state": "NOTPUSHED",
            "origin": "index-image",
            "filename": "operator-op1",
            "dest": "redhat-operators",
            "build": "feed.com/index/image:tag",
            "signing_key": None,
            "checksums": None,
            "src": None,
        },
    ]


def test_remove_operators_py(
    fixture_iib_client,
    fixture_pulp_client,
    fixture_iib_krb_auth,
    fixture_pulplib_repo_publish,
    fixture_pulplib_repo_sync,
    fixture_container_image_repo,
    fixture_common_iib_op_args,
):

    repo = fixture_container_image_repo
    fixture_pulp_client.return_value.search_repository.return_value = [repo]
    fixture_pulp_client.return_value.get_repository.return_value = repo
    with setup_entry_point_py(
        ("pubtools_iib", "console_scripts", "pubtools-iib-remove-operators"),
        {"PULP_PASSWORD": "pulp-password"},
    ) as entry_func:
        retval = entry_func(
            ["cmd"] + fixture_common_iib_op_args + ["--operator", "op1"]
        )

    assert isinstance(retval, IIBBuildDetailsModel)

    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.remove_operators.assert_called_once_with(
        "index-image", "binary-image", ["op1"], ["arch"]
    )
    fixture_pulplib_repo_sync.assert_called_once()
    assert fixture_pulplib_repo_sync.mock_calls[0].args[0].feed == "https://feed.com"

    fixture_pulplib_repo_publish.assert_called_once()


def test_invalid_op(fixture_common_iib_op_args):
    try:
        _iib_op_main((), "invalid-op")
        assert False, "Should have raised"
    except ValueError:
        pass
