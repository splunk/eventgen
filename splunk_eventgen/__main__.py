'''
Copyright (C) 2005-2015 Splunk Inc. All Rights Reserved.
'''

from __future__ import division

import argparse
import errno
import os
import shutil
import sys
import time

import requests

FILE_LOCATION = os.path.dirname(os.path.abspath(__file__))
path_prepend = os.path.join(FILE_LOCATION, 'lib')
sys.path.append(path_prepend)
import __init__ as splunk_eventgen_init
import logging
import eventgen_core

EVENTGEN_VERSION = splunk_eventgen_init.__version__
logger = logging.getLogger()

def parse_args():
    """Parse command line arguments"""
    subparser_dict = {}
    parser = argparse.ArgumentParser(prog='Eventgen',
                                     description='Splunk Event Generation Tool')
    parser.add_argument("-v", "--verbosity", action="count", help="increase output verbosity")
    parser.add_argument("--version", action='version', default=False, version='%(prog)s ' + EVENTGEN_VERSION)
    parser.add_argument("--modinput-mode", default=False)
    subparsers = parser.add_subparsers(title='commands', help="valid subcommands", dest='subcommand')
    # Generate subparser
    generate_subparser = subparsers.add_parser('generate', help="Generate events using a supplied config file")
    generate_subparser.add_argument("configfile", help="Location of eventgen.conf, app folder, or name of an app in $SPLUNK_HOME/etc/apps to run")
    generate_subparser.add_argument("-s", "--sample", help="Run specified sample only, disabling all other samples")
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
    generate_subparser.add_argument("--log-path", type=str, default="{0}/logs".format(FILE_LOCATION))
    # Build subparser
    build_subparser = subparsers.add_parser('build', help="Will build different forms of sa-eventgen")
    build_subparser.add_argument("--mode", type=str, default="splunk-app", help="Specify what type of package to build, defaults to splunk-app mode.")
    build_subparser.add_argument("--destination", help="Specify where to store the output of the build command.")
    build_subparser.add_argument("--remove", default=True, help="Remove the build directory after completion.  Defaults to True")
    # WSGI subparser
    wsgi_subparser = subparsers.add_parser('wsgi', help="start a wsgi server to interact with eventgen.")
    wsgi_subparser.add_argument("--daemon", action="store_true", help="Daemon will tell the wsgi server to start in a daemon mode and will release the cli.")
    # Service subparser
    service_subparser = subparsers.add_parser('service', help="Run Eventgen as a Nameko service. Parameters for starting this service can be defined as either environment variables or CLI arguments, where environment variables takes precedence. See help for more info.")
    service_subparser.add_argument("--role", "-r", type=str, default=None, required=True, choices=["controller", "server"], help="Define the role for this Eventgen node. Options: master, slave")
    service_subparser.add_argument("--amqp-uri", type=str, default=None, help="Full URI to AMQP endpoint in the format pyamqp://<user>:<password>@<host>:<port>. This can also be set using the environment variable EVENTGEN_AMQP_URI")
    service_subparser.add_argument("--amqp-host", type=str, default=None, help="Specify AMQP hostname. This can also be set using the environment variable EVENTGEN_AMQP_HOST. Default is localhost")
    service_subparser.add_argument("--amqp-port", type=int, default=None, help="Specify AMQP port. This can also be set using the environment variable EVENTGEN_AMQP_PORT. Default is 5672")
    service_subparser.add_argument("--amqp-webport", type=int, default=None, help="Specify AMQP web port. This can also be set using the environment variable EVENTGEN_AMQP_WEBPORT. Default is 15672")
    service_subparser.add_argument("--amqp-user", type=str, default=None, help="Specify AMQP user. This can also be set using the environment variable EVENTGEN_AMQP_USER. Default is 'guest'")
    service_subparser.add_argument("--amqp-pass", type=str, default=None, help="Specify AMQP password. This can also be set using the environment variable EVENTGEN_AMQP_PASS. Default is 'guest'")
    service_subparser.add_argument("--web-server-address", type=str, default=None, help="Specify nameko webserver address. This can also be set using the environment variable EVENTGEN_WEB_SERVER_ADDR. Default is 0.0.0.0:9500")
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
    
    if args.subcommand == "service":
        if not args.role:
            msg = "Role is undefined. Please specify a role for this Eventgen service using --role/-r."
            logger.exception(msg)
            raise Exception(msg)

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

