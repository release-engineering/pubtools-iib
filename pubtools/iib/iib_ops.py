import json
import os
import logging
import sys

from .utils import (
    setup_iib_client,
    setup_pulp_client,
    setup_arg_parser,
    setup_entry_point_cli,
)
from iiblib.iib_build_details_model import AddModel

from pubtools import pulplib
import pushcollector

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

CMD_ARGS = {
    ("--pulp-url",): {
        "group": "Pulp environment",
        "help": "Pulp server URL",
        "required": False,
        "type": str,
    },
    ("--pulp-user",): {
        "group": "Pulp environment",
        "help": "Pulp username",
        "required": False,
        "type": str,
    },
    ("--pulp-password",): {
        "group": "Pulp environment",
        "help": "Pulp password (or set PULP_PASSWORD environment variable)",
        "required": False,
        "type": str,
        "env_variable": "PULP_PASSWORD",
    },
    ("--pulp-insecure",): {
        "group": "Pulp environment",
        "help": "Allow unverified HTTPS connection to Pulp",
        "required": False,
        "type": bool,
    },
    ("--pulp-repository",): {
        "group": "Pulp environment",
        "help": "Pulp repository for publishing index image",
        "required": False,
        "type": str,
        "default": "redhat-operators",
    },
    ("--iib-insecure",): {
        "group": "IIB service",
        "help": "Allow unverified HTTPS connection to IIB",
        "required": False,
        "type": bool,
    },
    ("--iib-server",): {
        "group": "IIB service",
        "help": "IIB service hostname",
        "required": True,
        "type": str,
    },
    ("--iib-krb-principal",): {
        "group": "IIB service",
        "help": "IIB kerberos principal in form: name@REALM",
        "required": True,
        "type": str,
    },
    ("--iib-krb-ktfile",): {
        "group": "IIB service",
        "help": "IIB kerberos client keytab",
        "required": False,
        "type": str,
    },
    ("--iib-cnr-token",): {
        "group": "IIB service",
        "help": "Auth token for quay.io (or set CNR_TOKEN environment variable)",
        "required": False,
        "type": str,
        "env_variable": "CNR_TOKEN",
    },
    ("--index-image",): {
        "group": "IIB service",
        "help": "<hostname>/<namespace>/<image>:<tag> of index image to rebuild",
        "required": False,
        "type": str,
    },
    ("--binary-image",): {
        "group": "IIB service",
        "help": "<hostname>/<namespace>/<image>:<tag> of binary image",
        "required": False,
        "type": str,
    },
    ("--arch",): {
        "group": "IIB service",
        "help": "architecture to rebuild",
        "required": False,
        "type": str,
        "action": "append",
    },
    ("--overwrite-from-index",): {
        "group": "IIB service",
        "help": (
            "overwrite from_index_image as output. If this is true,"
            " overwrite-from-index-token should also be specified."
        ),
        "required": False,
        "type": bool,
    },
    ("--overwrite-from-index-token",): {
        "group": "IIB service",
        "help": (
            "destination repo token to overwrite from_index_image"
            "If this is specified, overwrite-from-index must be set to True."
            "Or set the OVERWRITE_FROM_INDEX_TOKEN environment variable."
        ),
        "required": False,
        "type": str,
        "env_variable": "OVERWRITE_FROM_INDEX_TOKEN",
    },
    ("--skip-pulp",): {
        "group": "IIB service",
        "help": "Skip operations on pulp",
        "required": False,
        "type": bool,
    },
    ("--skip-quay",): {
        "group": "IIB service",
        "help": "Skip pushing to Quay.",
        "required": False,
        "type": bool,
    },
    ("--quay-dest-repo",): {
        "group": "IIB service",
        "help": "Destination repository for push to Quay. Tag will be provided by IIB build.",
        "required": False,
        "type": str,
    },
    ("--quay-user",): {
        "group": "IIB service",
        "help": "Username for Quay login.",
        "required": False,
        "type": str,
    },
    ("--quay-password",): {
        "group": "IIB service",
        "help": "Password for Quay. Can be specified by env variable QUAY_PASSWORD.",
        "required": False,
        "type": str,
        "env_variable": "QUAY_PASSWORD",
    },
    ("--quay-remote-exec",): {
        "group": "IIB service",
        "help": "Flag of whether the quay tag commands should be executed on a remote server.",
        "required": False,
        "type": bool,
    },
    ("--quay-ssh-remote-host",): {
        "group": "IIB service",
        "help": "Hostname for Quay tag remote execution.",
        "required": False,
        "type": str,
    },
    ("--quay-ssh-remote-host-port",): {
        "group": "IIB service",
        "help": "Port of the remote host",
        "required": False,
        "type": int,
    },
    ("--quay-ssh-reject-unknown-host",): {
        "group": "IIB service",
        "help": "Flag of whether to reject an SSH host when it's not found among known hosts.",
        "required": False,
        "type": bool,
    },
    ("--quay-ssh-username",): {
        "group": "IIB service",
        "help": "Username for SSH connection. Defaults to local username.",
        "required": False,
        "type": str,
    },
    ("--quay-ssh-password",): {
        "group": "IIB service",
        "help": "Password for SSH. Will only be used if key-based validation is not available. "
        "Can be specified by env variable SSH_PASSWORD",
        "required": False,
        "type": str,
        "env_variable": "SSH_PASSWORD",
    },
    ("--quay-ssh-key-filename",): {
        "group": "IIB service",
        "help": "Path to the private key file for SSH authentication.",
        "required": False,
        "type": str,
    },
    ("--quay-send-umb-msg",): {
        "group": "IIB service",
        "help": "Flag of whether to send a UMB message after performing a Quay push",
        "required": False,
        "type": bool,
    },
    ("--quay-umb-url",): {
        "group": "IIB service",
        "help": "UMB URL. More than one can be specified.",
        "required": False,
        "type": str,
        "action": "append",
    },
    ("--quay-umb-cert",): {
        "group": "IIB service",
        "help": "Path to the UMB certificate for SSL authentication.",
        "required": False,
        "type": str,
    },
    ("--quay-umb-client-key",): {
        "group": "IIB service",
        "help": "Path to the UMB private key for accessing the certificate.",
        "required": False,
        "type": str,
    },
    ("--quay-umb-ca-cert",): {
        "group": "IIB service",
        "help": "Path to the UMB CA certificate.",
        "required": False,
        "type": str,
    },
    ("--quay-umb-topic",): {
        "group": "IIB service",
        "help": "UMB topic to send the message to.",
        "required": False,
        "type": str,
    },
}

