from __future__ import division
from generatorplugin import GeneratorPlugin
import datetime, time, os
from jinja2 import Environment, FileSystemLoader, select_autoescape

class CantFindTemplate(Exception):

    def __init__(self, msg):
        """Exception raised when we / Jinja can't find the template

        :param msg: (str) The message to send back to the user
        """
        self.msg = msg
        super(CantFindTemplate, self).__init__(msg)

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
                extensions=['jinja2.ext.loopcontrols'],
                autoescape=select_autoescape(['html', 'xml'])
            )
            jinja_loaded_template = jinja_env.get_template(str(self._sample.jinja_target_template))
            jinja_stream = jinja_loaded_template.stream()
            for line in  jinja_stream:
                if line != "\n":
                    #TODO: Time can be supported by self._sample.timestamp, should probably set that up in this logic.
                    self._out.send(line.lstrip('\n'))
            endTime = datetime.datetime.now()
            timeDiff = endTime - startTime
            timeDiffFrac = "%d.%06d" % (timeDiff.seconds, timeDiff.microseconds)
            self.logger.debugv("Interval complete, flushing feed")
            self._out.flush(endOfInterval=True)
            self.logger.debug("Generation of sample '%s' completed in %s seconds." % (self._sample.name, timeDiffFrac) )
            return 0
        except Exception as e:
            self.logger.exception(e)
            return 1

def load():
    return JinjaGenerator
