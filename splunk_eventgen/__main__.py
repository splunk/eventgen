import argparse
import errno
import logging
import os
import shutil
import sys

from splunk_eventgen.eventgen_core import EventGenerator
from splunk_eventgen.lib.logging_config import logger

FILE_LOCATION = os.path.dirname(os.path.abspath(__file__))


def _get_version():
    """
    @return: Version Number
    """
    try:
        from sys import version_info

        if version_info[0] < 3 or (version_info[0] and version_info[1] < 8):
            from importlib_metadata import PackageNotFoundError, distribution

            try:
                dist = distribution("splunk_eventgen")
                return dist.version
            except PackageNotFoundError:
                return "dev"
        else:
            # module change in python 3.8
            from importlib.metadata import PackageNotFoundError, distribution

            try:
                dist = distribution("splunk_eventgen")
                return dist.version
            except PackageNotFoundError:
                return "dev"
            except ImportError:
                return "Unknown"
            except ModuleNotFoundError:
                return "Unknown"
    except Exception:
        return "Unknown"


EVENTGEN_VERSION = _get_version()


def parse_args():
    """Parse command line arguments"""
    subparser_dict = {}
    parser = argparse.ArgumentParser(
        prog="Eventgen", description="Splunk Event Generation Tool"
    )
    parser.add_argument(
        "-v", "--verbosity", action="count", help="increase output verbosity"
    )
    parser.add_argument(
        "--version",
        action="version",
        default=False,
        version="%(prog)s " + EVENTGEN_VERSION,
    )
    parser.add_argument("--modinput-mode", default=False)
    parser.add_argument("--counter-output", action="store_true", default=False)
    subparsers = parser.add_subparsers(
        title="commands", help="valid subcommands", dest="subcommand"
    )
    # Generate subparser
    generate_subparser = subparsers.add_parser(
        "generate", help="Generate events using a supplied config file"
    )
    generate_subparser.add_argument(
        "configfile",
        help="Location of eventgen.conf, app folder, or name of an app in $SPLUNK_HOME/etc/apps to run",
    )
    generate_subparser.add_argument(
        "-s", "--sample", help="Run specified sample only, disabling all other samples"
    )
    generate_subparser.add_argument(
        "--keepoutput",
        action="store_true",
        help="Keep original outputMode for the sample",
    )
    generate_subparser.add_argument(
        "--devnull", action="store_true", help="Set outputMode to devnull"
    )
    generate_subparser.add_argument(
        "--modinput",
        action="store_true",
        help="Set outputMode to modinput, to see metadata",
    )
    generate_subparser.add_argument("-c", "--count", type=int, help="Set sample count")
    generate_subparser.add_argument(
        "-i", "--interval", type=int, help="Set sample interval"
    )
    generate_subparser.add_argument(
        "-b", "--backfill", help="Set time to backfill from"
    )
    generate_subparser.add_argument(
        "-e",
        "--end",
        help="Set time to end generation at or a number of intervals to run",
    )
    generate_subparser.add_argument(
        "--generators", type=int, help="Number of GeneratorWorkers (mappers)"
    )
    generate_subparser.add_argument(
        "--outputters", type=int, help="Number of OutputWorkers (reducers)"
    )
    generate_subparser.add_argument(
        "--disableOutputQueue", action="store_true", help="Disable reducer step"
    )
    generate_subparser.add_argument(
        "--multiprocess",
        action="store_true",
        help="Use multiprocesing instead of threading",
    )
    generate_subparser.add_argument(
        "--profiler", action="store_true", help="Turn on cProfiler"
    )
    generate_subparser.add_argument(
        "--generator-queue-size",
        type=int,
        default=500,
        help="the max queue size for the "
        "generator queue, timer object puts all the generator tasks into this queue, default max size is 500",
    )
    generate_subparser.add_argument(
        "--disable-logging", action="store_true", help="disable logging"
    )
    # Build subparser
    build_subparser = subparsers.add_parser(
        "build", help="Will build different forms of sa-eventgen"
    )
    build_subparser.add_argument(
        "--mode",
        type=str,
        default="splunk-app",
        help="Specify what type of package to build, defaults to splunk-app mode.",
    )
    build_subparser.add_argument(
        "--destination", help="Specify where to store the output of the build command."
    )
    build_subparser.add_argument(
        "--remove",
        default=True,
        help="Remove the build directory after completion. Defaults to True",
    )
    # Service subparser
    service_subparser = subparsers.add_parser(
        "service",
        help=(
            "Run Eventgen as an api server. Parameters for starting this service can be defined as either env"
            "variables or CLI arguments, where env variables takes precedence. See help for more info."
        ),
    )
    service_subparser.add_argument(
        "--role",
        "-r",
        type=str,
        default=None,
        required=True,
        choices=["controller", "server", "standalone"],
        help="Define the role for this Eventgen node. Options: controller, server, standalone",
    )
    service_subparser.add_argument(
        "--redis-host", type=str, default="127.0.0.1", help="Redis Host"
    )
    service_subparser.add_argument(
        "--redis-port", type=str, default="6379", help="Redis Port"
    )
    service_subparser.add_argument(
        "--web-server-port",
        type=str,
        default="9500",
        help="Port you want to run a web server on",
    )
    service_subparser.add_argument(
        "--multithread",
        action="store_true",
        help="Use multi-thread instead of multi-process",
    )
    # Help subparser
    # NOTE: Keep this at the end so we can use the subparser_dict.keys() to display valid commands
    help_subparser = subparsers.add_parser("help", help="Display usage on a subcommand")
    helpstr = "Help on a specific command, valid commands are: " + ", ".join(
        list(subparser_dict.keys()) + ["help"]
    )
    help_subparser.add_argument("command", nargs="?", default="default", help=helpstr)
    # add subparsers to the subparser dict, this will be used later for usage / help statements.
    subparser_dict["generate"] = generate_subparser
    subparser_dict["build"] = build_subparser
    subparser_dict["help"] = help_subparser

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)

    args = parser.parse_args()

    if args.version:
        args.print_version()
        sys.exit(0)

    if "subcommand" not in args:
        parser.print_help()
        sys.exit(2)

    if args.subcommand == "service":
        if not args.role:
            msg = "Role is undefined. Please specify a role for this Eventgen service using --role/-r."
            logger.exception(msg)
            raise Exception(msg)

    if args.subcommand == "help" and args.command == "default":
        parser.print_help()
        sys.exit(0)

    if args.subcommand == "help":
        if args.command in list(subparser_dict.keys()):
            subparser_dict[args.command].print_help()
        else:
            parser.print_help()
        sys.exit(0)
    elif args.subcommand == "build" and not args.destination:
        print(
            "No destination passed for storing output file, attempting to use the current working dir."
        )

    # Allow passing of a Splunk app on the command line and expand the full path before passing up the chain
    if hasattr(args, "configfile") and not os.path.exists(args.configfile):
        if "SPLUNK_HOME" in os.environ:
            if os.path.isdir(
                os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", args.configfile)
            ):
                args.configfile = os.path.join(
                    os.environ["SPLUNK_HOME"], "etc", "apps", args.configfile
                )
        else:
            args.configfile = None
    return args


