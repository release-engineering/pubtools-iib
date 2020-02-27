import os
import logging
import sys

from .utils import (
    setup_iib_client,
    setup_pulp_client,
    setup_arg_parser,
    setup_entry_point_cli,
)

from pubtools import pulplib
import pushcollector

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

CMD_ARGS = {
    ("--pulp-url",): {
        "group": "Pulp environment",
        "help": "Pulp server URL",
        "required": True,
        "type": str,
    },
    ("--pulp-user",): {
        "group": "Pulp environment",
        "help": "Pulp username",
        "required": True,
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
    ("--iib-legacy-org",): {
        "group": "IIB service",
        "help": "Organization for legacy registry",
        "required": False,
        "type": str,
    },
    ("--index-image",): {
        "group": "IIB service",
        "help": "<hostname>/<namespace>/<image>:<tag> of index image to rebuild",
        "required": True,
        "type": str,
    },
    ("--binary-image",): {
        "group": "IIB service",
        "help": "<hostname>/<namespace>/<image>:<tag> of binary image",
        "required": True,
        "type": str,
    },
    ("--arch",): {
        "group": "IIB service",
        "help": "architecture to rebuild",
        "required": False,
        "type": str,
        "count": "+",
    },
}

ADD_CMD_ARGS = CMD_ARGS.copy()
ADD_CMD_ARGS[("--bundle",)] = {
    "group": "IIB service",
    "help": "<hostname>/<namespace>/<image>:<tag> of bundle",
    "required": True,
    "type": str,
    "count": "+",
}

RM_CMD_ARGS = CMD_ARGS.copy()
RM_CMD_ARGS[("--operator",)] = {
    "group": "IIB service",
    "help": "operator name",
    "required": True,
    "type": str,
    "count": "+",
}


def push_items_from_build(build_details, state, pulp_repository):
    ret = []
    if build_details.request_type == 1:
        for operator, bundles in build_details.bundle_mapping.items():
            for bundle in bundles:
                item = {
                    "state": state,
                    "origin": build_details.from_index,
                    "filename": operator,
                    "file_path": bundle,
                    "repo": pulp_repository,
                    "build": None,
                    "signing_key": None,
                    "checksums": None,
                }
                ret.append(item)
    elif build_details.request_type == 2:
        for operator in build_details.removed_operators:
            item = {
                "state": state,
                "origin": build_details.from_index,
                "filename": operator,
                "file_path": "",
                "repo": pulp_repository,
                "build": None,
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


def _iib_op_main(args, operation=None, items_final_state="PUSHED"):
    if operation not in ("add_bundles", "remove_operators"):
        raise ValueError("Must set iib operation")

    pc = pushcollector.Collector.get()
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

    print(extra_args, bundle_op)
    build_details = bundle_op(
        args.index_image,
        args.binary_image,
        args.bundle if hasattr(args, "bundle") else args.operator,
        args.arch,
        **extra_args
    )

    push_items = push_items_from_build(build_details, "PENDING", args.pulp_repository)
    LOG.debug("Updating push items")
    pc.update_push_items(push_items)

    build_details = iib_c.wait_for_build(build_details)
    if build_details.state == "failed":
        LOG.error("IIB operation failed")
        push_items = push_items_from_build(
            build_details, "NOTPUSHED", args.pulp_repository
        )
        pc.update_push_items(push_items)
        sys.exit(1)

    LOG.info("IIB build finished")
    LOG.debug("Getting pulp repository: %s", args.pulp_repository)
    container_repo = pulp_c.get_repository(args.pulp_repository)
    LOG.info("Syncing pulp repository with %s", build_details.index_image)
    container_repo.sync(
        pulplib.ContainerSyncOptions(feed=build_details.index_image)
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
    LOG.info("IIB push finished")
    pc.update_push_items(push_items)
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

    return _iib_op_main(args, "add_bundles")


def remove_operators_main(sysargs=None):
    parser = make_rm_operators_parser()
    if sysargs:
        args = parser.parse_args(sysargs[1:])
    else:
        args = parser.parse_args()
    process_parsed_args(args, RM_CMD_ARGS)

    return _iib_op_main(args, "remove_operators", "DELETED")
