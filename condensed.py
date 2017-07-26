# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
from collections import OrderedDict

from ansible.plugins.callback.default import CallbackModule as CallbackModule_default
from ansible import constants as C
from ansible.utils.color import stringc, hostcolor, colorize
from ansible.module_utils._text import to_bytes, to_text
from ansible.utils.display import Display

try:
    from __main__ import display as global_display
except ImportError:
    global_display = Display()

class CallbackModule(CallbackModule_default):

    '''
    This is the default callback interface, which simply prints messages
    to stdout when new callback events are received.
    '''

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'condensed'

    _progress = OrderedDict()

    class CallbackDisplay(Display):

        def banner(self, msg, color=None, cows=False, newline=True):
            msg = msg.strip()
            if newline:
                msg = u"\n" + msg
            self.display(u"%s" % (msg), color=color)

        def display(self, msg, color=None, stderr=False, screen_only=False, log_only=False):
            if color:
                msg = stringc(msg, color)
            msg2 = to_bytes(msg, encoding=self._output_encoding(stderr=stderr))
            if sys.version_info >= (3,):
                msg2 = to_text(msg2, self._output_encoding(stderr=stderr), errors='replace')
            if not stderr:
                fileobj = sys.stdout
            else:
                fileobj = sys.stderr
            fileobj.write(msg2)
            try:
                fileobj.flush()
            except IOError as e:
                if e.errno != errno.EPIPE:
                    raise

        def clear_line(self):
            sys.stdout.write("\r" + " " * self.columns + "\r")
            sys.stdout.flush()

    def __init__(self):
        self.super_ref = super(CallbackModule, self)
        self.super_ref.__init__()
        self._display = self.CallbackDisplay(verbosity=global_display.verbosity)

    def v2_runner_on_skipped(self, result):
        pass

    def v2_runner_item_on_skipped(self, result):
        pass

    def _print_task_banner(self, task):

        newline = True
        while self._progress != {}:
            last = self._progress.keys()[-1]
            if self._progress[last] == None:
                del self._progress[last]
                self._display.clear_line()
                newline = False
            else:
                break

        self._progress[task._uuid] = None
        args = ''
        if not task.no_log and C.DISPLAY_ARGS_TO_STDOUT:
            args = u', '.join(u'%s=%s' % a for a in task.args.items())
            args = u' %s' % args

        self._display.banner(u"TASK [%s%s]" % (task.get_name().strip(), args), newline=newline)
        if self._display.verbosity >= 2:
            path = task.get_path()
            if path:
                self._display.display(u"task path: %s" % path, color=C.COLOR_DEBUG)

        self._last_task_banner = task._uuid

    def v2_runner_on_ok(self, result):
        self._progress[result._task._uuid] = True
        
        if self._play.strategy == 'free' and self._last_task_banner != result._task._uuid:
            self._print_task_banner(result._task)

        self._clean_results(result._result, result._task.action)
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._clean_results(result._result, result._task.action)

        msg = u'\n     %s' % (result._host.get_name())
        if result._task.action in ('include', 'include_role'):
            return
        elif result._result.get('changed', False):
            color = C.COLOR_CHANGED
        else:
            color = C.COLOR_OK

        self._handle_warnings(result._result)

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            if (self._display.verbosity > 0 or '_ansible_verbose_always' in result._result) and not '_ansible_verbose_override' in result._result:
                msg += " => %s" % (self._dump_results(result._result),)
            self._display.display(msg, color=color)

    def v2_runner_item_on_ok(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        msg = "\n    "
        if result._task.action in ('include', 'include_role'):
            return
        elif result._result.get('changed', False):
            color = C.COLOR_CHANGED
        else:
            color = C.COLOR_OK

        if delegated_vars:
            msg += "[%s -> %s]" % (result._host.get_name(), delegated_vars['ansible_host'])
        else:
            msg += "%s" % result._host.get_name()

        msg += " => (item=%s)" % (self._get_item(result._result),)

        if (self._display.verbosity > 0 or '_ansible_verbose_always' in result._result) and not '_ansible_verbose_override' in result._result:
            msg += " => %s" % self._dump_results(result._result)
        self._display.display(msg, color=color)


    def v2_on_file_diff(self, result):
        if result._task.loop and 'results' in result._result:
            for res in result._result['results']:
                if 'diff' in res and res['diff'] and res.get('changed', False):
                    diff = self._get_diff(res['diff'])
                    if diff:
                        self._display.display(u"\n" + diff.strip())
        elif 'diff' in result._result and result._result['diff'] and result._result.get('changed', False):
            diff = self._get_diff(result._result['diff'])
            if diff:
                self._display.display(u"\n" + diff.strip())

    def v2_playbook_on_stats(self, stats):
        self._display.display("\nPLAY RECAP\n")
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            self._display.display(u"%s : %s %s %s %s\n" % (
                hostcolor(h, t),
                colorize(u'ok', t['ok'], C.COLOR_OK),
                colorize(u'changed', t['changed'], C.COLOR_CHANGED),
                colorize(u'unreachable', t['unreachable'], C.COLOR_UNREACHABLE),
                colorize(u'failed', t['failures'], C.COLOR_ERROR)),
                screen_only=True
            )
