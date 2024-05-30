import contextlib
import logging
import mock
import pkg_resources
import pytest
import os

from pubtools.iib.utils import setup_entry_point_cli
from pubtools.iib.iib_ops import _iib_op_main, print_error_message

import pushcollector
import requests_mock


from iiblib.iib_build_details_model import IIBBuildDetailsModel
from more_executors.futures import f_return

from utils import FakeTaskManager, FakeCollector


FIXTURE_IIB_SERVER = "iib-server"


fake_tm = FakeTaskManager()

operator_1_push_item_pending = {
    "state": "PENDING",
    "origin": "index-image",
    "filename": "operator-1",
    "build": "feed.com/index/image:tag",
    "dest": "redhat-operator-index",
    "signing_key": None,
    "checksums": None,
    "src": "bundle1",
}
operator_1_push_item_notpushed = operator_1_push_item_pending.copy()
operator_1_push_item_notpushed["state"] = "NOTPUSHED"
operator_1_push_item_pushed = operator_1_push_item_pending.copy()
operator_1_push_item_pushed["state"] = "PUSHED"

operator_1_push_item_delete_pending = {
    "state": "PENDING",
    "origin": "index-image",
    "filename": "operator-1",
    "build": "feed.com/index/image:tag",
    "dest": "redhat-operator-index",
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
def fixture_common_iib_op_args():
    return [
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
        "--build-tag",
        "extra-tag-1",
        "--build-tag",
        "extra-tag-2",
    ]


def add_bundles_mock_calls_tester(
    fixture_iib_client,
    fixture_iib_krb_auth,
):
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
        deprecation_list=["bundle1"],
        build_tags=["extra-tag-1", "extra-tag-2"],
    )
    fixture_iib_client.assert_called_once_with(
        "iib-server",
        auth=fixture_iib_krb_auth.return_value,
        ssl_verify=False,
        wait_for_build_timeout=30,
    )


def add_bundles_mock_calls_tester_check_related_images(
    fixture_iib_client,
    fixture_iib_krb_auth,
):
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
        build_tags=["extra-tag-1", "extra-tag-2"],
        check_related_images=True,
    )
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )


def add_bundles_mock_calls_tester_empty_deprecation_list(
    fixture_iib_client,
    fixture_iib_krb_auth,
):
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
        build_tags=["extra-tag-1", "extra-tag-2"],
    )
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )


def add_bundles_mock_calls_tester_deprecation_bundles(
    fixture_iib_client,
    fixture_iib_krb_auth,
):
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
        deprecation_list=["bundle1", "bundle2"],
        build_tags=["extra-tag-1", "extra-tag-2"],
    )
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )


def add_bundles_mock_calls_tester_not_called(
    fixture_iib_client,
    fixture_iib_krb_auth,
):
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
        build_tags=["extra-tag-1", "extra-tag-2"],
    )
    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )


def remove_operators_mock_calls_tester_not_called(
    fixture_iib_client,
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
        build_tags=["extra-tag-1", "extra-tag-2"],
    )


def remove_operators_mock_calls_tester(
    fixture_iib_client,
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
        build_tags=["extra-tag-1", "extra-tag-2"],
    )