def filter_function(tarinfo):
    # removing any hidden . files.
    last_index = tarinfo.name.rfind("/")
    if last_index != -1:
        if tarinfo.name[last_index + 1 :].startswith("."):
            return None
    if (
        tarinfo.name.endswith(".pyo")
        or tarinfo.name.endswith(".pyc")
        or "/splunk_app" in tarinfo.name
    ):
        return None
    else:
        return tarinfo


def make_tarfile(output_filename, source_dir):
    import tarfile

    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(
            source_dir, arcname=os.path.basename(source_dir), filter=filter_function
        )


def build_splunk_app(dest, source=os.getcwd(), remove=True):
    cwd = os.getcwd()
    os.chdir(source)
    directory = os.path.join(dest, "SA-Eventgen")
    target_file = os.path.join(dest, "sa_eventgen_{}.spl".format(EVENTGEN_VERSION))
    splunk_app = os.path.join(FILE_LOCATION, "splunk_app")
    splunk_app_samples = os.path.join(splunk_app, "samples")
    if os.path.exists(splunk_app_samples):
        shutil.rmtree(splunk_app_samples)
    shutil.copytree(os.path.join(FILE_LOCATION, "samples"), splunk_app_samples)
    try:
        shutil.copytree(splunk_app, directory)
    except OSError as e:
        os.chdir(cwd)
        if e.errno == errno.EEXIST:
            print("Directory already exists. Please remove before continuing")
            sys.exit(3)
        else:
            raise
    directory_lib_dir = os.path.join(directory, "lib", "splunk_eventgen")
    shutil.copytree(FILE_LOCATION, directory_lib_dir)
    directory_default_dir = os.path.join(directory, "default", "eventgen.conf")
    eventgen_conf = os.path.join(FILE_LOCATION, "default", "eventgen.conf")
    shutil.copyfile(eventgen_conf, directory_default_dir)

    # install 3rd lib dependencies
    install_target = os.path.join(directory, "bin")
    install_cmd = (
        "pip install --requirement splunk_eventgen/lib/requirements.txt --upgrade --no-compile "
        + "--no-binary :all: --target "
        + install_target
    )
    return_code = os.system(install_cmd)
    if return_code != 0:
        install_cmd = (
            "pip3 install --requirement splunk_eventgen/lib/requirements.txt --upgrade --no-compile "
            + "--no-binary :all: --target "
            + install_target
        )
        return_code = os.system(install_cmd)
        if return_code != 0:
            print(
                "Failed to install dependencies via pip. Please check whether pip is installed."
            )
    os.system("rm -rf " + os.path.join(install_target, "*.egg-info"))

    make_tarfile(target_file, directory)
    shutil.rmtree(splunk_app_samples)
    if remove:
        shutil.rmtree(directory)
    os.chdir(cwd)


