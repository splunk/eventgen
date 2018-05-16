from __future__ import division
from generatorplugin import GeneratorPlugin
import datetime, time, os
try:
    import ujson as json
except:
    import json as json

from jinja2 import nodes
from jinja2.ext import Extension

import random

class CantFindTemplate(Exception):

    def __init__(self, msg):
        """Exception raised when we / Jinja can't find the template

        :param msg: (str) The message to send back to the user
        """
        self.msg = msg
        super(CantFindTemplate, self).__init__(msg)

class CantProcessTemplate(Exception):

    def __init__(self, msg):
        """Exception raised when we / Jinja can't find the template

        :param msg: (str) The message to send back to the user
        """
        self.msg = msg
        super(CantProcessTemplate, self).__init__(msg)

class JinjaTime(Extension):
    tags = set(['time_now', 'time_slice', 'time_delta', 'time_backfill'])

    @staticmethod
    def _get_time_slice(earliest, latest, slices, target_slice, slice_type="lower"):
        """
        This method will take a time block bounded by "earliest and latest", and a slice.  It'll then divide the time
        in sections and return a tuple with 3 arugments, the lower bound, the higher bound, and the target in the middle.
        :param earliest (in epoch):
        :param latest (in epoch):
        :param slices:
        :param target_slice:
        :param slice_type [lower,upper,middle,random]:
        :return:
        """
        earliest = float(earliest)
        latest = float(latest)
        slices = int(slices)
        target_slice = int(target_slice)
        time_span = latest - earliest
        slice_size = time_span / slices
        slice_start = (slice_size * target_slice) + earliest
        slice_end = slice_start + slice_size
        slice_time = float()
        if slice_type == "lower":
            slice_time = slice_start
        elif slice_type == "middle":
            slice_time = slice_start + (slice_size/2)
        elif slice_type == "upper":
            slice_time = slice_end
        elif slice_type == "random":
            start = int(slice_start*100)
            end = int(slice_end*100)
            if start == end:
                slice_time = end * 0.01
            else:
                slice_time = random.randrange(start, end) * 0.01
        return slice_start, slice_end, slice_size, slice_time

    def _convert_epoch_formatted(self, epoch_time, date_format):
        datetime_timenow = datetime.datetime.fromtimestamp(epoch_time)
        formatted = datetime_timenow.strftime(date_format)
        return formatted

    def _time_now_formatted(self, date_format='%Y-%m-%dT%H:%M:%S%z'):
        time_now = self._time_now_epoch()
        return self._convert_epoch_formatted(time_now, date_format)

    def _time_now_epoch(self):
        time_now = time.mktime(time.localtime())
        return time_now

    def _time_slice_formatted(self,earliest, latest, count, slices, date_format='%Y-%m-%dT%H:%M:%S%z'):
        target_time = self._time_slice_epoch(earliest, latest, count, slices)
        return self._convert_epoch_formatted(target_time, date_format)

    def _time_slice_epoch(self, earliest, latest, count, slices):
        slice_start, slice_end, slice_size, slice_time = \
            self._get_time_slice(earliest=earliest, latest=latest, slices=slices, target_slice=count, slice_type="lower")
        return slice_time

    @staticmethod
    def _set_var(var_name, var_value, lineno):
        target_var = nodes.Name(var_name, 'store', lineno=lineno)
        return nodes.Assign(target_var, var_value, lineno=lineno)

    @staticmethod
    def _output_var(var_value, lineno):
        return nodes.Output([var_value], lineno=lineno)

    def parse(self, parser):
        target_var_name = {
            "time_now": "time_now",
            "time_slice": "time_target"
        }
        tag = parser.stream.current.value
        name_base = target_var_name[tag]
        lineno = parser.stream.next().lineno
        args, kwargs = self.parse_args(parser)
        task_list = []
        epoch_name = name_base+"_epoch"
        formatted_name = name_base+"_formatted"
        target_epoch_method = "_{0}_epoch".format(tag)
        target_formatted_method = "_{0}_formatted".format(tag)
        epoch_call = self.call_method(target_epoch_method, args=args, kwargs=kwargs, lineno=lineno)
        formatted_call = self.call_method(target_formatted_method, args=args, kwargs=kwargs, lineno=lineno)
        task_list.append(self._set_var(epoch_name, epoch_call, lineno))
        task_list.append(self._set_var(formatted_name, formatted_call, lineno))
        return task_list

    def parse_args(self, parser):
        args = []
        kwargs = []
        require_comma = False
        while parser.stream.current.type != 'block_end':
            if require_comma:
                parser.stream.expect('comma')
            if parser.stream.current.type == 'name' and parser.stream.look().type == 'assign':
                key = parser.stream.current.value
                parser.stream.skip(2)
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=value.lineno))
            else:
                if kwargs:
                    parser.fail('Invalid argument syntax for WrapExtension tag',
                                parser.stream.current.lineno)
                args.append(parser.parse_expression())
            require_comma = True
        return args, kwargs


