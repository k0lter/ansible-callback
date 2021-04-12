# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    callback: condensed
    callback_type: stdout
    requirements:
      - set as main display callback
    short_description: Ansible screen output that ignores skipped status
    version_added: "2.0"
    deprecated:
        why: The 'default' callback plugin now supports this functionality
        removed_in: '2.11'
        alternative: "'default' callback plugin with 'display_skipped_hosts = no' option"
    extends_documentation_fragment:
      - default_callback
    description:
        - This callback does the same as the default except it does not output skipped host/task/item status
'''

from ansible.plugins.callback.default import CallbackModule as CallbackModule_default
from ansible.playbook.task_include import TaskInclude
from ansible.utils.display import Display
from ansible import constants as C

class CondensedDisplay(Display):

    def banner(self, msg, color=None, cows=True):
        '''
        Prints a header-looking line with cowsay or stars with length depending on terminal width (3 minimum)
        '''
        if self.b_cowsay and cows:
            try:
                self.banner_cowsay(msg)
                return
            except OSError:
                self.warning("somebody cleverly deleted cowsay or something during the PB run.  heh.")

        msg = msg.strip()
        self.display(u"%s" % (msg), color=color)

class CallbackModule(CallbackModule_default):

    '''
    This is the default callback interface, which simply prints messages
    to stdout when new callback events are received.
    '''

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'condensed'

    def __init__(self):
        super(CallbackModule, self).__init__()
        self._display = CondensedDisplay()

    def v2_playbook_on_include(self, included_file):
        basedir = included_file._task._loader.get_basedir()
        hosts = ", ".join([h.name for h in included_file._hosts])
        filepath = included_file._filename.replace(basedir, '').strip('/')
        msg = '    %s => %s' % (hosts, filepath)
        self._display.display('INCLUDE TASKS')
        self._display.display(msg, color=C.COLOR_SKIP)

    def v2_runner_on_ok(self, result):

        delegated_vars = result._result.get('_ansible_delegated_vars', None)

        if isinstance(result._task, TaskInclude):
            return
        elif result._result.get('changed', False):
            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)

            if delegated_vars:
                msg = "    %s -> %s" % (result._host.get_name(), delegated_vars['ansible_host'])
            else:
                msg = "    %s" % result._host.get_name()
            color = C.COLOR_CHANGED
        else:
            if not self.display_ok_hosts:
                return

            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)

            if delegated_vars:
                msg = "    %s -> %s" % (result._host.get_name(), delegated_vars['ansible_host'])
            else:
                msg = "    %s" % result._host.get_name()
            color = C.COLOR_OK

        self._handle_warnings(result._result)

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            self._clean_results(result._result, result._task.action)

            #if self._run_is_verbose(result):
            #    msg += " => %s" % (self._dump_results(result._result),)
            self._display.display(msg, color=color)

    def v2_runner_item_on_ok(self, result):

        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._clean_results(result._result, result._task.action)
        if isinstance(result._task, TaskInclude):
            return
        elif result._result.get('changed', False):
            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)

            color = C.COLOR_CHANGED
        else:
            if not self.display_ok_hosts:
                return

            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)

            color = C.COLOR_OK

        if delegated_vars:
            msg = "    %s -> %s" % (result._host.get_name(), delegated_vars['ansible_host'])
        else:
            msg = "    %s" % result._host.get_name()

        msg += " => (item=%s)" % (self._get_item_label(result._result),)

        #if self._run_is_verbose(result):
        #    msg += " => %s" % self._dump_results(result._result)
        self._display.display(msg, color=color)

    def v2_runner_on_skipped(self, result):
        pass

    def v2_runner_item_on_skipped(self, result):
        pass
