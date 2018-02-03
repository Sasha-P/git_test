# -*- coding: utf-8 -*-
# Copyright 2016-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import shlex
import sys

from builtins import object
from io import StringIO

import pexpect

from .exception import OperationError
from .helpers import string_types


class Operation(object):

    def __init__(self, command):
        if isinstance(command, string_types):
            command = self._shlex_split_unicode(command)
        self.command = command

    @staticmethod
    def _shlex_split_unicode(command):
        if sys.version_info < (3, 4):
            return [l.decode('utf8') for l in shlex.split(
                command.encode('utf-8'))]
        else:
            return shlex.split(command)

    def __bool__(self):
        return bool(self.command)

    def _execute(self, log, interactive=True):
        assert self.command
        executable = self.command[0]
        params = self.command[1:]
        child = pexpect.spawn(executable, params, timeout=None,
                              encoding='utf8')
        # interact() will transfer the child's stdout to
        # stdout, but we also copy the output in a buffer
        # so we can save the logs in the database
        log_buffer = StringIO()
        if interactive:
            # use the interactive mode so we can use pdb in the
            # migration scripts
            child.interact()
        else:
            # set the logfile to stdout so we have an unbuffered
            # output
            child.logfile = sys.stdout
            child.expect(pexpect.EOF)
            # child.before contains all the the output of the child program
            # before the EOF
            # child.before is unicode
            log_buffer.write(child.before)
        child.close()
        if child.signalstatus is not None:
            raise OperationError(
                u"command '{}' has been interrupted by signal {}".format(
                    ' '.join(self.command),
                    child.signalstatus
                )
            )
        elif child.exitstatus != 0:
            raise OperationError(
                u"command '{}' returned {}".format(
                    ' '.join(self.command),
                    child.exitstatus
                )
            )
        log_buffer.seek(0)
        # the pseudo-tty used for the child process returns
        # lines with \r\n endings
        msg = '\n'.join(log_buffer.read().splitlines())
        log(msg, decorated=False, stdout=False)

    def execute(self, log):
        log(u'{}'.format(u' '.join(self.command)))
        self._execute(log, interactive=sys.stdout.isatty())

    def __repr__(self):
        return u'Operation<{}>'.format(' '.join(self.command))