ADD_CMD_ARGS = CMD_ARGS.copy()
ADD_CMD_ARGS[("--bundle",)] = {
    "group": "IIB service",
    "help": "<hostname>/<namespace>/<image>:<tag> of bundle",
    "required": False,
    "type": str,
    "action": "append",
}
ADD_CMD_ARGS[("--iib-legacy-org",)] = {
    "group": "IIB service",
    "help": "Organization for legacy registry",
    "required": False,
    "type": str,
}
ADD_CMD_ARGS[("--deprecation-list",)] = {
    "group": "IIB service",
    "help": "Comma separated list of deprecated bundles",
    "required": False,
    "type": str,
}

RM_CMD_ARGS = CMD_ARGS.copy()
RM_CMD_ARGS[("--operator",)] = {
    "group": "IIB service",
    "help": "operator name",
    "required": True,
    "type": str,
    "action": "append",
}


def push_items_from_build(build_details, state, destination_repository):
    ret = []
    if build_details.request_type == "add":
        for operator, bundles in build_details.bundle_mapping.items():
            for bundle in bundles:
                item = {
                    "state": state,
                    "origin": build_details.from_index or "scratch",
                    "src": bundle,
                    "filename": operator,
                    "dest": destination_repository,
                    "build": build_details.index_image,
                    "signing_key": None,
                    "checksums": None,
                }
                ret.append(item)
    elif build_details.request_type == "rm":
        for operator in build_details.removed_operators:
            item = {
                "state": state,
                "origin": build_details.from_index or "scratch",
                "src": None,
                "filename": operator,
                "dest": destination_repository,
                "build": build_details.index_image,
                "signing_key": None,
                "checksums": None,
            }
            ret.append(item)

    return ret


def process_parsed_args(parsed_args, args):
    for aliases, arg_data in args.items():
        named_alias = [
            x.lstrip("-").replace("-", "_") for x in aliases if x.startswith("--")
        ][0]
        if arg_data.get("env_variable"):
            if not getattr(parsed_args, named_alias) and os.environ.get(
                arg_data["env_variable"]
            ):
                setattr(
                    parsed_args, named_alias, os.environ.get(arg_data["env_variable"])
                )
    return parsed_args


