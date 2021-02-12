import contextlib
import mock
import pkg_resources
import pytest
import os

from pubtools.iib.utils import setup_entry_point_cli
from pubtools.iib.iib_ops import _iib_op_main

import pushcollector


from iiblib.iib_build_details_model import IIBBuildDetailsModel
from pubtools.pulplib import ContainerImageRepository
from more_executors.futures import f_return

from utils import FakeTaskManager, FakeCollector


FIXTURE_IIB_SERVER = "iib-server"


fake_tm = FakeTaskManager()

operator_1_push_item_pending = {
    "state": "PENDING",
    "origin": "index-image",
    "filename": "operator-1",
    "build": "feed.com/index/image:tag",
    "dest": "redhat-operators",
    "signing_key": None,
    "checksums": None,
    "src": "bundle1",
}
operator_1_push_item_notpushed = operator_1_push_item_pending.copy()
operator_1_push_item_notpushed["state"] = "NOTPUSHED"
operator_1_push_item_pushed = operator_1_push_item_pending.copy()
operator_1_push_item_pushed["state"] = "PUSHED"
operator_quay_push_item_pending = operator_1_push_item_pending.copy()
operator_quay_push_item_pending["dest"] = "some-repo"
operator_quay_push_item_pushed = operator_quay_push_item_pending.copy()
operator_quay_push_item_pushed["state"] = "PUSHED"

operator_1_push_item_delete_pending = {
    "state": "PENDING",
    "origin": "index-image",
    "filename": "operator-1",
    "build": "feed.com/index/image:tag",
    "dest": "redhat-operators",
    "signing_key": None,
    "checksums": None,
    "src": None,
}
operator_1_push_item_deleted = operator_1_push_item_delete_pending.copy()
operator_1_push_item_deleted["state"] = "DELETED"
operator_1_push_item_delete_notpushed = operator_1_push_item_delete_pending.copy()
operator_1_push_item_delete_notpushed["state"] = "NOTPUSHED"


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
    with mock.patch("iiblib.iib_client.IIBClient") as iibc_patched:
        iibc_patched.return_value.add_bundles.side_effect = (
            lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
                fake_tm.setup_task(*args, **kwargs)
            )
        )
        iibc_patched.return_value.remove_operators.side_effect = (
            lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
                fake_tm.setup_task(*args, **kwargs)
            )
        )
        iibc_patched.return_value.get_build.side_effect = fake_tm.get_task
        iibc_patched.return_value.wait_for_build.side_effect = (
            lambda build_details: IIBBuildDetailsModel.from_dict(
                fake_tm.get_task(build_details.id)
            )
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
    with mock.patch("iiblib.iib_authentication.IIBKrbAuth") as iib_krbauth_patched:
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
def fixture_pubtools_quay():
    with mock.patch("pubtools._quay.tag_images.tag_images") as quay_patched:
        yield quay_patched


@pytest.fixture
def fixture_common_iib_op_args():
    return [
        "--pulp-url",
        "pulp-url",
        "--pulp-user",
        "pulp-user",
        "--pulp-insecure",
        "--iib-server",
        FIXTURE_IIB_SERVER,
        "--index-image",
        "index-image",
        "--binary-image",
        "binary-image",
        "--arch",
        "arch",
        "--iib-krb-principal",
        "example@REALM",
        "--iib-insecure",
        "--overwrite-from-index",
    ]


@pytest.fixture
def fixture_push_to_quay_args():
    return [
        "--quay-dest-repo",
        "some-repo",
        "--quay-user",
        "some-user",
        "--quay-remote-exec",
        "--quay-ssh-remote-host",
        "some-host",
        "--quay-ssh-remote-host-port",
        "2222",
        "--quay-ssh-reject-unknown-host",
        "--quay-ssh-username",
        "ssh-user",
        "--quay-ssh-key-filename",
        "/path/to/ssh/file.crt",
        "--quay-send-umb-msg",
        "--quay-umb-url",
        "some-umb-url:5555",
        "--quay-umb-cert",
        "/some/path.crt",
        "--quay-umb-client-key",
        "/some/path.key",
        "--quay-umb-ca-cert",
        "some/cacert.crt",
        "--quay-umb-topic",
        "some-topic",
    ]


def add_bundles_mock_calls_tester(
    fixture_iib_client,
    fixture_pulplib_repo_sync,
    fixture_pulplib_repo_publish,
    fixture_iib_krb_auth,
):
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        cnr_token="cnr_token",
        organization="legacy-org",
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
    )
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_pulplib_repo_sync.assert_called_once()
    assert fixture_pulplib_repo_sync.mock_calls[0].args[0].feed == "https://feed.com"
    fixture_pulplib_repo_publish.assert_called_once()


