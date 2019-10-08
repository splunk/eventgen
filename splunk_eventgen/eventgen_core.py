#!/usr/bin/env python
# encoding: utf-8
import imp
import logging
import logging.config
import os
import sys
import time
from Queue import Empty, Queue
from threading import Thread
import multiprocessing

from lib.eventgenconfig import Config
from lib.eventgenexceptions import PluginNotLoaded
from lib.eventgentimer import Timer
from lib.outputcounter import OutputCounter
from lib.logging_config import logger

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

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
EVENTGEN_DIR = os.path.realpath(os.path.join(FILE_PATH, ".."))
EVENTGEN_ENGINE_CONF_PATH = os.path.abspath(os.path.join(FILE_PATH, "default", "eventgen_engine.conf"))


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
        self.force_stop = False
        self.started = False
        self.completed = False
        self.config = None
        self.args = args

        self._setup_loggers(args=args)
        # attach to the logging queue
        self.logger.info("Logging Setup Complete.")

        self._generator_queue_size = getattr(self.args, 'generator_queue_size', 500)
        if self._generator_queue_size < 0:
            self._generator_queue_size = 0
        self.logger.info("Set generator queue size", queue_size=self._generator_queue_size)

        if self.args and 'configfile' in self.args and self.args.configfile:
            self._load_config(self.args.configfile, args=args)

    def _load_config(self, configfile, **kwargs):
        '''
        This method will use a configfile and set self.confg as a processeded config object,
        kwargs will need to match eventgenconfig.py
        :param configfile:
        :return:
        '''
        # TODO: The old eventgen had strange cli args. We should probably update the module args to match this usage.
        new_args = {}
        if "args" in kwargs:
            args = kwargs["args"]
            outputer = [key for key in ["keepoutput", "devnull", "modinput"] if getattr(args, key)]
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
            if getattr(args, "sample"):
                new_args["sample"] = args.sample
            if getattr(args, "verbosity"):
                new_args["verbosity"] = args.verbosity
        self.config = Config(configfile, **new_args)
        self.config.parse()
        self.args.multiprocess = True if self.config.threading == "process" else self.args.multiprocess
        self._reload_plugins()
        if "args" in kwargs and getattr(kwargs["args"], "generators"):
            generator_worker_count = kwargs["args"].generators
        else:
            generator_worker_count = self.config.generatorWorkers

        # TODO: Probably should destroy pools better so processes are cleaned.
        if self.args.multiprocess:
            self.kill_processes()
        self._setup_pools(generator_worker_count)

    def _reload_plugins(self):
        # Initialize plugins
        # Plugins must be loaded before objects that do work, otherwise threads and processes generated will not have
        # the modules loaded in active memory.
        try:
            self.config.outputPlugins = {}
            plugins = self._initializePlugins(
                os.path.join(FILE_PATH, 'lib', 'plugins', 'output'), self.config.outputPlugins, 'output')
            self.config.validOutputModes.extend(plugins)
            self._initializePlugins(
                os.path.join(FILE_PATH, 'lib', 'plugins', 'generator'), self.config.plugins, 'generator')
            plugins = self._initializePlugins(
                os.path.join(FILE_PATH, 'lib', 'plugins', 'rater'), self.config.plugins, 'rater')
            self.config._complexSettings['rater'] = plugins
        except Exception as e:
            self.logger.exception(str(e))

    def _load_custom_plugins(self, PluginNotLoadedException):
        plugintype = PluginNotLoadedException.type
        plugin = PluginNotLoadedException.name
        bindir = PluginNotLoadedException.bindir
        plugindir = PluginNotLoadedException.plugindir
        pluginsdict = self.config.plugins if plugintype in ('generator', 'rater') else self.config.outputPlugins
        # APPPERF-263: be picky when loading from an app bindir (only load name)
        self._initializePlugins(bindir, pluginsdict, plugintype, name=plugin)

        # APPPERF-263: be greedy when scanning plugin dir (eat all the pys)
        self._initializePlugins(plugindir, pluginsdict, plugintype)

    def _setup_pools(self, generator_worker_count=20):
        '''
        This method is an internal method called on init to generate pools needed for processing.

        :return:
        '''
        # Load the things that actually do the work.
        self._create_generator_pool()
        self._create_timer_threadpool()
        self._create_output_threadpool()
        if self.args.multiprocess:
            self.pool = multiprocessing.Pool(generator_worker_count, maxtasksperchild=1000000)

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
        self.timer_thread_pool = []
        for i in range(num_threads):
            worker = Thread(target=self._worker_do_work, args=(
                self.sampleQueue,
                self.loggingQueue,
            ), name="TimeThread{0}".format(i))
            self.timer_thread_pool.append(worker)
            worker.setDaemon(True)
            worker.start()

    def _create_output_threadpool(self, threadcount=1):
        '''
        the output thread pool is used for output plugins that need to control file locking, or only have 1 set thread
        to send all the data out of. This FIFO queue just helps make sure there are file collisions or write collisions.
        There's only 1 active thread for this queue, if you're ever considering upping this, don't.  Just shut off the
        outputQueue and let each generator directly output it's data.
        :param threadcount: is how many active output threads we want to allow inside of eventgen.  Default 1
        :return:
        '''
        # TODO: Make this take the config param and figure out what we want to do with this.
        if getattr(self, "manager", None):
            self.outputQueue = self.manager.Queue(maxsize=500)
        else:
            self.outputQueue = Queue(maxsize=500)
        num_threads = threadcount
        self.output_thread_pool = []
        for i in range(num_threads):
            worker = Thread(target=self._worker_do_work, args=(
                self.outputQueue,
                self.loggingQueue,
            ), name="OutputThread{0}".format(i))
            self.output_thread_pool.append(worker)
            worker.setDaemon(True)
            worker.start()

    def _create_generator_pool(self, workercount=20):
        '''
        The generator pool has two main options, it can run in multiprocessing or in threading.  We check the argument
        from configuration, and then build the appropriate queue type.  Each time a timer runs for a sample, if the
        timer says it's time to generate, it will create a new generator plugin object, and place it in this queue.
        :param workercount: is how many active workers we want to allow inside of eventgen.  Default 10.  If someone
                            has over 10 generators working, additional samples won't run until the first ones end.
        :return:
        '''
        if self.args.multiprocess:
            self.manager = multiprocessing.Manager()
            if self.config.disableLoggingQueue:
                self.loggingQueue = None
            else:
                # TODO crash caused by logging Thread https://github.com/splunk/eventgen/issues/217
                self.loggingQueue = self.manager.Queue()
                self.logging_pool = Thread(target=self.logger_thread, args=(self.loggingQueue, ), name="LoggerThread")
                self.logging_pool.start()
            # since we're now in multiprocess, we need to use better queues.
            self.workerQueue = multiprocessing.JoinableQueue(maxsize=self._generator_queue_size)
            self.genconfig = self.manager.dict()
            self.genconfig["stopping"] = False
        else:
            self.workerQueue = Queue(maxsize=self._generator_queue_size)
            worker_threads = workercount
            if hasattr(self.config, 'outputCounter') and self.config.outputCounter:
                self.output_counters = []
                for i in range(workercount):
                    self.output_counters.append(OutputCounter())
                for i in range(worker_threads):
                    worker = Thread(target=self._generator_do_work, args=(self.workerQueue, self.loggingQueue,
                                                                          self.output_counters[i]))
                    worker.setDaemon(True)
                    worker.start()
            else:
                for i in range(worker_threads):
                    worker = Thread(target=self._generator_do_work, args=(self.workerQueue, self.loggingQueue, None))
                    worker.setDaemon(True)
                    worker.start()

    def _setup_loggers(self, args=None):
        self.logger = logger
        self.loggingQueue = None
        if args and args.verbosity:
            self.logger.setLevel(args.verbosity)
        # Set the default log level to ERROR when directly called Generator in tests
        if args.verbosity is None:
            self.logger.setLevel(logging.ERROR)

    def _worker_do_work(self, work_queue, logging_queue):
        while not self.stopping:
            try:
                item = work_queue.get(timeout=10)
                startTime = time.time()
                item.run()
                totalTime = time.time() - startTime
                if totalTime > self.config.interval and self.config.end != 1:
                    self.logger.warning("work took longer than current interval, queue/threading throughput limitation")
                work_queue.task_done()
            except Empty:
                pass
            except Exception as e:
                self.logger.exception(str(e))
                raise e

    def _generator_do_work(self, work_queue, logging_queue, output_counter=None):
        while not self.stopping:
            try:
                item = work_queue.get(timeout=10)
                startTime = time.time()
                item.run(output_counter=output_counter)
                totalTime = time.time() - startTime
                if totalTime > self.config.interval and item._sample.end != 1:
                    self.logger.warning("work took longer than current interval, queue/threading throughput limitation")
                work_queue.task_done()
            except Empty:
                pass
            except Exception as e:
                if self.force_stop:
                    break
                self.logger.exception(str(e))
                raise e

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
                if self.force_stop:
                    break
                self.logger.exception(str(e))
                raise e

    def _initializePlugins(self, dirname, plugins, plugintype, name=None):
        """Load a python module dynamically and add to internal dictionary of plugins (only accessed by getPlugin)"""
        ret = []
        syspathset = set(sys.path)

        dirname = os.path.abspath(dirname)
        self.logger.debug("looking for plugin(s) in {}".format(dirname))
        if not os.path.isdir(dirname):
            self.logger.debug("directory {} does not exist ... moving on".format(dirname))
            return ret

        # Include all plugin directories in sys.path for includes
        if dirname not in sys.path:
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
                # if extension == ".py" and not basename.startswith("_"):
                # APPPERF-263: If name param is supplied, only attempt to load
                # {name}.py from {app}/bin directory
                if extension == ".py" and ((name is None and not basename.startswith("_")) or base == name):
                    self.logger.debug("Searching for plugin in file '%s'" % filename)
                    try:
                        # Import the module
                        # module = imp.load_source(base, filename)
                        mod_name, mod_path, mod_desc = imp.find_module(base, [dirname])
                        # TODO: Probably need to adjust module.load() to be added later so this can be pickled.
                        module = imp.load_module(base, mod_name, mod_path, mod_desc)
                        plugin = module.load()

                        # set plugin to something like output.file or generator.default
                        pluginname = plugintype + '.' + base
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
                    except ImportError as ie:
                        self.logger.warning("Could not load plugin: %s, skipping" % mod_name.name)
                        self.logger.exception(ie)
                    except Exception as e:
                        self.logger.exception(str(e))
                        raise e
        return ret

    def start(self, join_after_start=True):
        self.stopping = False
        self.started = True
        self.config.stopping = False
        self.completed = False
        if len(self.config.samples) <= 0:
            self.logger.info("No samples found.  Exiting.")
        for s in self.config.samples:
            if s.interval > 0 or s.mode == 'replay' or s.end != "0":
                self.logger.info("Creating timer object for sample '%s' in app '%s'" % (s.name, s.app))
                # This is where the timer is finally sent to a queue to be processed.  Needs to move to this object.
                try:
                    if self.args.multiprocess:
                        t = Timer(1.0, sample=s, config=self.config, genqueue=self.workerQueue,
                                  outputqueue=self.outputQueue, loggingqueue=self.loggingQueue, pool=self.pool)
                    else:
                        t = Timer(1.0, sample=s, config=self.config, genqueue=self.workerQueue,
                                  outputqueue=self.outputQueue, loggingqueue=self.loggingQueue)
                except PluginNotLoaded as pnl:
                    self._load_custom_plugins(pnl)
                    t = Timer(1.0, sample=s, config=self.config, genqueue=self.workerQueue,
                              outputqueue=self.outputQueue, loggingqueue=self.loggingQueue)
                except Exception as e:
                    raise e
                self.sampleQueue.put(t)
        if join_after_start:
            self.logger.info("All timers started, joining queue until it's empty.")
            self.join_process()

    def join_process(self):
        '''
        This method will attach the current object to the queues existing for generation and will call stop after all
        generation is complete.  If the queue never finishes, this will lock the main process to the child indefinitely.
        :return:
        '''
        try:
            while not self.sampleQueue.empty() or self.sampleQueue.unfinished_tasks > 0 or not self.workerQueue.empty():
                time.sleep(5)
            self.logger.info("All timers have finished, signalling workers to exit.")
            self.stop()
        except Exception as e:
            self.logger.exception(str(e))
            raise e

    def stop(self, force_stop=False):
        # empty the sample queue:
        self.config.stopping = True
        self.stopping = True
        self.force_stop = force_stop

        # join timer thread and output thread
        for output_thread in self.output_thread_pool:
            output_thread.join()
        for timer_thread in self.timer_thread_pool:
            timer_thread.join()

        self.logger.info("All timers exited, joining generation queue until it's empty.")
        if force_stop:
            self.logger.info("Forcibly stopping Eventgen: Deleting workerQueue.")
            del self.workerQueue
            self._create_generator_pool()
        self.workerQueue.join()
        # if we're in multiprocess, make sure we don't add more generators after the timers stopped.
        if self.args.multiprocess:
            if force_stop:
                self.kill_processes()
            else:
                self.genconfig["stopping"] = True
                self.pool.close()
                self.pool.join()

        self.logger.info("All generators working/exited, joining output queue until it's empty.")
        if not self.args.multiprocess and not force_stop:
            self.outputQueue.join()
        self.logger.info("All items fully processed. Cleaning up internal processes.")
        self.started = False
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
            if not self.args.multiprocess:
                if self.outputQueue.empty() and self.sampleQueue.empty() and self.workerQueue.empty() \
                        and self.sampleQueue.unfinished_tasks <= 0 \
                        and self.outputQueue.unfinished_tasks <= 0 \
                        and self.workerQueue.unfinished_tasks <= 0:
                    self.logger.info("Queues are all empty and there are no pending tasks")
                    return self.started
                else:
                    return True
            else:
                if self.outputQueue.empty() and self.sampleQueue.empty() and self.workerQueue.empty() \
                        and self.sampleQueue.unfinished_tasks <= 0:
                    self.logger.info("Queues are all empty and there are no pending tasks")
                    return self.started
                else:
                    return True
        return False

    def check_done(self):
        '''

        :return: if eventgen jobs are finished, return True else False
        '''
        return self.sampleQueue.empty() and self.sampleQueue.unfinished_tasks <= 0 and self.workerQueue.empty()

    def kill_processes(self):
        if self.args.multiprocess and hasattr(self, "pool"):
            self.pool.close()
            self.pool.terminate()
            self.pool.join()
            del self.outputQueue
            self.manager.shutdown()