def validate_args(args, operation=None):
    """
    Validate the correctness of input arguments.

    Args:
        args (argparse.Namespace):
            Arguments from the command line
        operation (str):
            Type of operation performed. Can be 'add_bundles' or 'remove_operators'.
    """

    if not args.skip_pulp and args.skip_quay:
        if not args.pulp_url:
            raise ValueError("If pushing to Pulp, '--pulp-url' must be specified.")
        if not args.pulp_user:
            raise ValueError("If pushing to Pulp, '--pulp-user' must be specified.")
        if not args.pulp_password:
            raise ValueError(
                "If pushing to Pulp, '--pulp-password' must be specified "
                "(or via PULP_PASSWORD env variable)."
            )

    if not args.skip_quay:
        if not args.quay_dest_repo:
            raise ValueError("If pushing to Quay, destination repo must be specified.")
        if ":" in args.quay_dest_repo:
            raise ValueError(
                "Quay destination repo contains a tag or digest. "
                "Please specify only a repo."
            )
        if (args.quay_user and not args.quay_password) or (
            args.quay_password and not args.quay_user
        ):
            raise ValueError(
                "Both Quay user and password must be present when attempting to log in."
            )
        if args.quay_remote_exec and not args.quay_ssh_remote_host:
            raise ValueError(
                "Remote host is missing when remote execution was specified."
            )
        if args.quay_send_umb_msg and not args.quay_umb_url:
            raise ValueError(
                "UMB URL must be specified if sending a UMB message was requested (for Quay push)."
            )
        if args.quay_send_umb_msg and not args.quay_umb_cert:
            raise ValueError(
                "A path to a client certificate must be provided "
                "when sending a UMB message. (for Quay push)."
            )


def make_pubtools_quay_args(args, build_details):
    """
    Construct a pubtools-quay command containing all the necessary arguments.

    Args:
        args (argparse.Namespace):
            Input command line arguments.
        build_details (IIBBuildDetailsModel):
            Details of IIB build.
    Return ((list, dict)):
        Tuple of command line arguments and environment variable arguments
    """
    _, tag = build_details.index_image.split(":", 1)
    dest_image = "{0}:{1}".format(args.quay_dest_repo, tag)

    cmd_args = [
        "--source-ref",
        build_details.index_image,
        "--dest-ref",
        dest_image,
        "--all-arch",
    ]
    if args.quay_user:
        cmd_args += ["--quay-user", args.quay_user]
    if args.quay_remote_exec:
        cmd_args.append("--remote-exec")
    if args.quay_ssh_remote_host:
        cmd_args += ["--ssh-remote-host", args.quay_ssh_remote_host]
    if args.quay_ssh_remote_host_port:
        cmd_args += ["--ssh-remote-host-port", str(args.quay_ssh_remote_host_port)]
    if args.quay_ssh_reject_unknown_host:
        cmd_args.append("--ssh-reject-unknown-host")
    if args.quay_ssh_username:
        cmd_args += ["--ssh-username", args.quay_ssh_username]
    if args.quay_ssh_key_filename:
        cmd_args += ["--ssh-key-filename", args.quay_ssh_key_filename]
    if args.quay_send_umb_msg:
        cmd_args.append("--send-umb-msg")
    if args.quay_umb_url:
        umb_urls = (
            args.quay_umb_url
            if isinstance(args.quay_umb_url, list)
            else [args.quay_umb_url]
        )
        for umb_url in umb_urls:
            cmd_args += ["--umb-url", umb_url]
    if args.quay_umb_cert:
        cmd_args += ["--umb-cert", args.quay_umb_cert]
    if args.quay_umb_client_key:
        cmd_args += ["--umb-client-key", args.quay_umb_client_key]
    if args.quay_umb_ca_cert:
        cmd_args += ["--umb-ca-cert", args.quay_umb_ca_cert]
    if args.quay_umb_topic:
        cmd_args += ["--umb-topic", args.quay_umb_topic]

    env_args = {}
    if args.quay_password:
        env_args["QUAY_PASSWORD"] = args.quay_password
    if args.quay_ssh_password:
        env_args["SSH_PASSWORD"] = args.quay_ssh_password

    return (cmd_args, env_args)


def push_to_pulp(args, pulp_c, build_details, pc, items_final_state):
    """
    Push the created index image to pulp.

    Args:
        args (argparse.Namespace):
            Input command line arguments.
        pulp_c (pulplib.Client):
            Pulp client instance.
        build_details (IIBBuildDetailsModel):
            Details of IIB build.
        pc (pushcollector.Collector):
            Push collector instance.
        items_final_state (str):
            Final state of the items.
    """
    LOG.debug("Getting pulp repository: %s", args.pulp_repository)
    container_repo = pulp_c.get_repository(args.pulp_repository)
    feed, path = build_details.index_image.split("/", 1)
    upstream_name, tag = path.split(":")
    LOG.info("Syncing pulp repository with %s", build_details.index_image)
    container_repo.sync(
        pulplib.ContainerSyncOptions(
            feed="https://%s" % feed, upstream_name=upstream_name, tags=[tag]
        )
    ).result()
    LOG.info("Publishing repository %s", args.pulp_repository)
    publish_args = [
        "--pulp-url",
        args.pulp_url,
        "--pulp-user",
        args.pulp_user,
        "--repo-ids",
        args.pulp_repository,
    ]
    env_args = {"PULP_PASSWORD": args.pulp_password}
    if args.pulp_insecure:
        publish_args.append("--pulp-insecure")

    with setup_entry_point_cli(
        ("pubtools-pulp", "console_scripts", "pubtools-pulp-publish"),
        "pubtools-pulp-publish",
        publish_args,
        env_args,
    ) as entry_func:
        entry_func()

    push_items = push_items_from_build(
        build_details, items_final_state, args.pulp_repository
    )
    LOG.info("IIB push to pulp finished")
    pc.update_push_items(push_items)