def wait_for_response(address, webport, timeout=300):
    '''
    This function extracts the hostname off the given address in the form <protocol>://<user>:<password>@<hostname>:<port>
    and builds a URL in the form http://<hostname>:<webport>. Using this URL, it tries to verify the endpoint is reachable.

    Retry will occur for ~300s
    '''
    protocol, url = address.split("://")
    creds, addr = url.split("@")
    host, port = addr.split(":")
    userid, password = creds.split(":")
    start = time.time()
    end = start
    while end-start < timeout:
        try:
            r = requests.get("http://{}:{}".format(host, webport))
            r.raise_for_status()
            return
        except requests.exceptions.ConnectionError as e:
            time.sleep(1)
        finally:
            end = time.time()
    msg = "Unable to contact broker URL."
    logger.exception(msg)
    raise Exception(msg)

def parse_cli_vars(config, args):
    config["AMQP_URI"] = args.amqp_uri if args.amqp_uri else config["AMQP_URI"]
    config["AMQP_HOST"] = args.amqp_host if args.amqp_host else config["AMQP_HOST"]
    config["AMQP_PORT"] = args.amqp_port if args.amqp_port else config["AMQP_PORT"]
    config["AMQP_WEBPORT"] = args.amqp_webport if args.amqp_webport else config["AMQP_WEBPORT"]
    config["AMQP_USER"] = args.amqp_user if args.amqp_user else config["AMQP_USER"]
    config["AMQP_PASS"] = args.amqp_pass if args.amqp_pass else config["AMQP_PASS"]
    config["WEB_SERVER_ADDRESS"] = args.web_server_address if args.web_server_address else config["WEB_SERVER_ADDRESS"]
    return config

def parse_env_vars():
    osvars, config = dict(os.environ), {}
    config["AMQP_URI"] = osvars.get("EVENTGEN_AMQP_URI", None)
    config["AMQP_HOST"] = osvars.get("EVENTGEN_AMQP_HOST", "localhost")
    config["AMQP_PORT"] = osvars.get("EVENTGEN_AMQP_PORT", 5672)
    config["AMQP_WEBPORT"] = osvars.get("EVENTGEN_AMQP_WEBPORT", 15672)
    config["AMQP_USER"] = osvars.get("EVENTGEN_AMQP_URI", "guest")
    config["AMQP_PASS"] = osvars.get("EVENTGEN_AMQP_PASS", "guest")
    config["WEB_SERVER_ADDRESS"] = osvars.get("EVENTGEN_WEB_SERVER_ADDR", "0.0.0.0:9500")
    return config

def rectify_config(config):
    # For nameko purposes, all we need to pass into the config is AMQP_URI and WEB_SERVER_ADDRESS.
    new = {}
    new["WEB_SERVER_ADDRESS"] = config.get("WEB_SERVER_ADDRESS", "0.0.0.0:9500")
    new["AMQP_WEBPORT"] = config.get("AMQP_WEBPORT", 15672)
    if "AMQP_URI" in config and config["AMQP_URI"]:
        new["AMQP_URI"] = config["AMQP_URI"]
    else:
        if all([config["AMQP_HOST"], config["AMQP_PORT"], config["AMQP_USER"], config["AMQP_PASS"]]):
            new["AMQP_URI"] = "pyamqp://{user}:{pw}@{host}:{port}".format(user=config["AMQP_USER"],
                                                                          pw=config["AMQP_PASS"],
                                                                          host=config["AMQP_HOST"],
                                                                          port=config["AMQP_PORT"])
        else:
            msg = "AMQP_URI is not defined and cannot be constructed. Check environment variables/CLI arguments."
            logger.exception(msg)
            raise Exception(msg)
    return new

