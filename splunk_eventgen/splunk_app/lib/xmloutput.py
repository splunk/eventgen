import xml.sax.saxutils
import logging
import logging.handlers
import sys
import time
import datetime
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


def setupLogger(logger=None, log_format='%(asctime)s %(levelname)s [ModInput] %(message)s', level=logging.DEBUG,
                log_name="modinput.log", logger_name="modinput"):
    """
    Setup a logger suitable for splunkd consumption
    """
    if logger is None:
        logger = logging.getLogger(logger_name)

    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', log_name]),
                                                        maxBytes=2500000, backupCount=5)
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)

    logger.handlers = []
    logger.addHandler(file_handler)

    logger.debug("Initialized ModularInput Logger")
    return logger


########################################################################
# COMMUNICATION WITH SPLUNKD
# We provide a class for printing data out to splunkd. Essentially this
# is just a wrapper on using xml formatted data delivery to splunkd
########################################################################
class XMLOutputManager(object):
    """
    This guy handles writing data to splunkd with modular input xml 
    streaming mode. 
    """

    def __init__(self, out=sys.stdout):
        """
        Construct an output manager. 
        kwargs: 
            out - represents the stream to print to. Defaults to sys.stdout. 
        """
        self.stream_initiated = False
        self.out = out

    def initStream(self):
        """
        Initiate a stream of data for splunk to consume.
        This MUST be called before any call to sendData.
        """
        self.out.write("<stream>")
        self.stream_initiated = True

    def finishStream(self):
        """
        Close the stream of data for splunk to consume
        """
        if self.stream_initiated:
            self.out.write("</stream>")
            self.stream_initiated = False

    def sendData(self, buf, unbroken=None, sourcetype=None, source=None, host=None, time=None, index=None):
        """
        Send some data to splunk
        args:
            buf - the buffer of data to send (string). REQUIRED.
        kwargs:
            unbroken - this is a boolean indicating the buf passed is unbroken data if this is True. 
                       Defaults to False (buf is a single event).
            sourcetype - the sourcetype to assign to the event (string). Defaults to input default.
            source - the source to assign to the event (string). Defaults to input default.
            host - the host to assign to the event (string). Defaults to input default.
            time - the time to assign to the event (string of UTC UNIX timestamp, 
                   miliseconds supported). Defaults to letting splunkd work it out.
            index - the index into which the data should be stored. Defaults to the input default.
        """
        if not unbroken:
            self.out.write("<event>")
        else:
            self.out.write("<event unbroken=\"1\">")
        self.out.write("<data>")
        self.out.write(xml.sax.saxutils.escape(buf))
        self.out.write("</data>")
        if sourcetype is not None:
            self.out.write("<sourcetype>" + xml.sax.saxutils.escape(sourcetype) + "</sourcetype>")
        if source is not None:
            self.out.write("<source>" + xml.sax.saxutils.escape(source) + "</source>")
        if time is not None:
            if type(time) is datetime.datetime:
                time = time.strftime("%s")
            self.out.write("<time>" + xml.sax.saxutils.escape(time) + "</time>")
        if host is not None:
            self.out.write("<host>" + xml.sax.saxutils.escape(host) + "</host>")
        if index is not None:
            self.out.write("<index>" + xml.sax.saxutils.escape(index) + "</index>")
        self.out.write("</event>\n")
        self.out.flush()

    def sendDoneKey(self, sourcetype=None, source=None, host=None, time=None, index=None):
        """
        Let splunkd know that previously sent, unbroken events are now complete
        and ready for processing. Typically you will send some data, like chunks of a log file
        then when you know you are done, say at the end of the log file you will send a 
        done key to indicate that sent data may be processed for the provided source,
        sourcetype, host, and index
        kwargs:
            sourcetype - the sourcetype of the event (string). Defaults to input default.
            source - the source of the event (string). Defaults to input default.
            host - the host of the event (string). Defaults to input default.
            index - the index into which the data is being stored. Defaults to the input default.
        """
        self.out.write("<event unbroken=\"1\">")
        self.out.write("<data></data>")
        if sourcetype is not None:
            self.out.write("<sourcetype>" + xml.sax.saxutils.escape(sourcetype) + "</sourcetype>")
        if source is not None:
            self.out.write("<source>" + xml.sax.saxutils.escape(source) + "</source>")
        if time is not None:
            if type(time) is datetime.datetime:
                time = time.strftime("%s")
            self.out.write("<time>" + xml.sax.saxutils.escape(time) + "</time>")
        if host is not None:
            self.out.write("<host>" + xml.sax.saxutils.escape(host) + "</host>")
        if index is not None:
            self.out.write("<index>" + xml.sax.saxutils.escape(index) + "</index>")
        self.out.write("<done/></event>\n")
        self.out.flush()

    # prints XML error data to be consumed by Splunk
    def printError(self, s):
        self.out.write("<error><message>{0}</message></error>".format(xml.sax.saxutils.escape(s)))