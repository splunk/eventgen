#!/usr/bin/env python
# encoding: utf-8
from lib.eventgenconfig import Config
from lib.eventgentimer import Timer
import logging
import logging.config
import os
import sys
import imp
from Queue import Queue, Empty
from threading import Thread
import time

lib_path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
sys.path.insert(0, lib_path_prepend)
# Since i'm including a new library but external sources may not have access to pip (like splunk embeded), I need to
# be able to load this library directly from src if it's not installed.
try:
    import logutils
    import logutils.handlers
except ImportError:
    path_prepend = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'logutils_src')
    sys.path.append(path_prepend)
    import logutils
    import logutils.queue

file_path=os.path.dirname(os.path.realpath(__file__))


class EventGenerator(object):
    def __init__(self, args=None):
        '''
        This object will allow you to generate and control eventgen.  It should be handed the parse_args object
        from __main__ and will hand the argument object to the config parser of eventgen5.  This will provide the
        bridge to using the old code with the newer style.  As things get moved from the config parser, this should
        start to control all of the configuration items that are global, and the config object should only handle the
        localized .conf entries.
        :param args: __main__ parse_args() object.
        '''
        self.stopping = False
        self.started = False
        self.config = None
        self.args = args

        self._setup_loggers()
        # attach to the logging queue
        self.logger.debug("Logging Setup Complete.")

        if self.args and 'configfile' in self.args:
            self._load_config(self.args.configfile, args=args)

    def _load_config(self, configfile, **kwargs):
        '''
        This method will use a configfile and set self.confg as a processeded config object,
        kwargs will need to match eventgenconfig.py
        :param configfile:
        :return:
        '''
        #TODO: The old eventgne had strange cli args, and usage of args.  We should probably update the module args
        #to match more of what this is doing...
        new_args={}
        if "args" in kwargs:
            args = kwargs["args"]
            outputer = [key for key in ["keepoutput","devnull","modinput"] if getattr(args, key)]
            if len(outputer) > 0:
                new_args["override_outputter"] = outputer[0]
            if getattr(args, "count"):
                new_args["override_count"] = args.count
            if getattr(args, "interval"):
                new_args["override_interval"] = args.interval
            if getattr(args, "backfill"):
                new_args["override_backfill"] = args.backfill
            if getattr(args, "end"):
                new_args["override_end"] = args.end
            if getattr(args, "multiprocess"):
                new_args["threading"] = "process"
            if getattr(args, "generators"):
                new_args["override_generators"] = args.generators
            if getattr(args, "disableOutputQueue"):
                new_args["override_outputqueue"] = args.disableOutputQueue
            if getattr(args, "profiler"):
                new_args["profiler"] = args.profiler
        self.config = Config(configfile, new_args.iteritems())
        self.config.parse()
        self._reload_plugins()
        #TODO: Probably should destroy pools better so processes are cleaned.
        self._setup_pools()

    def _reload_plugins(self):
        # Initialize plugins
        # Plugins must be loaded before objects that do work, otherwise threads and processes generated will not have
        # the modules loaded in active memory.
        self.config.outputPlugins = { }
        plugins = self._initializePlugins(os.path.join(file_path, 'lib', 'plugins', 'output'), self.config.outputPlugins, 'output')
        self.config.validOutputModes.extend(plugins)
        self._initializePlugins(os.path.join(file_path, 'lib', 'plugins', 'generator'), self.config.plugins, 'generator')
        plugins = self._initializePlugins(os.path.join(file_path, 'lib', 'plugins', 'rater'), self.config.plugins, 'rater')
        self.config._complexSettings['rater'] = plugins

    def _setup_pools(self):
        '''
        This method is an internal method called on init to generate pools needed for processing.

        :return:
        '''
        # Load the things that actually do the work.
        self._create_generator_pool()
        self._create_timer_threadpool()
        self._create_output_threadpool()
        self._create_generator_workers()

    def _create_timer_threadpool(self, threadcount=100):
        '''
        Timer threadpool is used to contain the timer object for each sample.  A timer will stay active
        until the end condition is met for the sample.  If there is no end condition, the timer will exist forever.
        :param threadcount: is how many active timers we want to allow inside of eventgen.  Default 100.  If someone
                            has over 100 samples, additional samples won't run until the first ones end.
        :return:
        '''
        self.sampleQueue = Queue(maxsize=0)
        num_threads = threadcount
        for i in range(num_threads):
            worker = Thread(target=self._worker_do_work,
                            args=(self.sampleQueue, self.loggingQueue, ),
                            name="TimeThread{0}".format(i))
            worker.setDaemon(True)
            worker.start()

    def _create_output_threadpool(self, threadcount=1):
        '''
        the output thread pool is used for output plugins that need to control file locking, or only have 1 set thread
        to send all the data out of.  this FIFO queue just helps make sure there are file collisions or write collisions.
        There's only 1 active thread for this queue, if you're ever considering upping this, don't.  Just shut off the
        outputQueue and let each generator directly output it's data.
        :param threadcount: is how many active output threads we want to allow inside of eventgen.  Default 1
        :return:
        '''
        #TODO: Make this take the config param and figure out what we want to do with this.
        if getattr(self, "manager", None):
            self.outputQueue = self.manager.Queue(maxsize=10000)
        else:
            self.outputQueue = Queue(maxsize=10000)
        num_threads = threadcount
        for i in range(num_threads):
            worker = Thread(target=self._worker_do_work,
                            args=(self.outputQueue, self.loggingQueue, ),
                            name="OutputThread{0}".format(i))
            worker.setDaemon(True)
            worker.start()

    def _create_generator_pool(self, workercount=10):
        '''
        The generator pool has two main options, it can run in multiprocessing or in threading.  We check the argument
        from configuration, and then build the appropriate queue type.  Each time a timer runs for a sample, if the
        timer says it's time to generate, it will create a new generator plugin object, and place it in this queue.
        :param workercount: is how many active workers we want to allow inside of eventgen.  Default 10.  If someone
                            has over 10 generators working, additional samples won't run until the first ones end.
        :return:
        '''
        if self.args.multiprocess:
            import multiprocessing
            self.manager = multiprocessing.Manager()
            self.loggingQueue = self.manager.Queue()
            self.logging_pool = Thread(target=self.logger_thread, args=(self.loggingQueue,), name="LoggerThread")
            self.logging_pool.start()
            # since we're now in multiprocess, we need to use better queues.
            self.workerQueue = multiprocessing.JoinableQueue(maxsize=500)
            self.genconfig = self.manager.dict()
            self.genconfig["stopping"] = False
        else:
            self.workerQueue = Queue(maxsize=500)
            worker_threads = workercount
            for i in range(worker_threads):
                worker = Thread(target=self._worker_do_work, args=(self.workerQueue, self.loggingQueue, ))
                worker.setDaemon(True)
                worker.start()

    def _create_generator_workers(self, workercount=10):
        if self.args.multiprocess:
            import multiprocessing
            self.workerPool = []
            for worker in xrange(workercount):
                #builds a list of tuples to use the map function
                process = multiprocessing.Process(target=self._proc_worker_do_work,
                                                  args=(self.workerQueue, self.loggingQueue, self.genconfig, ))
                self.workerPool.append(process)
                process.start()
        else:
            pass

    def _setup_loggers(self, config=None):
        if not config:
            self.logger_config = {
                'version': 1,
                'formatters': {
                    'detailed': {
                        'class': 'logging.Formatter',
                        'format': '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
                    }
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'level': 'INFO',
                    },
                    'file': {
                        'class': 'logging.FileHandler',
                        'filename': 'eventgen_main.log',
                        'mode': 'w',
                        'formatter': 'detailed',
                    },
                    'eventgenfile': {
                        'class': 'logging.FileHandler',
                        'filename': 'eventgen-process.log',
                        'mode': 'w',
                        'formatter': 'detailed',
                    },
                    'errors': {
                        'class': 'logging.FileHandler',
                        'filename': 'eventgen-errors.log',
                        'mode': 'w',
                        'level': 'ERROR',
                        'formatter': 'detailed',
                    }
                },
                'loggers': {
                    'eventgen': {
                        'handlers': ['eventgenfile']
                    }
                },
                'root': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file', 'errors']
                },
            }
        else:
            self.logger_config = config

        if self.args and 'wsgi' in self.args and self.args.wsgi:
            self.setup_cherrpy_logger()

        logging.config.dictConfig(self.logger_config)
        # We need to have debugv from the olderversions of eventgen.
        DEBUG_LEVELV_NUM = 9
        logging.addLevelName(DEBUG_LEVELV_NUM, "DEBUGV")
        def debugv(self, message, *args, **kws):
            # Yes, logger takes its '*args' as 'args'.
            if self.isEnabledFor(DEBUG_LEVELV_NUM):
                self._log(DEBUG_LEVELV_NUM, message, args, **kws)
        logging.Logger.debugv = debugv
        self.logger = logging.getLogger('eventgen')
        self.loggingQueue = None

    def setup_cherrpy_logger(self):
        self.logger_config['handlers']['cherrypy_console'] = {'level': 'INFO',
                                                              'class': 'logging.StreamHandler',
                                                              'formatter': 'detailed',
                                                              'stream': 'ext://sys.stdout'}
        self.logger_config['handlers']['cherrypy_access'] = {'level': 'INFO',
                                                             'class': 'logging.handlers.RotatingFileHandler',
                                                             'formatter': 'detailed',
                                                             'filename': 'wsgi_access.log',
                                                             'maxBytes': 10485760,
                                                             'backupCount': 20,
                                                             'encoding': 'utf8'}
        self.logger_config['handlers']['cherrypy_error'] = {'level': 'INFO',
                                                            'class': 'logging.handlers.RotatingFileHandler',
                                                            'formatter': 'detailed',
                                                            'filename': 'wsgi_errors.log',
                                                            'maxBytes': 10485760,
                                                            'backupCount': 20,
                                                            'encoding': 'utf8'}
        self.logger_config['loggers']['cherrypy.access'] = {'handlers': ['cherrypy_access'],
                                                            'level': 'INFO',
                                                            'propagate': False}
        self.logger_config['loggers']['cherrypy.error'] = {'handlers': ['cherrypy_console', 'cherrypy_error'],
                                                           'level': 'INFO',
                                                           'propagate': False}
        self.logger_config['root']['handlers'].extend(['cherrypy_console', 'cherrypy_error', 'cherrypy_access'])


    def _worker_do_work(self, work_queue, logging_queue):
        while not self.stopping:
            try:
                item = work_queue.get(timeout=10)
                item.run()
                work_queue.task_done()
            except Empty:
                pass
            except Exception as e:
                self.logger.exception(e)
                raise e

    @staticmethod
    def _proc_worker_do_work(work_queue, logging_queue, config):
        genconfig = config
        stopping = genconfig['stopping']
        qh = logutils.queue.QueueHandler(logging_queue)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(qh)
        while not stopping:
            try:
                root.info("Checking for work")
                item = work_queue.get(timeout=10)
                item.logger = root
                item.config._setup_logging()
                item._out.updateConfig(item.config)
                item._out._setup_logging()
                item.run()
                work_queue.task_done()
                stopping = genconfig['stopping']
                item.logger.debug("Current Worker Stopping: {0}".format(stopping))
            except Empty:
                stopping = genconfig['stopping']
            except Exception as e:
                root.exception(e)
                raise e
        else:
            root.info("Stopping Process")
            sys.exit(0)

    def logger_thread(self, loggingQueue):
        while not self.stopping:
            try:
                record = loggingQueue.get(timeout=10)
                logger = logging.getLogger(record.name)
                logger.handle(record)
                loggingQueue.task_done()
            except Empty:
                pass
            except Exception as e:
                self.logger.exception(e)
                raise e

    def _initializePlugins(self, dirname, plugins, plugintype, name=None):
        """Load a python module dynamically and add to internal dictionary of plugins (only accessed by getPlugin)"""
        ret = []
        syspathset = set(sys.path)

        dirname = os.path.abspath(dirname)
        self.logger.debugv("looking for plugin(s) in {}".format(dirname))
        if not os.path.isdir(dirname):
            self.logger.debugv("directory {} does not exist ... moving on".format(dirname))
            return ret

        # Include all plugin directories in sys.path for includes
        if not dirname in sys.path:
            syspathset.add(dirname)
            sys.path = list(syspathset)

        # Loop through all files in passed dirname looking for plugins
        for filename in os.listdir(dirname):
            filename = dirname + os.sep + filename

            # If the file exists
            if os.path.isfile(filename):
                # Split file into a base name plus extension
                basename = os.path.basename(filename)
                base, extension = os.path.splitext(basename)

                # If we're a python file and we don't start with _
                #if extension == ".py" and not basename.startswith("_"):
                # APPPERF-263: If name param is supplied, only attempt to load
                # {name}.py from {app}/bin directory
                if extension == ".py" and ((name is None and not basename.startswith("_")) or base == name):
                    self.logger.debugv("Searching for plugin in file '%s'" % filename)
                    try:
                        # Import the module
                        #module = imp.load_source(base, filename)
                        mod_name, mod_path, mod_desc = imp.find_module(base, [dirname])
                        #TODO: Probably need to adjust module.load() to be added later so this can be pickled.
                        module = imp.load_module(base, mod_name, mod_path, mod_desc)
                        plugin = module.load()

                        # set plugin to something like output.file or generator.default
                        pluginname = plugintype + '.' + base
                        # self.logger.debugv("Filename: %s os.sep: %s pluginname: %s" % (filename, os.sep, pluginname))
                        plugins[pluginname] = plugin

                        # Return is used to determine valid configs, so only return the base name of the plugin
                        ret.append(base)

                        self.logger.debug("Loading module '%s' from '%s'" % (pluginname, basename))

                        # 12/3/13 If we haven't loaded a plugin right or we haven't initialized all the variables
                        # in the plugin, we will get an exception and the plan is to not handle it
                        if 'validSettings' in dir(plugin):
                            self.config._validSettings.extend(plugin.validSettings)
                        if 'defaultableSettings' in dir(plugin):
                            self.config._defaultableSettings.extend(plugin.defaultableSettings)
                        if 'intSettings' in dir(plugin):
                            self.config._intSettings.extend(plugin.intSettings)
                        if 'floatSettings' in dir(plugin):
                            self.config._floatSettings.extend(plugin.floatSettings)
                        if 'boolSettings' in dir(plugin):
                            self.config._boolSettings.extend(plugin.boolSettings)
                        if 'jsonSettings' in dir(plugin):
                            self.config._jsonSettings.extend(plugin.jsonSettings)
                        if 'complexSettings' in dir(plugin):
                            self.config._complexSettings.update(plugin.complexSettings)
                    except ValueError:
                        self.logger.error("Error loading plugin '%s' of type '%s'" % (base, plugintype))
                    except Exception as e:
                        self.logger.exception(e)
                        raise e

        return ret

    def start(self, join_after_start=True):
        self.stopping = False
        self.started = True
        if len(self.config.samples) <= 0:
            self.logger.info("No samples found.  Exiting.")
        for s in self.config.samples:
            if s.interval > 0 or s.mode == 'replay' or s.end != "0":
                self.logger.info("Creating timer object for sample '%s' in app '%s'" % (s.name, s.app) )
                # This is where the timer is finally sent to a queue to be processed.  Needs to move to this object.
                t = Timer(1.0, sample=s, config=self.config,
                          genqueue=self.workerQueue, outputqueue=self.outputQueue, loggingqueue=self.loggingQueue)
                self.sampleQueue.put(t)
        if join_after_start:
            self.logger.info("All timers started, joining queue until it's empty.")
            self.join_process()
        self.started = False
        ## Only need to start timers once
        # Every 5 seconds, get values and output basic statistics about our operations
        #TODO: Figure out how to do this better...
        #generatorsPerSec = (generatorDecrements - generatorQueueCounter) / 5
        #outputtersPerSec = (outputDecrements - outputQueueCounter) / 5
        #outputQueueCounter = outputDecrements
        #generatorQueueCounter = generatorDecrements
        #self.logger.info('OutputQueueDepth=%d  GeneratorQueueDepth=%d GeneratorsPerSec=%d OutputtersPerSec=%d' % (self.config.outputQueueSize.value(), self.config.generatorQueueSize.value(), generatorsPerSec, outputtersPerSec))
        #kiloBytesPerSec = self.config.bytesSent.valueAndClear() / 5 / 1024
        #gbPerDay = (kiloBytesPerSec / 1024 / 1024) * 60 * 60 * 24
        #eventsPerSec = self.config.eventsSent.valueAndClear() / 5
        #self.logger.info('GlobalEventsPerSec=%s KilobytesPerSec=%1f GigabytesPerDay=%1f' % (eventsPerSec, kiloBytesPerSec, gbPerDay))

    def join_process(self):
        '''
        This method will attach the current object to the queues existing for generation and will call stop after all
        generation is complete.  If the queue never finishes, this will lock the main process to the child indefinitly.
        :return:
        '''
        try:
            while not self.sampleQueue.empty() or self.sampleQueue.unfinished_tasks > 0:
                time.sleep(5)
            self.logger.info("All timers have finished, signalling workers to exit.")
            self.stop()
        except Exception as e:
            self.logger.exception(e)
            raise e

    def stop(self):
        # empty the sample queue:
        self.config.stopping = True
        self.stopping = True
        self.started = False
        self.logger.info("All timers exited, joining generation queue until it's empty.")
        self.workerQueue.join()
        # if we're in multiprocess, make sure that since all the timers stopped, we don't let any more generators get added.
        if self.args.multiprocess:
            self.genconfig["stopping"] = True
            for worker in self.workerPool:
                while worker.exitcode == None:
                    self.logger.info("Worker {0} still working, waiting for it to finish.".format(worker._name))
                    time.sleep(1)
        self.logger.info("All generators working/exited, joining output queue until it's empty.")
        self.outputQueue.join()
        self.logger.info("All items fully processed, exiting.")
        self.stopping = False


    def reload_conf(self, configfile):
        '''
        This method will allow a user to supply a new .conf file for generation and reload the sample files.
        :param configfile:
        :return:
        '''
        self._load_config(configfile=configfile)
        self.logger.debug("Config File Loading Complete.")

    def check_running(self):
        '''

        :return: if eventgen is running, return True else False
        '''
        if hasattr(self, "outputQueue") and hasattr(self, "sampleQueue") and hasattr(self, "workerQueue"):
            # If all queues are not empty, eventgen is running.
            # If all queues are empty and all tasks are finished, eventgen is not running.
            # If all queues are empty and there is an unfinished task, eventgen is running.
            if self.outputQueue.empty() and self.sampleQueue.empty() and self.workerQueue.empty():
                self.logger.info("Queues are all empty")
                return (self.outputQueue.unfinished_tasks +
                        self.sampleQueue.unfinished_tasks +
                        self.workerQueue.unfinished_tasks) > 0
            return True
        return False


