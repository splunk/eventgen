# Note as implemented this plugin is not threadsafe, file should only be used with one output worker
import os

from splunk_eventgen.lib.logging_config import logger
from splunk_eventgen.lib.outputplugin import OutputPlugin


class FileOutputPlugin(OutputPlugin):
    name = "file"
    MAXQUEUELENGTH = 10
    useOutputQueue = False

    validSettings = ["fileMaxBytes", "fileBackupFiles"]
    intSettings = ["fileMaxBytes", "fileBackupFiles"]

    def __init__(self, sample, output_counter=None):
        OutputPlugin.__init__(self, sample, output_counter)

        if sample.fileName is None:
            logger.error(
                "outputMode file but file not specified for sample %s"
                % self._sample.name
            )
            raise ValueError(
                "outputMode file but file not specified for sample %s"
                % self._sample.name
            )

        self._file = sample.pathParser(sample.fileName)
        self._fileMaxBytes = sample.fileMaxBytes
        self._fileBackupFiles = sample.fileBackupFiles

        self._fileHandle = open(self._file, "a")
        self._fileLength = os.stat(self._file).st_size
        logger.debug(
            "Configured to log to '%s' with maxBytes '%s' with backupCount '%s'"
            % (self._file, self._fileMaxBytes, self._fileBackupFiles)
        )

    def flush(self, q):
        if len(q) > 0:
            logger.debug(
                "Flushing output for sample '%s' in app '%s' for queue '%s'"
                % (self._sample.name, self._app, self._sample.source)
            )

            # Loop through all the messages and build the long string, write once for each flush
            # This may cause the file exceed the maxFileBytes a little bit but will greatly improve the performance
            try:
                for metamsg in q:
                    msg = metamsg.get("_raw")
                    if not msg:
                        continue
                    if msg[-1] != "\n":
                        msg += "\n"

                    if self._fileLength + len(msg) <= self._fileMaxBytes:
                        self._fileHandle.write(msg)
                        self._fileLength += len(msg)
                    else:
                        self._fileHandle.flush()
                        self._fileHandle.close()

                        if os.path.exists(
                            self._file + "." + str(self._fileBackupFiles)
                        ):
                            logger.debug(
                                "File Output: Removing file: %s" % self._file
                                + "."
                                + str(self._fileBackupFiles)
                            )
                            os.unlink(self._file + "." + str(self._fileBackupFiles))

                        for x in range(1, int(self._fileBackupFiles))[::-1]:
                            logger.debug(
                                "File Output: Checking for file: %s" % self._file
                                + "."
                                + str(x)
                            )
                            if os.path.exists(self._file + "." + str(x)):
                                logger.debug(
                                    "File Output: Renaming file %s to %s"
                                    % (
                                        self._file + "." + str(x),
                                        self._file + "." + str(x + 1),
                                    )
                                )
                                os.rename(
                                    self._file + "." + str(x),
                                    self._file + "." + str(x + 1),
                                )

                        os.rename(self._file, self._file + ".1")
                        self._fileHandle = open(self._file, "w")
                        self._fileHandle.write(msg)
                        self._fileLength = len(msg)
            except IndexError:
                logger.warning(
                    "IndexError when writting for app '%s' sample '%s'"
                    % (self._app, self._sample.name)
                )

            if not self._fileHandle.closed:
                self._fileHandle.flush()
            logger.debug(
                "Queue for app '%s' sample '%s' written"
                % (self._app, self._sample.name)
            )

            self._fileHandle.close()


def load():
    """Returns an instance of the plugin"""
    return FileOutputPlugin