def add_bundles_mock_calls_tester_not_called(
    fixture_iib_client,
    fixture_pulplib_repo_sync,
    fixture_pulplib_repo_publish,
    fixture_iib_krb_auth,
):
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        cnr_token="cnr_token",
        organization="legacy-org",
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
    )
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_pulplib_repo_sync.assert_not_called()
    fixture_pulplib_repo_publish.assert_not_called()


def remove_operators_mock_calls_tester_not_called(
    fixture_iib_client,
    fixture_pulplib_repo_sync,
    fixture_pulplib_repo_publish,
    fixture_iib_krb_auth,
):
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.remove_operators.assert_called_once_with(
        "index-image",
        ["1"],
        ["arch"],
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
    )
    fixture_pulplib_repo_sync.assert_not_called()
    fixture_pulplib_repo_publish.assert_not_called()


def remove_operators_mock_calls_tester(
    fixture_iib_client,
    fixture_pulplib_repo_sync,
    fixture_pulplib_repo_publish,
    fixture_iib_krb_auth,
):
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.remove_operators.assert_called_once_with(
        "index-image",
        ["1"],
        ["arch"],
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
    )
    fixture_pulplib_repo_sync.assert_called_once()
    assert fixture_pulplib_repo_sync.mock_calls[0].args[0].feed == "https://feed.com"

    fixture_pulplib_repo_publish.assert_called_once()


