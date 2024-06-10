import argparse
import contextlib
import os
import sys
import pkg_resources
from typing import Any

from iiblib import iib_client, iib_authentication


def setup_iib_client(parsed_args: argparse.Namespace) -> iib_client.IIBClient:
    iib_auth = iib_authentication.IIBKrbAuth(
        parsed_args.iib_krb_principal,
        parsed_args.iib_server,
        ktfile=parsed_args.iib_krb_ktfile,
    )
    kwargs = {
        "auth": iib_auth,
    }
    if parsed_args.iib_insecure:
        kwargs["ssl_verify"] = False
    if parsed_args.build_timeout:
        kwargs["wait_for_build_timeout"] = int(parsed_args.build_timeout)
    iibc = iib_client.IIBClient(parsed_args.iib_server, **kwargs)
    return iibc


def setup_arg_parser(args: dict[Any, Any]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    arg_groups: dict[Any, Any] = {}
    for aliases, arg_data in args.items():
        holder = parser
        if arg_data["group"]:
            arg_groups.setdefault(
                arg_data["group"], parser.add_argument_group(arg_data["group"])
            )
            holder = arg_groups[arg_data["group"]]
        action = arg_data.get("action")
        if not action and arg_data["type"] == bool:
            action = "store_true"
        kwargs = {
            "help": arg_data.get("help"),
            "required": arg_data.get("required", False),
            "default": arg_data.get("default"),
        }
        if action:
            kwargs["action"] = action
        else:
            kwargs["type"] = arg_data.get("type", "str")
            kwargs["nargs"] = arg_data.get("count")

        holder.add_argument(*aliases, **kwargs)

    return parser


@contextlib.contextmanager
def setup_entry_point_cli(
    entry_tuple: tuple[str, str, str],
    name: str,
    args: list[str],
    environ_vars: dict[str, str],
) -> Any:
    orig_argv = sys.argv[:]
    orig_environ = os.environ.copy()

    try:
        # First argv element is always the entry point name.
        # For a console_scripts entry point, this will be the same value
        # as if the script was invoked directly. For any other kind of entry point,
        # this value is probably meaningless.
        sys.argv = [name]
        sys.argv.extend(args)
        for key in environ_vars:
            os.environ[key] = environ_vars[key]
        entry_point_func = pkg_resources.load_entry_point(*entry_tuple)
        yield entry_point_func
    finally:
        sys.argv = orig_argv[:]
        os.environ.update(orig_environ)

        to_delete = [key for key in os.environ if key not in orig_environ]
        for key in to_delete:
            del os.environ[key]