def convert_verbosity_count_to_logging_level(verbosity):
    if type(verbosity) == int:
        if verbosity == 0:
            return logging.ERROR
        elif verbosity == 1:
            return logging.INFO
        elif verbosity >= 2:
            return logging.DEBUG
        else:
            return logging.DEBUG
    else:
        return logging.ERROR


def gather_env_vars(args):
    env_vars = dict()
    env_vars["REDIS_HOST"] = os.environ.get("REDIS_HOST", args.redis_host)
    env_vars["REDIS_PORT"] = os.environ.get("REDIS_PORT", args.redis_port)
    env_vars["WEB_SERVER_PORT"] = os.environ.get(
        "WEB_SERVER_PORT", args.web_server_port
    )
    if "multithread" in args:
        env_vars["multithread"] = args.multithread
    return env_vars


def main():
    cwd = os.getcwd()
    args = parse_args()
    args.verbosity = convert_verbosity_count_to_logging_level(args.verbosity)
    if args.subcommand == "generate":
        eventgen = EventGenerator(args=args)
        eventgen.start()
    elif args.subcommand == "service":
        env_vars = gather_env_vars(args)
        if args.role == "controller":
            from splunk_eventgen.eventgen_api_server.eventgen_controller import (
                EventgenController,
            )

            EventgenController(env_vars=env_vars).app_run()
        elif args.role == "server":
            from splunk_eventgen.eventgen_api_server.eventgen_server import (
                EventgenServer,
            )

            EventgenServer(env_vars=env_vars, mode="cluster").app_run()
        elif args.role == "standalone":
            from splunk_eventgen.eventgen_api_server.eventgen_server import (
                EventgenServer,
            )

            EventgenServer(env_vars=env_vars, mode="standalone").app_run()
    elif args.subcommand == "build":
        if not args.destination:
            args.destination = cwd
        build_splunk_app(dest=args.destination, remove=args.remove)
    sys.exit(0)


if __name__ == "__main__":
    main()