@pytest.mark.parametrize(
    "extra_args,push_items,mock_calls_tester",
    [
        (
            [],
            [operator_1_push_item_pending, operator_1_push_item_pushed],
            add_bundles_mock_calls_tester,
        ),
        (
            ["--skip-pulp"],
            [operator_1_push_item_pending],
            add_bundles_mock_calls_tester_not_called,
        ),
    ],
)
def test_add_bundles_cli(
    fixture_iib_client,
    fixture_pulp_client,
    fixture_iib_krb_auth,
    fixture_pulplib_repo_publish,
    fixture_pulplib_repo_sync,
    fixture_container_image_repo,
    fixture_common_iib_op_args,
    fixture_pushcollector,
    extra_args,
    push_items,
    mock_calls_tester,
):

    repo = fixture_container_image_repo
    fixture_pulp_client.return_value.search_repository.return_value = [repo]
    fixture_pulp_client.return_value.get_repository.return_value = repo

    with setup_entry_point_cli(
        ("pubtools_iib", "console_scripts", "pubtools-iib-add-bundles"),
        "pubtools-iib-add-bundle",
        fixture_common_iib_op_args
        + ["--bundle", "bundle1", "--iib-legacy-org", "legacy-org", "--skip-quay"]
        + extra_args,
        {
            "PULP_PASSWORD": "pulp-password",
            "CNR_TOKEN": "cnr_token",
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        entry_func()
    assert fixture_pushcollector.items == push_items
    mock_calls_tester(
        fixture_iib_client,
        fixture_pulplib_repo_sync,
        fixture_pulplib_repo_publish,
        fixture_iib_krb_auth,
    )


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
    fixture_iib_client.return_value.add_bundles.side_effect = (
        lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
            fake_tm.setup_task(
                *args,
                **dict(
                    list(kwargs.items()) + [("state_seq", ("in_progress", "failed"))]
                )
            )
        )
    )

    with setup_entry_point_cli(
        ("pubtools_iib", "console_scripts", "pubtools-iib-add-bundles"),
        "pubtools-iib-add-bundle",
        fixture_common_iib_op_args + ["--bundle", "bundle1", "--skip-quay"],
        {
            "PULP_PASSWORD": "pulp-password",
            "CNR_TOKEN": "cnr_token",
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        try:
            entry_func()
            assert False, "Should have raised SystemError"
        except SystemExit:
            pass

    assert fixture_pushcollector.items == [
        operator_1_push_item_pending,
        operator_1_push_item_notpushed,
    ]


def test_add_bundles_py(
    caplog,
    capsys,
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
        {
            "PULP_PASSWORD": "pulp-password",
            "CNR_TOKEN": "cnr_token",
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        retval = entry_func(
            ["cmd"]
            + fixture_common_iib_op_args
            + ["--bundle", "bundle1", "--skip-quay"]
        )

    assert isinstance(retval, IIBBuildDetailsModel)

    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        cnr_token="cnr_token",
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
    )
    fixture_pulplib_repo_sync.assert_called_once()
    assert fixture_pulplib_repo_sync.mock_calls[0].args[0].feed == "https://feed.com"

    fixture_pulplib_repo_publish.assert_called_once()

    task_id = retval.id
    url_msg = "IIB details: https://{}/api/v1/builds/{}".format(
        FIXTURE_IIB_SERVER, task_id
    )
    assert url_msg in caplog.messages

    # neither build details nor anything else dumped into stdout
    captured = capsys.readouterr()
    assert not captured.out


def test_add_bundles_py_multiple_bundles(
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
        {
            "PULP_PASSWORD": "pulp-password",
            "CNR_TOKEN": "cnr_token",
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        retval = entry_func(
            ["cmd"]
            + fixture_common_iib_op_args
            + ["--bundle", "bundle1", "--bundle", "bundle2", "--skip-quay"]
        )

    assert isinstance(retval, IIBBuildDetailsModel)

    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1", "bundle2"],
        ["arch"],
        cnr_token="cnr_token",
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
    )
    fixture_pulplib_repo_sync.assert_called_once()
    assert fixture_pulplib_repo_sync.mock_calls[0].args[0].feed == "https://feed.com"

    fixture_pulplib_repo_publish.assert_called_once()


@pytest.mark.parametrize(
    "extra_args,push_items,mock_calls_tester",
    [
        (
            [],
            [operator_1_push_item_delete_pending, operator_1_push_item_deleted],
            remove_operators_mock_calls_tester,
        ),
        (
            ["--skip-pulp"],
            [operator_1_push_item_delete_pending],
            remove_operators_mock_calls_tester_not_called,
        ),
    ],
)
def test_remove_operators_cli(
    fixture_iib_client,
    fixture_pulp_client,
    fixture_iib_krb_auth,
    fixture_pulplib_repo_publish,
    fixture_pulplib_repo_sync,
    fixture_container_image_repo,
    fixture_common_iib_op_args,
    fixture_pushcollector,
    extra_args,
    push_items,
    mock_calls_tester,
):

    repo = fixture_container_image_repo
    fixture_pulp_client.return_value.search_repository.return_value = [repo]
    fixture_pulp_client.return_value.get_repository.return_value = repo
    fixture_iib_client.return_value.remove_operators.side_effect = (
        lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
            fake_tm.setup_task(
                *args, **dict(list(kwargs.items()) + [("op_type", "rm")])
            )
        )
    )
    with setup_entry_point_cli(
        ("pubtools_iib", "console_scripts", "pubtools-iib-remove-operators"),
        "pubtools-iib-remove-operators",
        fixture_common_iib_op_args + ["--operator", "1", "--skip-quay"] + extra_args,
        {
            "PULP_PASSWORD": "pulp-password",
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        entry_func()
    assert fixture_pushcollector.items == push_items
    mock_calls_tester(
        fixture_iib_client,
        fixture_pulplib_repo_sync,
        fixture_pulplib_repo_publish,
        fixture_iib_krb_auth,
    )


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
    fixture_iib_client.return_value.remove_operators.side_effect = (
        lambda *args, **kwargs: IIBBuildDetailsModel.from_dict(
            fake_tm.setup_task(
                *args,
                **dict(
                    list(kwargs.items())
                    + [("state_seq", ("in_progress", "failed")), ("op_type", "rm")]
                )
            )
        )
    )
    with setup_entry_point_cli(
        ("pubtools_iib", "console_scripts", "pubtools-iib-remove-operators"),
        "pubtools-iib-remove-operators",
        fixture_common_iib_op_args + ["--operator", "1", "--skip-quay"],
        {
            "PULP_PASSWORD": "pulp-password",
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        try:
            entry_func()
            assert False, "Should have raised SystemError"
        except SystemExit:
            pass

    assert fixture_pushcollector.items == [
        operator_1_push_item_delete_pending,
        operator_1_push_item_delete_notpushed,
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
        {
            "PULP_PASSWORD": "pulp-password",
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        retval = entry_func(
            ["cmd"] + fixture_common_iib_op_args + ["--operator", "1", "--skip-quay"]
        )

    assert isinstance(retval, IIBBuildDetailsModel)

    remove_operators_mock_calls_tester(
        fixture_iib_client,
        fixture_pulplib_repo_sync,
        fixture_pulplib_repo_publish,
        fixture_iib_krb_auth,
    )


def test_invalid_op(fixture_common_iib_op_args):
    try:
        _iib_op_main((), "invalid-op")
        assert False, "Should have raised"
    except ValueError:
        pass


def test_add_bundles_push_to_quay_all_args(
    caplog,
    capsys,
    fixture_iib_client,
    fixture_pulp_client,
    fixture_iib_krb_auth,
    fixture_pulplib_repo_publish,
    fixture_pulplib_repo_sync,
    fixture_container_image_repo,
    fixture_common_iib_op_args,
    fixture_push_to_quay_args,
    fixture_pubtools_quay,
    fixture_pushcollector,
):

    repo = fixture_container_image_repo
    fixture_pulp_client.return_value.search_repository.return_value = [repo]
    fixture_pulp_client.return_value.get_repository.return_value = repo
    with setup_entry_point_py(
        ("pubtools_iib", "console_scripts", "pubtools-iib-add-bundles"),
        {
            "PULP_PASSWORD": "pulp-password",
            "CNR_TOKEN": "cnr_token",
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
            "QUAY_PASSWORD": "quay-password",
            "SSH_PASSWORD": "ssh-password",
        },
    ) as entry_func:
        # --skip-pulp not specified
        retval = entry_func(
            ["cmd"]
            + fixture_common_iib_op_args
            + ["--bundle", "bundle1"]
            + fixture_push_to_quay_args
        )

    assert isinstance(retval, IIBBuildDetailsModel)

    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        cnr_token="cnr_token",
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
    )
    fixture_pulplib_repo_sync.assert_not_called()
    fixture_pulplib_repo_publish.assert_not_called()

    task_id = retval.id
    url_msg = "IIB details: https://{}/api/v1/builds/{}".format(
        FIXTURE_IIB_SERVER, task_id
    )
    assert url_msg in caplog.messages

    # neither build details nor anything else dumped into stdout
    captured = capsys.readouterr()
    assert not captured.out

    fixture_pubtools_quay.assert_called_once()
    called_args = fixture_pubtools_quay.call_args[0][0]
    assert called_args.source_ref == "feed.com/index/image:tag"
    assert called_args.dest_ref == ["some-repo:tag"]
    assert called_args.all_arch
    assert called_args.quay_user == "some-user"
    assert called_args.quay_password == "quay-password"
    assert called_args.remote_exec
    assert called_args.ssh_remote_host == "some-host"
    assert called_args.ssh_remote_host_port == 2222
    assert called_args.ssh_reject_unknown_host
    assert called_args.ssh_username == "ssh-user"
    assert called_args.ssh_password == "ssh-password"
    assert called_args.ssh_key_filename == "/path/to/ssh/file.crt"
    assert called_args.send_umb_msg
    assert called_args.umb_url == ["some-umb-url:5555"]
    assert called_args.umb_cert == "/some/path.crt"
    assert called_args.umb_client_key == "/some/path.key"
    assert called_args.umb_ca_cert == "some/cacert.crt"
    assert called_args.umb_topic == "some-topic"

    print(fixture_pushcollector.items)
    assert fixture_pushcollector.items == [
        operator_quay_push_item_pending,
        operator_quay_push_item_pushed,
    ]
