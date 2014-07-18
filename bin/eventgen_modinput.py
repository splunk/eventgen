'''
Copyright (C) 2005-2012 Splunk Inc. All Rights Reserved.
'''
from __future__ import division

import sys, os
path_prepend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.append(path_prepend)

import logging
import threading
import multiprocessing
import time
import datetime
from select import select
from eventgenconfig import Config
from eventgentimer import Timer
import xml.dom.minidom
import pprint

SCHEME = """<scheme>
    <title>SA-Eventgen</title>
    <description>Generate data for Splunk Apps with eventgen.conf</description>
    <use_external_validation>false</use_external_validation>
    <use_single_instance>true</use_single_instance>
    <streaming_mode>xml</streaming_mode>
    <endpoint/>
</scheme>
"""
def do_scheme():
    print SCHEME

# read XML configuration passed from splunkd
def get_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()
        logger.debug("Config Str: %s" % config_str)

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        server_host = str(root.getElementsByTagName("server_host")[0].firstChild.data)
        if server_host:
            logger.debug("XML: Found server_host")
            config["server_host"] = server_host
        server_uri = str(root.getElementsByTagName("server_uri")[0].firstChild.data)
        if server_uri:
            logger.debug("XML: Found server_uri")
            config["server_uri"] = server_uri
        session_key = str(root.getElementsByTagName("session_key")[0].firstChild.data)
        if session_key:
            logger.debug("XML: Found session_key")
            config["session_key"] = session_key
        checkpoint_dir = str(root.getElementsByTagName("checkpoint_dir")[0].firstChild.data)
        if checkpoint_dir:
            logger.debug("XML: Found checkpoint_dir")
            config["checkpoint_dir"] = checkpoint_dir
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logger.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logger.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logger.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logger.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

        # just some validation: make sure these keys are present (required)
        # validate_conf(config, "name")
        # validate_conf(config, "key_id")
        # validate_conf(config, "secret_key")
        # validate_conf(config, "checkpoint_dir")
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
            sys.exit(0)
            
    c = Config()
    # Logger is setup by Config, just have to get an instance
    logobj = logging.getLogger('eventgen')
    logobj.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logobj.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s %(message)s')
    streamHandler = logging.StreamHandler(sys.stderr)
    streamHandler.setFormatter(formatter)
    logobj.handlers = [ ]
    logobj.addHandler(streamHandler)
    from eventgenconfig import EventgenAdapter
    adapter = EventgenAdapter(logobj, {'sample': 'null', 'module': 'main'})
    logger = adapter

    logobj.info('Starting eventgen')

    # Start the stream, only once for the whole program
    print '<stream>\n'
        

    splunkconf = get_config()
    # logger.debug("Splunkconf: %s" % pprint.pformat(splunkconf))
    if 'session_key' in splunkconf:
        c.makeSplunkEmbedded(sessionKey=splunkconf['session_key'])
    else:
        raise ValueError('sessionKey missing from Splunk stdin config')
        
    c.parse()

    # Hopefully this will catch interrupts, signals, etc
    # To allow us to stop gracefully
    t = Timer(1.0, interruptcatcher=True)

    for s in c.samples:
        if s.interval > 0 or s.mode == 'replay':
            logger.info("Creating timer object for sample '%s' in app '%s'" % (s.name, s.app) )    
            t = Timer(1.0, s) 
            c.sampleTimers.append(t)
    
    if os.name != "nt":
        c.set_exit_handler(c.handle_exit)
    first = True
    outputQueueCounter = 0
    generatorQueueCounter = 0
    while (1):
        try:
            ## Only need to start timers once
            if first:
                c.start()
                first = False

            # Every 5 seconds, get values and output basic statistics about our operations
            generatorDecrements = c.generatorQueueSize.totaldecrements()
            outputDecrements = c.outputQueueSize.totaldecrements()
            generatorsPerSec = (generatorDecrements - generatorQueueCounter) / 5
            outputtersPerSec = (outputDecrements - outputQueueCounter) / 5
            outputQueueCounter = outputDecrements
            generatorQueueCounter = generatorDecrements
            logger.info('OutputQueueDepth=%d  GeneratorQueueDepth=%d GeneratorsPerSec=%d OutputtersPerSec=%d' % (c.outputQueueSize.value(), c.generatorQueueSize.value(), generatorsPerSec, outputtersPerSec))
            # Using Embedded Metrics log when in Splunk
            # kiloBytesPerSec = c.bytesSent.valueAndClear() / 5 / 1024
            # gbPerDay = (kiloBytesPerSec / 1024 / 1024) * 60 * 60 * 24
            # eventsPerSec = c.eventsSent.valueAndClear() / 5
            # logger.info('GlobalEventsPerSec=%s KilobytesPerSec=%1f GigabytesPerDay=%1f' % (eventsPerSec, kiloBytesPerSec, gbPerDay))
            time.sleep(5)
        except KeyboardInterrupt:
            c.handle_exit()