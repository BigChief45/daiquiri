#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import logging
import os
import sys
try:
    import syslog
except ImportError:
    syslog = None

from pythonjsonlogger import jsonlogger

from daiquiri import handlers


DEFAULT_FORMAT = (
    "%(asctime)s [%(process)d] %(color)s%(levelname)s "
    "%(name)s: %(message)s%(color_stop)s"
)

TEXT_FORMATTER = logging.Formatter(fmt=DEFAULT_FORMAT)
JSON_FORMATTER = jsonlogger.JsonFormatter()


class Target(object):
    """Generic log target."""

    def __init__(self, handler, formatter=TEXT_FORMATTER, level=logging.INFO):
        self.handler = handler
        self.handler.setFormatter(formatter)
        self.handler.setLevel(level)

    def add_to_logger(self, logger):
        """Add this target to a logger."""
        logger.addHandler(self.handler)


class File(Target):
    def __init__(self, filename=None, directory=None, suffix=".log",
                 binary=None, formatter=TEXT_FORMATTER, level=logging.INFO):
        """Log file target.

        :param filename: The log file path to write to.
        If directory is also specified, both will be combined.
        :param directory: The log directory to write to.
        If no filename is specified, the binary name and suffix will be used
        to contruct the full path relative to the directory.
        :param suffix: The log file name suffix.
        This will be only used if no filename has been provided.
        :param binary: Program name. Autodetected by default.
        """
        logpath = self._get_log_file_path(filename, directory, binary)
        if not logpath:
            raise ValueError("Unable to determine log file destination")
        handler = logging.handlers.WatchedFileHandler(logpath)
        super(File, self).__init__(handler, formatter, level)

    @staticmethod
    def _get_log_file_path(logfile=None, logdir=None, binary=None,
                           logfile_suffix=".log"):
        if not logdir:
            return logfile

        if logfile and logdir:
            return os.path.join(logdir, logfile)

        if logdir:
            binary = binary or handlers._get_binary_name()
            return os.path.join(logdir, binary) + logfile_suffix


class Stream(Target):
    def __init__(self, stream=sys.stderr, formatter=TEXT_FORMATTER,
                 level=logging.INFO):
        super(Stream, self).__init__(handlers.ColorStreamHandler(stream),
                                     formatter, level)


STDERR = Stream()
STDOUT = Stream(sys.stdout)


class Journal(Target):
    def __init__(self, formatter=TEXT_FORMATTER, level=logging.INFO):
        super(Journal, self).__init__(handlers.JournalHandler(),
                                      formatter, level)


class Syslog(Target):
    def __init__(self, facility="user", formatter=TEXT_FORMATTER,
                 level=logging.INFO):
        if syslog is None:
            # FIXME(jd) raise something more specific
            raise RuntimeError("syslog is not available on this platform")
        super(Syslog, self).__init__(
            handlers.SyslogHandler(facility=self._find_facility(facility)),
            formatter, level)

    @staticmethod
    def _find_facility(facility):
        # NOTE(jd): Check the validity of facilities at run time as they differ
        # depending on the OS and Python version being used.
        valid_facilities = [f for f in
                            ["LOG_KERN", "LOG_USER", "LOG_MAIL",
                             "LOG_DAEMON", "LOG_AUTH", "LOG_SYSLOG",
                             "LOG_LPR", "LOG_NEWS", "LOG_UUCP",
                             "LOG_CRON", "LOG_AUTHPRIV", "LOG_FTP",
                             "LOG_LOCAL0", "LOG_LOCAL1", "LOG_LOCAL2",
                             "LOG_LOCAL3", "LOG_LOCAL4", "LOG_LOCAL5",
                             "LOG_LOCAL6", "LOG_LOCAL7"]
                            if getattr(syslog, f, None)]

        facility = facility.upper()

        if not facility.startswith("LOG_"):
            facility = "LOG_" + facility

        if facility not in valid_facilities:
            raise TypeError('syslog facility must be one of: %s' %
                            ', '.join("'%s'" % fac
                                      for fac in valid_facilities))

        return getattr(syslog, facility)