class JinjaGenerator(GeneratorPlugin):
    validSettings = ['jinja_count_type', 'jinja_target_template', 'jinja_template_dir']
    defaultableSettings = ['jinja_count_type', 'jinja_target_template', 'jinja_template_dir']
    jsonSettings = ['jinja_variables']

    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)
        self.current_count = 0
        self.target_count = 0
        self.earliest = None
        self.latest = None
        self.jinja_count_type = "cycles"
        self.end_of_cycle = False

    def _increment_count(self, lines):
        """
        Helper function that keeps track of the count of the current generation.
        :param line:
        :return:
        """
        if self.jinja_count_type == "perDayVolume":
            for line in lines:
                self.current_count = self.current_count + len(line)
        elif self.jinja_count_type == "count":
            self.current_count = self.current_count + len(lines)
        elif self.jinja_count_type == "cycles":
            self.current_count = self.current_count + 1
        else:
            raise Exception("Unable to process target count style: %s".format(self.jinja_count_type))

    def gen(self, count, earliest, latest, samplename=None):
        #TODO: Figure out how to gracefully tell generator plugins to exit when there is an error.
        try:
            from jinja2 import Environment, FileSystemLoader
            self.target_count = count
            # assume that if there is no "count" field, we want to run 1 time, and only one time.
            if self.target_count == -1:
                self.target_count = 1
            self.earliest = earliest
            self.latest = latest
            if hasattr(self._sample, "jinja_count_type"):
                if self._sample.jinja_count_type in ["line_count", "cycles", "perDayVolume"]:
                    self.jinja_count_type = self._sample.jinja_count_type
            startTime = datetime.datetime.now()
            working_dir, working_config_file = os.path.split(self.config.configfile)
            if not hasattr(self._sample, "jinja_template_dir"):
                template_dir = "templates"
            else:
                template_dir = self._sample.jinja_template_dir
            target_template_dir = os.path.join(working_dir, template_dir)
            if not hasattr(self._sample, "jinja_target_template"):
                raise CantFindTemplate("Template to load not specified in eventgen conf for stanza.  Skipping Stanza")
            jinja_env = Environment(
                loader=FileSystemLoader([target_template_dir, working_dir, template_dir], encoding='utf-8',  followlinks=False),
                extensions=['jinja2.ext.do', 'jinja2.ext.with_','jinja2.ext.loopcontrols', JinjaTime],
                line_statement_prefix="#",
                line_comment_prefix="##"
            )
            jinja_loaded_template = jinja_env.get_template(str(self._sample.jinja_target_template))
            if hasattr(self._sample, 'jinja_variables'):
                jinja_loaded_vars = json.loads(self._sample.jinja_variables)
            else:
                jinja_loaded_vars = None
            # make the default generator vars accessable to jinja
            jinja_loaded_vars["eventgen_count"] = self.current_count
            jinja_loaded_vars["eventgen_maxcount"] = self.target_count
            jinja_loaded_vars["eventgen_earliest"] = self.earliest
            self.earliest_epoch = (self.earliest - datetime.datetime(1970,1,1)).total_seconds()
            jinja_loaded_vars["eventgen_earliest_epoch"] = self.earliest_epoch
            jinja_loaded_vars["eventgen_latest"] = self.latest
            jinja_loaded_vars["eventgen_latest_epoch"] = (self.latest - datetime.datetime(1970,1,1)).total_seconds()
            self.latest_epoch = (self.latest - datetime.datetime(1970,1,1)).total_seconds()
            while self.current_count < self.target_count:
                self.end_of_cycle = False
                jinja_loaded_vars["eventgen_count"] = self.current_count
                jinja_loaded_vars["eventgen_target_time_earliest"], jinja_loaded_vars["eventgen_target_time_latest"], \
                jinja_loaded_vars["eventgen_target_time_slice_size"], jinja_loaded_vars["eventgen_target_time_epoch"] = \
                    JinjaTime._get_time_slice(self.earliest_epoch, self.latest_epoch, self.target_count, self.current_count, slice_type="random")
                self.jinja_stream = jinja_loaded_template.stream(jinja_loaded_vars)
                lines_out = []
                try:
                    for line in self.jinja_stream:
                        if line != "\n":
                            #TODO: Time can be supported by self._sample.timestamp, should probably set that up in this logic.
                            try:
                                target_line = json.loads(line)
                            except ValueError as e:
                                self.logger.error("Unable to parse Jinja's return.  Line: {0}".format(line))
                                self.logger.error("Parse Failure Reason: {0}".format(e.message))
                                self.logger.error("Please note, you must meet the requirements for json.loads in python if you have not installed ujson. Native python does not support multi-line events.")
                                continue
                            current_line_keys = target_line.keys()
                            if "_time" not in current_line_keys:
                                #TODO: Add a custom exception here
                                raise Exception("No _time field supplied, please add time to your jinja template.")
                            if "_raw" not in current_line_keys:
                                #TODO: Add a custom exception here
                                raise Exception("No _raw field supplied, please add time to your jinja template.")
                            if "host" not in current_line_keys:
                                target_line["host"] = self._sample.host
                            if "hostRegex" not in current_line_keys:
                                target_line["hostRegex"] = self._sample.hostRegex
                            if "source" not in current_line_keys:
                                target_line["source"] = self._sample.source
                            if "sourcetype" not in current_line_keys:
                                target_line["sourcetype"] = self._sample.sourcetype
                            lines_out.append(target_line)
                        else:
                            break
                except TypeError as e:
                    self.logger.exception(e)
                self.end_of_cycle = True
                self._increment_count(lines_out)
                self._out.bulksend(lines_out)
            endTime = datetime.datetime.now()
            timeDiff = endTime - startTime
            timeDiffFrac = "%d.%06d" % (timeDiff.seconds, timeDiff.microseconds)
            self.logger.debugv("Interval complete, flushing feed")
            self._out.flush(endOfInterval=True)
            self.logger.info("Generation of sample '%s' completed in %s seconds." % (self._sample.name, timeDiffFrac) )
            return 0
        except Exception as e:
            self.logger.exception(e)
            return 1

def load():
    return JinjaGenerator
