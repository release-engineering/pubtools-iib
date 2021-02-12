import mock
import pytest

from pubtools.iib import iib_ops


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_basic_passed(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--skip-quay",
        "--skip-pulp",
    ]
    iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])
    called_args, _ = mock_main.call_args

    assert called_args[0].iib_server == "some-server.com"
    assert called_args[0].iib_krb_principal == "some-name"
    assert called_args[0].bundle == ["some-bundle"]
    assert called_args[0].skip_quay
    assert called_args[0].skip_pulp

    iib_ops.remove_operators_main(required_args + ["--operator", "some-operator"])
    called_args, _ = mock_main.call_args

    assert called_args[0].iib_server == "some-server.com"
    assert called_args[0].iib_krb_principal == "some-name"
    assert called_args[0].operator == ["some-operator"]
    assert called_args[0].skip_quay
    assert called_args[0].skip_pulp


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_missing_operator(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--skip-quay",
        "--skip-pulp",
    ]

    with pytest.raises(SystemExit) as system_error:
        iib_ops.remove_operators_main(required_args)

    assert system_error.type == SystemExit
    assert system_error.value.code == 2
    mock_main.assert_not_called()


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_pulp_success(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--skip-quay",
        "--pulp-url",
        "pulp-url.com",
        "--pulp-user",
        "some-user",
        "--pulp-password",
        "some-password",
        "--pulp-repository",
        "some-repository",
    ]
    iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])
    called_args, _ = mock_main.call_args

    assert called_args[0].iib_server == "some-server.com"
    assert called_args[0].iib_krb_principal == "some-name"
    assert called_args[0].bundle == ["some-bundle"]
    assert called_args[0].skip_quay
    assert not called_args[0].skip_pulp
    assert called_args[0].pulp_url == "pulp-url.com"
    assert called_args[0].pulp_user == "some-user"
    assert called_args[0].pulp_password == "some-password"
    assert called_args[0].pulp_repository == "some-repository"


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_pulp_missing_url(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--skip-quay",
        "--pulp-user",
        "some-user",
        "--pulp-password",
        "some-password",
        "--pulp-repository",
        "some-repository",
    ]
    with pytest.raises(ValueError, match="If pushing to Pulp, '--pulp-url'.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_pulp_missing_user(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--skip-quay",
        "--pulp-url",
        "pulp-url.com",
        "--pulp-password",
        "some-password",
        "--pulp-repository",
        "some-repository",
    ]
    with pytest.raises(ValueError, match="If pushing to Pulp, '--pulp-user'.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_pulp_missing_password(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--skip-quay",
        "--pulp-url",
        "pulp-url.com",
        "--pulp-user",
        "some-user",
        "--pulp-repository",
        "some-repository",
    ]
    with pytest.raises(ValueError, match="If pushing to Pulp, '--pulp-password'.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_quay_success(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--skip-pulp",
        "--quay-dest-repo",
        "some-repo",
        "--quay-user",
        "some-user",
        "--quay-password",
        "some-password",
        "--quay-remote-exec",
        "--quay-ssh-remote-host",
        "some-host",
        "--quay-send-umb-msg",
        "--quay-umb-url",
        "some-umb-url:5555",
        "--quay-umb-cert",
        "/some/path.crt",
    ]
    iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])
    called_args, _ = mock_main.call_args
    print(called_args[0])

    assert called_args[0].iib_server == "some-server.com"
    assert called_args[0].iib_krb_principal == "some-name"
    assert called_args[0].bundle == ["some-bundle"]
    assert called_args[0].skip_pulp
    assert not called_args[0].skip_quay
    assert called_args[0].quay_user == "some-user"
    assert called_args[0].quay_password == "some-password"
    assert called_args[0].quay_remote_exec
    assert called_args[0].quay_ssh_remote_host == "some-host"
    assert called_args[0].quay_send_umb_msg
    assert called_args[0].quay_umb_url == ["some-umb-url:5555"]
    assert called_args[0].quay_umb_cert == "/some/path.crt"


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_quay_success_not_skip_pulp(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--quay-dest-repo",
        "some-repo",
        "--quay-user",
        "some-user",
        "--quay-password",
        "some-password",
        "--quay-remote-exec",
        "--quay-ssh-remote-host",
        "some-host",
        "--quay-send-umb-msg",
        "--quay-umb-url",
        "some-umb-url:5555",
        "--quay-umb-cert",
        "/some/path.crt",
    ]
    iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])
    called_args, _ = mock_main.call_args

    assert called_args[0].iib_server == "some-server.com"
    assert called_args[0].iib_krb_principal == "some-name"
    assert called_args[0].bundle == ["some-bundle"]
    assert not called_args[0].skip_pulp
    assert not called_args[0].skip_quay
    assert called_args[0].quay_user == "some-user"
    assert called_args[0].quay_password == "some-password"
    assert called_args[0].quay_remote_exec
    assert called_args[0].quay_ssh_remote_host == "some-host"
    assert called_args[0].quay_send_umb_msg
    assert called_args[0].quay_umb_url == ["some-umb-url:5555"]
    assert called_args[0].quay_umb_cert == "/some/path.crt"


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_quay_fail_missing_quay_dest_ref(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--quay-user",
        "some-user",
        "--quay-password",
        "some-password",
        "--quay-remote-exec",
        "--quay-ssh-remote-host",
        "some-host",
        "--quay-send-umb-msg",
        "--quay-umb-url",
        "some-umb-url:5555",
        "--quay-umb-cert",
        "/some/path.crt",
    ]
    with pytest.raises(ValueError, match="If pushing to Quay, destination.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_quay_fail_wrong_quay_dest_ref(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--quay-dest-repo",
        "some-repo:1",
        "--quay-user",
        "some-user",
        "--quay-password",
        "some-password",
        "--quay-remote-exec",
        "--quay-ssh-remote-host",
        "some-host",
        "--quay-send-umb-msg",
        "--quay-umb-url",
        "some-umb-url:5555",
        "--quay-umb-cert",
        "/some/path.crt",
    ]
    with pytest.raises(ValueError, match="Quay destination repo contains a tag.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_quay_fail_missing_user(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--quay-dest-repo",
        "some-repo",
        "--quay-password",
        "some-password",
        "--quay-remote-exec",
        "--quay-ssh-remote-host",
        "some-host",
        "--quay-send-umb-msg",
        "--quay-umb-url",
        "some-umb-url:5555",
        "--quay-umb-cert",
        "/some/path.crt",
    ]
    with pytest.raises(ValueError, match="Both Quay user and password.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_quay_fail_missing_password(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--quay-dest-repo",
        "some-repo",
        "--quay-user",
        "some-user",
        "--quay-remote-exec",
        "--quay-ssh-remote-host",
        "some-host",
        "--quay-send-umb-msg",
        "--quay-umb-url",
        "some-umb-url:5555",
        "--quay-umb-cert",
        "/some/path.crt",
    ]
    with pytest.raises(ValueError, match="Both Quay user and password.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_quay_fail_missing_ssh_remote_host(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--quay-dest-repo",
        "some-repo",
        "--quay-user",
        "some-user",
        "--quay-password",
        "some-password",
        "--quay-remote-exec",
        "--quay-send-umb-msg",
        "--quay-umb-url",
        "some-umb-url:5555",
        "--quay-umb-cert",
        "/some/path.crt",
    ]
    with pytest.raises(ValueError, match="Remote host is missing.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_quay_fail_missing_umb_url(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--quay-dest-repo",
        "some-repo",
        "--quay-user",
        "some-user",
        "--quay-password",
        "some-password",
        "--quay-remote-exec",
        "--quay-ssh-remote-host",
        "some-host",
        "--quay-send-umb-msg",
        "--quay-umb-cert",
        "/some/path.crt",
    ]
    with pytest.raises(ValueError, match="UMB URL must be specified.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])


@mock.patch("pubtools.iib.iib_ops._iib_op_main")
def test_arg_validation_push_to_quay_fail_missing_umb_cert(mock_main):
    required_args = [
        "dummy",
        "--iib-server",
        "some-server.com",
        "--iib-krb-principal",
        "some-name",
        "--quay-dest-repo",
        "some-repo",
        "--quay-user",
        "some-user",
        "--quay-password",
        "some-password",
        "--quay-remote-exec",
        "--quay-ssh-remote-host",
        "some-host",
        "--quay-send-umb-msg",
        "--quay-umb-url",
        "some-umb-url:5555",
    ]
    with pytest.raises(ValueError, match="A path to a client certificate.*"):
        iib_ops.add_bundles_main(required_args + ["--bundle", "some-bundle"])
