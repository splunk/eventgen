'''
Copyright (C) 2005-2015 Splunk Inc. All Rights Reserved.
'''

from __future__ import division
import sys, os, shutil
path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
sys.path.append(path_prepend)
import __init__ as splunk_eventgen_init
import logging
import eventgen_core

EVENTGEN_VERSION = splunk_eventgen_init.__version__
logger = logging.getLogger()

def parse_args():
    """Parse command line arguments"""

    import argparse
    subparser_dict = {}
    parser = argparse.ArgumentParser(prog='Eventgen',
                                     description='Splunk Event Generation Tool')
    parser.add_argument("-v", "--verbosity", action="count", help="increase output verbosity")
    parser.add_argument("--version", action='version', default=False, version='%(prog)s ' + EVENTGEN_VERSION)
    subparsers = parser.add_subparsers(title='commands', help="valid subcommands", dest='subcommand')
    generate_subparser = subparsers.add_parser('generate', help="Generate events using a supplied config file")
    generate_subparser.add_argument("configfile", help="Location of eventgen.conf, app folder, or name of an app in $SPLUNK_HOME/etc/apps to run")
    generate_subparser.add_argument("-s", "--sample", help="Run specified sample only, overriding outputMode to stdout, disabling all other samples")
    generate_subparser.add_argument("--keepoutput", action="store_true", help="Keep original outputMode for the sample")
    generate_subparser.add_argument("--devnull", action="store_true", help="Set outputMode to devnull")
    generate_subparser.add_argument("--modinput", action="store_true", help="Set outputMode to modinput, to see metadata")
    generate_subparser.add_argument("-c", "--count", type=int, help="Set sample count")
    generate_subparser.add_argument("-i", "--interval", type=int, help="Set sample interval")
    generate_subparser.add_argument("-b", "--backfill", help="Set time to backfill from.  Note: to use it, send the parameter with space in front like ' -60m'")
    generate_subparser.add_argument("-e", "--end", help="Set time to end generation at or a number of intervals to run.  Note: to use it with a time, send the parameter with space in front like ' -10m'")
    generate_subparser.add_argument("--generators", type=int, help="Number of GeneratorWorkers (mappers)")
    generate_subparser.add_argument("--outputters", type=int, help="Number of OutputWorkers (reducers)")
    generate_subparser.add_argument("--disableOutputQueue", action="store_true", help="Disable reducer step")
    generate_subparser.add_argument("--multiprocess", action="store_true", help="Use multiprocesing instead of threading")
    generate_subparser.add_argument("--profiler", action="store_true", help="Turn on cProfiler")
    build_subparser = subparsers.add_parser('build', help="Will build different forms of sa-eventgen")
    build_subparser.add_argument("--mode", type=str, default="splunk-app", help="Specify what type of package to build, defaults to splunk-app mode.")
    build_subparser.add_argument("--destination", help="Specify where to store the output of the build command.")
    build_subparser.add_argument("--remove", default=True, help="Remove the build directory after completion.  Defaults to True")
    wsgi_subparser = subparsers.add_parser('wsgi', help="start a wsgi server to interact with eventgen.")
    wsgi_subparser.add_argument("--daemon", action="store_true", help="Daemon will tell the wsgi server to start in a daemon mode and will release the cli.")
    # Help subparser
    # NOTE: Keep this at the end so we can use the subparser_dict.keys() to display valid commands
    help_subparser = subparsers.add_parser('help', help="Display usage on a subcommand")
    helpstr =  "Help on a specific command, valid commands are: " + ", ".join(subparser_dict.keys() + ["help"])
    help_subparser.add_argument("command", nargs='?', default="default", help=helpstr)
    # add subparsers to the subparser dict, this will be used later for usage / help statements.
    subparser_dict['generate'] = generate_subparser
    subparser_dict['build'] = build_subparser
    subparser_dict['wsgi'] = wsgi_subparser
    subparser_dict['help'] = help_subparser

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)

    args = parser.parse_args()

    if args.version:
        args.print_version()
        sys.exit(0)

    if 'subcommand' not in args:
        parser.print_help()
        sys.exit(2)

    if args.subcommand == "help" and args.command == "default":
        parser.print_help()
        sys.exit(0)

    if args.subcommand == "help":
        if args.command in subparser_dict.keys():
            subparser_dict[args.command].print_help()
        else:
            parser.print_help()
        sys.exit(0)
    elif args.subcommand == "build" and not args.destination:
        print("No destination passed for storing output file, attempting to use the current working dir.")

    # Allow passing of a Splunk app on the command line and expand the full path before passing up the chain
    if hasattr(args, "configfile") and not os.path.exists(args.configfile):
        if 'SPLUNK_HOME' in os.environ:
            if os.path.isdir(os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', args.configfile)):
                args.configfile = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', args.configfile)
        else:
            args.configfile = None
    return args

def make_tarfile(output_filename, source_dir):
    import tarfile
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def build_splunk_app(dest, remove=True):
    import errno, imp
    directory = os.path.join(dest, 'SA-Eventgen')
    target_file = os.path.join(dest, 'sa_eventgen.spl')
    module_file, module_path, module_description = imp.find_module('splunk_eventgen')
    splunk_app = os.path.join(module_path, 'splunk_app')
    lib_dir = os.path.join(module_path, 'lib')
    try:
        shutil.copytree(splunk_app, directory)
    except OSError as e:
        if e.errno == errno.EEXIST:
            print("Directory already exists. Please remove before continuing")
            sys.exit(3)
        else:
            raise
    directory_lib_dir = os.path.join(directory, 'lib')
    shutil.copytree(lib_dir, directory_lib_dir)
    make_tarfile(target_file, directory)
    if remove:
        shutil.rmtree(directory)

if __name__ == '__main__':
    cwd = os.getcwd()
    args = parse_args()
    if args.subcommand == "generate":
        eventgen = eventgen_core.EventGenerator(args=args)
        eventgen.start()
    elif args.subcommand == "build":
        if not args.destination:
            args.destination = cwd
        build_splunk_app(dest=args.destination, remove=args.remove)
    sys.exit(0)
