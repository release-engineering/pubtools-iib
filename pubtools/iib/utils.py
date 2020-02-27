import argparse
import contextlib
import os
import sys
import pkg_resources

from iiblib import iibclient
from pubtools import pulplib

from iiblib.iibclient import IIBBuildDetailsModel


def setup_iib_client(parsed_args):
    iib_auth = iibclient.IIBKrbAuth(
        parsed_args.iib_krb_principal, ktfile=parsed_args.iib_krb_ktfile
    )
    iibc = iibclient.IIBClient(parsed_args.iib_server, iib_auth)
    return iibc


def setup_pulp_client(parsed_args):
    pulp_kwargs = {"auth": (parsed_args.pulp_user, parsed_args.pulp_password)}
    if parsed_args.pulp_insecure:
        pulp_kwargs["verify"] = False
    pulp_c = pulplib.Client(parsed_args.pulp_url, **pulp_kwargs)
    return pulp_c


def setup_arg_parser(args):
    parser = argparse.ArgumentParser()
    arg_groups = {}
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
def setup_entry_point_cli(entry_tuple, name, args, environ_vars):
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
