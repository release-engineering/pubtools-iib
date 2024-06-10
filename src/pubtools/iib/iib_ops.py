import os
import logging
import sys
from typing import Any
from argparse import Namespace, ArgumentParser

import requests
from iiblib.iib_build_details_model import IIBBuildDetailsModel

from .utils import (
    setup_iib_client,
    setup_arg_parser,
    setup_entry_point_cli,
)

import pushcollector

LOG = logging.getLogger("pubtools.iib")


CMD_ARGS = {
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
    ("--build-tag",): {
        "group": "IIB service",
        "help": "extra tags to apply on built index image in temp namespace",
        "required": False,
        "type": str,
        "action": "append",
    },
    ("--build-timeout",): {
        "group": "IIB service",
        "help": "How long to wait for an IIB build before raising timeout error",
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
ADD_CMD_ARGS[("--deprecation-list",)] = {
    "group": "IIB service",
    "help": "Comma separated list of deprecated bundles",
    "required": False,
    "type": str,
}
ADD_CMD_ARGS[("--check-related-images",)] = {
    "group": "IIB service",
    "help": "Flag to indicate if related and depending images of a bundle should be inspected",
    "required": False,
    "type": bool,
}

RM_CMD_ARGS = CMD_ARGS.copy()
RM_CMD_ARGS[("--operator",)] = {
    "group": "IIB service",
    "help": "operator name",
    "required": True,
    "type": str,
    "action": "append",
}


def push_items_from_build(
    build_details: IIBBuildDetailsModel, state: str
) -> list[dict[Any, Any]]:
    ret = []
    if build_details.request_type == "add":
        for operator, bundles in build_details.bundle_mapping.items():
            for bundle in bundles:
                item = {
                    "state": state,
                    "origin": build_details.from_index or "scratch",
                    "src": bundle,
                    "filename": operator,
                    "dest": "redhat-operator-index",
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
                "dest": "redhat-operator-index",
                "build": build_details.index_image,
                "signing_key": None,
                "checksums": None,
            }
            ret.append(item)

    return ret


def process_parsed_args(parsed_args: Namespace, args: dict[Any, Any]) -> Namespace:
    for aliases, arg_data in args.items():
        named_alias = [
            x.lstrip("-").replace("-", "_") for x in aliases if x.startswith("--")
        ][0]
        if arg_data.get("env_variable"):
            if not getattr(parsed_args, named_alias) and os.environ.get(
                arg_data["env_variable"]
            ):
                setattr(
                    parsed_args,
                    named_alias,
                    os.environ.get(arg_data["env_variable"]),
                )
    return parsed_args


def _iib_op_main(
    args: Namespace,
    operation: str | None = None,
    items_final_state: str = "PUSHED",
) -> list[dict[Any, Any]] | Any:
    if operation not in ("add_bundles", "remove_operators"):
        raise ValueError("Must set iib operation")

    pc = pushcollector.Collector.get()
    LOG.debug("Initializing iib client")
    iib_c = setup_iib_client(args)
    LOG.debug("Request to rebuild %s", args.index_image)

    bundle_op = getattr(iib_c, operation)

    extra_args = {}
    if operation == "add_bundles":
        if args.deprecation_list:
            extra_args["deprecation_list"] = args.deprecation_list.split(",")
        if args.check_related_images:
            extra_args["check_related_images"] = args.check_related_images

    if args.binary_image:
        extra_args["binary_image"] = args.binary_image

    if args.overwrite_from_index:
        extra_args["overwrite_from_index"] = args.overwrite_from_index

    if args.overwrite_from_index_token:
        extra_args["overwrite_from_index_token"] = args.overwrite_from_index_token

    if args.build_tag:
        extra_args["build_tags"] = args.build_tag

    build_details = bundle_op(
        args.index_image,
        args.bundle if operation == "add_bundles" else args.operator,
        args.arch,
        **extra_args,
    )

    push_items = push_items_from_build(build_details, "PENDING")
    LOG.debug("Updating push items")
    pc.update_push_items(push_items)

    build_details = iib_c.wait_for_build(build_details)

    build_details_url = _make_iib_build_details_url(args.iib_server, build_details.id)
    LOG.info("IIB details: %s", build_details_url)

    if build_details.state == "failed":
        LOG.error("IIB operation failed")
        print_error_message(build_details_url)
        push_items = push_items_from_build(build_details, "NOTPUSHED")
        pc.update_push_items(push_items)
        sys.exit(1)

    push_items = push_items_from_build(build_details, items_final_state)
    pc.update_push_items(push_items)
    LOG.info("IIB build finished")
    return build_details


def make_add_bundles_parser() -> ArgumentParser:
    return setup_arg_parser(ADD_CMD_ARGS)


def make_rm_operators_parser() -> ArgumentParser:
    return setup_arg_parser(RM_CMD_ARGS)


def add_bundles_main(sysargs: list[str] | None = None) -> list[dict[Any, Any]]:
    logging.basicConfig(level=logging.INFO)

    parser = make_add_bundles_parser()
    if sysargs:
        args = parser.parse_args(sysargs[1:])
    else:
        args = parser.parse_args()
    process_parsed_args(args, ADD_CMD_ARGS)

    return _iib_op_main(args, "add_bundles")


def remove_operators_main(
    sysargs: list[str] | None = None,
) -> list[dict[Any, Any]]:
    logging.basicConfig(level=logging.INFO)

    parser = make_rm_operators_parser()
    if sysargs:
        args = parser.parse_args(sysargs[1:])
    else:
        args = parser.parse_args()
    process_parsed_args(args, RM_CMD_ARGS)

    return _iib_op_main(args, "remove_operators", "DELETED")


def _make_iib_build_details_url(host: str, task_id: str) -> str:
    return "https://%s/api/v1/builds/%s" % (host, task_id)


def print_error_message(iib_build_url: str) -> None:
    """
    Construct and print an error message for IIB failure.

    Args:
        iib_build_url (str): URL of the IIB build.
    """
    res = requests.get(iib_build_url, timeout=30).json()

    LOG.error("IIB Failed with the error: '%s'", res["state_reason"])
    LOG.error("Please check the full logs at %s", f"{iib_build_url.rstrip('/')}/logs")
