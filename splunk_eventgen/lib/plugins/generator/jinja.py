from __future__ import division
from generatorplugin import GeneratorPlugin
import datetime, time, os, json
from jinja2 import Environment, FileSystemLoader, select_autoescape, lexer, nodes
from jinja2.ext import Extension

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

class JinjaNow(Extension):
    tags = set(['now', 'datetime', 'timedelta'])

    def _now(self, date_format=None):
        formatted = datetime.datetime.now().strftime(date_format)
        return formatted

    def parse(self, parser):
        target_var_name = {
            "now": "time_now"
        }
        tag = parser.stream.current.value
        lineno = parser.stream.next().lineno
        target_method = "_{0}".format(tag)
        args, kwargs = self.parse_args(parser)
        call = self.call_method(target_method, args=args, kwargs=kwargs, lineno=lineno)
        as_var = nodes.Name(target_var_name[tag], 'store', lineno=lineno)
        return nodes.Assign(as_var, call, lineno=lineno)

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
    def __init__(self, sample):
        GeneratorPlugin.__init__(self, sample)

    def gen(self, count, earliest, latest, samplename=None):
        #TODO: Figure out how to gracefully tell generator plugins to exit when there is an error.
        try:
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
                extensions=['jinja2.ext.do', 'jinja2.ext.with_','jinja2.ext.loopcontrols', JinjaNow],
                autoescape=select_autoescape(['html', 'xml'])
            )
            jinja_loaded_template = jinja_env.get_template(str(self._sample.jinja_target_template))
            if hasattr(self._sample, 'jinja_variables'):
                jinja_loaded_vars = json.loads(self._sample.jinja_variables)
            else:
                jinja_loaded_vars = None
            jinja_stream = jinja_loaded_template.stream(jinja_loaded_vars)
            try:
                for line in jinja_stream:
                    if line != "\n":
                        #TODO: Time can be supported by self._sample.timestamp, should probably set that up in this logic.
                        self._out.send(line.lstrip('\n'))
            except TypeError as e:
                self.logger.exception(e)
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