def run_nameko(args):
    # Running nameko imports here so that Eventgen as a module does not require nameko to run.
    import eventlet
    eventlet.monkey_patch()
    from nameko.runners import ServiceRunner
    # In order to make this run locally as well as within a container-ized environment, we're to pull variables 
    # from both environment variables and CLI arguments, where CLI will take precendence.
    config = parse_env_vars()
    config = parse_cli_vars(config, args)
    config = rectify_config(config)
    print "Config used: {}".format(config)
    # Wait up to 30s for RMQ service to be up
    wait_for_response(config["AMQP_URI"], config["AMQP_WEBPORT"])
    # Start Nameko service
    runner = ServiceRunner(config=config)
    if args.role == "controller":
        from eventgen_nameko_controller import EventgenController
        runner.add_service(EventgenController)
    else:
        from eventgen_nameko_server import EventgenServer
        runner.add_service(EventgenServer)
    runner.start()
    runnlet = eventlet.spawn(runner.wait)
    while True:
        try:
            runnlet.wait()
        except OSError as exc:
            if exc.errno == errno.EINTR:
                # this is the OSError(4) caused by the signalhandler.
                # ignore and go back to waiting on the runner
                continue
            raise
        except KeyboardInterrupt:
            print()  # looks nicer with the ^C e.g. bash prints in the terminal
            try:
                runner.stop()
            except KeyboardInterrupt:
                print()  # as above
                runner.kill()
        else:
            # runner.wait completed
            break

def exclude_function(filename):
    # removing any hidden . files.
    last_index = filename.rfind('/')
    if last_index != -1:
        if filename[last_index + 1:].startswith('.'):
            return True
    if filename.endswith('.pyo') or filename.endswith('.pyc'):
        return True
    else:
        return False

def make_tarfile(output_filename, source_dir):
    import tarfile
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir), exclude=exclude_function)

def build_splunk_app(dest, remove=True):
    import errno, imp
    directory = os.path.join(dest, 'SA-Eventgen')
    target_file = os.path.join(dest, 'sa_eventgen_{}.spl'.format(EVENTGEN_VERSION))
    module_file, module_path, module_description = imp.find_module('splunk_eventgen')
    splunk_app = os.path.join(module_path, 'splunk_app')
    splunk_app_samples = os.path.join(splunk_app, "samples")
    shutil.copytree(os.path.join(module_path, "samples"), splunk_app_samples)
    try:
        shutil.copytree(splunk_app, directory)
    except OSError as e:
        if e.errno == errno.EEXIST:
            print("Directory already exists. Please remove before continuing")
            sys.exit(3)
        else:
            raise
    directory_lib_dir = os.path.join(directory, 'lib', 'splunk_eventgen')
    shutil.copytree(module_path, directory_lib_dir)
    directory_default_dir = os.path.join(directory, 'default', 'eventgen.conf')
    eventgen_conf = os.path.join(module_path, 'default', 'eventgen.conf')
    shutil.copyfile(eventgen_conf, directory_default_dir)
    make_tarfile(target_file, directory)
    shutil.rmtree(splunk_app_samples)
    if remove:
        shutil.rmtree(directory)

def main():
    cwd = os.getcwd()
    args = parse_args()
    if args.subcommand == "generate":
        eventgen = eventgen_core.EventGenerator(args=args)
        eventgen.start()
    elif args.subcommand == "service":
        run_nameko(args)
    elif args.subcommand == "build":
        if not args.destination:
            args.destination = cwd
        build_splunk_app(dest=args.destination, remove=args.remove)
    sys.exit(0)


if __name__ == '__main__':
    main()