@pytest.mark.parametrize(
    "extra_args,push_items,mock_calls_tester",
    [
        (
            ["--deprecation-list", "bundle1,bundle2"],
            [operator_1_push_item_pending, operator_1_push_item_pushed],
            add_bundles_mock_calls_tester_deprecation_bundles,
        ),
        (
            ["--deprecation-list", "bundle1", "--build-timeout", "30"],
            [operator_1_push_item_pending, operator_1_push_item_pushed],
            add_bundles_mock_calls_tester,
        ),
        (
            ["--deprecation-list", ""],
            [operator_1_push_item_pending, operator_1_push_item_pushed],
            add_bundles_mock_calls_tester_empty_deprecation_list,
        ),
        (
            ["--check-related-images"],
            [operator_1_push_item_pending, operator_1_push_item_pushed],
            add_bundles_mock_calls_tester_check_related_images,
        ),
    ],
)
def test_add_bundles_cli(
    fixture_iib_client,
    fixture_iib_krb_auth,
    fixture_common_iib_op_args,
    fixture_pushcollector,
    extra_args,
    push_items,
    mock_calls_tester,
):
    with setup_entry_point_cli(
        ("pubtools_iib", "console_scripts", "pubtools-iib-add-bundles"),
        "pubtools-iib-add-bundle",
        fixture_common_iib_op_args + ["--bundle", "bundle1"] + extra_args,
        {
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        entry_func()
    assert fixture_pushcollector.items == push_items
    mock_calls_tester(
        fixture_iib_client,
        fixture_iib_krb_auth,
    )


@mock.patch("pubtools.iib.iib_ops.print_error_message")
def test_add_bundles_cli_error(
    mock_print_error_message,
    fixture_iib_client,
    fixture_iib_krb_auth,
    fixture_common_iib_op_args,
    fixture_pushcollector,
):
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
        fixture_common_iib_op_args + ["--bundle", "bundle1"],
        {
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

    mock_print_error_message.assert_called_once_with(
        "https://iib-server/api/v1/builds/task-4"
    )


def test_add_bundles_py(
    caplog,
    capsys,
    fixture_iib_client,
    fixture_iib_krb_auth,
    fixture_common_iib_op_args,
):
    caplog.set_level(logging.INFO)
    with setup_entry_point_py(
        ("pubtools_iib", "console_scripts", "pubtools-iib-add-bundles"),
        {
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        retval = entry_func(
            ["cmd"]
            + fixture_common_iib_op_args
            + ["--bundle", "bundle1", "--check-related-images"]
        )

    assert isinstance(retval, IIBBuildDetailsModel)

    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1"],
        ["arch"],
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
        build_tags=["extra-tag-1", "extra-tag-2"],
        check_related_images=True,
    )

    task_id = retval.id
    url_msg = "IIB details: https://{}/api/v1/builds/{}".format(
        FIXTURE_IIB_SERVER, task_id
    )
    assert url_msg in [r.getMessage() for r in caplog.records]

    # neither build details nor anything else dumped into stdout
    captured = capsys.readouterr()
    assert not captured.out


def test_add_bundles_py_multiple_bundles(
    fixture_iib_client,
    fixture_iib_krb_auth,
    fixture_common_iib_op_args,
):
    with setup_entry_point_py(
        ("pubtools_iib", "console_scripts", "pubtools-iib-add-bundles"),
        {
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        retval = entry_func(
            ["cmd"]
            + fixture_common_iib_op_args
            + ["--bundle", "bundle1", "--bundle", "bundle2"]
        )

    assert isinstance(retval, IIBBuildDetailsModel)

    fixture_iib_client.assert_called_once_with(
        "iib-server", auth=fixture_iib_krb_auth.return_value, ssl_verify=False
    )
    fixture_iib_client.return_value.add_bundles.assert_called_once_with(
        "index-image",
        ["bundle1", "bundle2"],
        ["arch"],
        binary_image="binary-image",
        overwrite_from_index=True,
        overwrite_from_index_token="overwrite_from_index_token",
        build_tags=["extra-tag-1", "extra-tag-2"],
    )


@pytest.mark.parametrize(
    "extra_args,push_items,mock_calls_tester",
    [
        (
            [],
            [operator_1_push_item_delete_pending, operator_1_push_item_deleted],
            remove_operators_mock_calls_tester,
        ),
    ],
)
def test_remove_operators_cli(
    fixture_iib_client,
    fixture_iib_krb_auth,
    fixture_common_iib_op_args,
    fixture_pushcollector,
    extra_args,
    push_items,
    mock_calls_tester,
):
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
        fixture_common_iib_op_args + ["--operator", "1"] + extra_args,
        {
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        entry_func()
    assert fixture_pushcollector.items == push_items
    mock_calls_tester(
        fixture_iib_client,
        fixture_iib_krb_auth,
    )


@mock.patch("pubtools.iib.iib_ops.print_error_message")
def test_remove_operators_cli_error(
    mock_print_error_message,
    fixture_iib_client,
    fixture_iib_krb_auth,
    fixture_common_iib_op_args,
    fixture_pushcollector,
):
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
        fixture_common_iib_op_args + ["--operator", "1"],
        {
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

    mock_print_error_message.assert_called_once_with(
        "https://iib-server/api/v1/builds/task-8"
    )


def test_remove_operators_py(
    fixture_iib_client,
    fixture_iib_krb_auth,
    fixture_common_iib_op_args,
):
    with setup_entry_point_py(
        ("pubtools_iib", "console_scripts", "pubtools-iib-remove-operators"),
        {
            "OVERWRITE_FROM_INDEX_TOKEN": "overwrite_from_index_token",
        },
    ) as entry_func:
        retval = entry_func(["cmd"] + fixture_common_iib_op_args + ["--operator", "1"])

    assert isinstance(retval, IIBBuildDetailsModel)

    remove_operators_mock_calls_tester(
        fixture_iib_client,
        fixture_iib_krb_auth,
    )


def test_invalid_op(fixture_common_iib_op_args):
    try:
        _iib_op_main((), "invalid-op")
        assert False, "Should have raised"
    except ValueError:
        pass


def test_print_error_message(caplog):
    caplog.set_level(logging.INFO)
    with requests_mock.Mocker() as m:
        m.register_uri(
            "GET",
            "https://iib-test.com/api/v1/builds/5",
            json={"state_reason": "Generic IIB error"},
        )

        print_error_message("https://iib-test.com/api/v1/builds/5")

        assert (
            caplog.records[0].message
            == "IIB Failed with the error: 'Generic IIB error'"
        )
        assert caplog.records[1].message == (
            "Please check the full logs at https://iib-test.com/api/v1/builds/5/logs"
        )

        assert len(m.request_history) == 1
        assert m.request_history[0].url == "https://iib-test.com/api/v1/builds/5"