def push_to_quay(args, build_details, pc, items_final_state):
    """
    Push the created index image to Quay.

    Args:
        args (argparse.Namespace):
            Input command line arguments.
        build_details (IIBBuildDetailsModel):
            Details of IIB build.
        pc (pushcollector.Collector):
            Push collector instance.
        items_final_state (str):
            Final state of the items.
    """
    LOG.debug("Pushing image to Quay repository: %s", args.quay_dest_repo)
    _, tag = build_details.index_image.split(":", 1)
    dest_image = "{0}:{1}".format(args.quay_dest_repo, tag)
    tag_args, env_args = make_pubtools_quay_args(args, build_details)

    with setup_entry_point_cli(
        ("pubtools-quay", "console_scripts", "pubtools-quay-tag-image"),
        "pubtools-quay-tag-image",
        tag_args,
        env_args,
    ) as entry_func:
        entry_func()

    push_items = push_items_from_build(
        build_details, items_final_state, args.quay_dest_repo
    )
    LOG.info("IIB push to quay finished")
    pc.update_push_items(push_items)


def _iib_op_main(args, operation=None, items_final_state="PUSHED"):
    if operation not in ("add_bundles", "remove_operators"):
        raise ValueError("Must set iib operation")

    pc = pushcollector.Collector.get()
    if not args.skip_pulp:
        LOG.debug("Initializing pulp client")
        pulp_c = setup_pulp_client(args)
    LOG.debug("Initializing iib client")
    iib_c = setup_iib_client(args)
    LOG.debug("Request to rebuild %s", args.index_image)

    bundle_op = getattr(iib_c, operation)

    extra_args = {}
    if operation == "add_bundles":
        extra_args = {"cnr_token": args.iib_cnr_token}
        if args.iib_legacy_org:
            extra_args["organization"] = args.iib_legacy_org
        if args.deprecation_list:
            extra_args["deprecation_list"] = args.deprecation_list.split(",")

    if args.binary_image:
        extra_args["binary_image"] = args.binary_image

    if args.overwrite_from_index:
        extra_args["overwrite_from_index"] = args.overwrite_from_index

    if args.overwrite_from_index_token:
        extra_args["overwrite_from_index_token"] = args.overwrite_from_index_token

    build_details = bundle_op(
        args.index_image,
        args.bundle if operation == "add_bundles" else args.operator,
        args.arch,
        **extra_args
    )

    destination_repository = (
        args.pulp_repository if args.skip_quay else args.quay_dest_repo
    )
    push_items = push_items_from_build(build_details, "PENDING", destination_repository)
    LOG.debug("Updating push items")
    pc.update_push_items(push_items)

    build_details = iib_c.wait_for_build(build_details)

    build_details_url = _make_iib_build_details_url(args.iib_server, build_details.id)
    LOG.info("IIB details: %s", build_details_url)

    if build_details.state == "failed":
        LOG.error("IIB operation failed")
        push_items = push_items_from_build(
            build_details, "NOTPUSHED", destination_repository
        )
        pc.update_push_items(push_items)
        sys.exit(1)

    LOG.info("IIB build finished")
    # If both pulp and quay are enabled, only push to quay
    if not args.skip_quay:
        push_to_quay(args, build_details, pc, items_final_state)
        return build_details

    if not args.skip_pulp:
        push_to_pulp(args, pulp_c, build_details, pc, items_final_state)
        return build_details

    return build_details


def make_add_bundles_parser():
    return setup_arg_parser(ADD_CMD_ARGS)


def make_rm_operators_parser():
    return setup_arg_parser(RM_CMD_ARGS)


def add_bundles_main(sysargs=None):
    parser = make_add_bundles_parser()
    if sysargs:
        args = parser.parse_args(sysargs[1:])
    else:
        args = parser.parse_args()
    process_parsed_args(args, ADD_CMD_ARGS)
    validate_args(args, "add_bundles")

    return _iib_op_main(args, "add_bundles")


def remove_operators_main(sysargs=None):
    parser = make_rm_operators_parser()
    if sysargs:
        args = parser.parse_args(sysargs[1:])
    else:
        args = parser.parse_args()
    process_parsed_args(args, RM_CMD_ARGS)
    validate_args(args, "remove_operators")

    return _iib_op_main(args, "remove_operators", "DELETED")


def _make_iib_build_details_url(host, task_id):
    return "https://%s/api/v1/builds/%s" % (host, task_id)
