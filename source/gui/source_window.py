# source_window.py, source edit window for the QT Lab environment
# Reinier Heeres <reinier@heeres.eu>, 2008
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import gobject
import qt

import os
import tempfile
import time

try:
    import gtksourceview2
    _have_gtksourceview = True
except:
    _have_gtksourceview = False

import pango

from gettext import gettext as _L

import lib.gui as gui
from lib.gui.qtwindow import QTWindow

def get_python_filter():
    filter = gtk.FileFilter()
    filter.set_name(_L('Python files'))
    filter.add_pattern('*.py')
    return filter

class SourceWindow(QTWindow):

    def __init__(self):
        QTWindow.__init__(self, 'source', 'Source')

        self.connect("delete-event", self._delete_event_cb)

        self._find_string = ''
        self._find_ofs = 0

        menu = [
            {'name': _L('File'), 'submenu':
                [
                    {'name': _L('Open'),
                        'action': self._open_cb, 'accel': '<Control>o'},
                    {'name': _L('Save'),
                        'action': self._save_cb, 'accel': '<Control>s'},
                    {'name': _L('Save as'), 'action': self._save_as_cb},
                    {'name': _L('Run'),
                        'action': self._run_clicked_cb, 'accel': '<Control>r'}
                ]
            },
            {'name': _L('Edit'), 'submenu':
                [
                    {'name': _L('Find'),
                        'action': self._find_cb, 'accel': '<Control>f'},
                    {'name': _L('Find next'),
                        'action': self._find_next_cb, 'accel': '<Control>n'},
                    {'name': _L('Find previous'),
                        'action': self._find_prev_cb, 'accel': '<Control>p'},
                ]
            }
        ]

        self._accel_group = gtk.AccelGroup()
        self.add_accel_group(self._accel_group)
        self._menu = gui.build_menu(menu, accelgroup=self._accel_group)

        self._name = gtk.Entry()
        self._run_button = gtk.Button(_L('Run'))
        self._run_button.connect('clicked', self._run_clicked_cb)

        self._options = gui.pack_hbox([
            gtk.Label(_L('Name')),
            self._name,
            self._run_button
            ])

        self.setup_source_view()

        self._vbox = gtk.VBox()
        self._vbox.pack_start(self._menu, False, False)
        self._vbox.pack_start(self._options, False, False)
        self._vbox.pack_start(self._source_win)
        self.add(self._vbox)

        self._vbox.show_all()

    def setup_source_view(self):
        self._buffer = gtksourceview2.Buffer()
        lang_manager = gtksourceview2.language_manager_get_default()
        if 'python' in lang_manager.get_language_ids():
            lang = lang_manager.get_language('python')
            self._buffer.set_language(lang)

        self._source_view = gtksourceview2.View(self._buffer)
        self._source_view.set_editable(True)
        self._source_view.set_cursor_visible(True)
        self._source_view.set_show_line_numbers(True)
        self._source_view.set_wrap_mode(gtk.WRAP_CHAR)
        self._source_view.modify_font(pango.FontDescription("Monospace 10"))

        self._source_win = gtk.ScrolledWindow()
        self._source_win.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._source_win.add(self._source_view)

        self._find_tag = self._buffer.create_tag('find')
        self._find_tag.props.background = 'gray'
        self._find_tag.props.foreground = 'yellow'

    def _delete_event_cb(self, widget, event, data=None):
        self.hide()
        return True

    def _save_cb(self, sender):
        self.save_file()

    def _save_as_cb(self, sender):
        chooser = gtk.FileChooserDialog(
            _L('Save as'), None,
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_SAVE, gtk.RESPONSE_OK))

        chooser.add_filter(get_python_filter())

        result = chooser.run()
        if result == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
            self.save_file(filename)

        chooser.destroy()

    def _open_cb(self, sender):
        chooser = gtk.FileChooserDialog(
            _L('Select file'), None,
            action=gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        chooser.add_filter(get_python_filter())

        result = chooser.run()
        if result == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
            self.load_file(filename)

        chooser.destroy()

    def load_file(self, filename):
        self._filename = filename

        f = open(filename)
        data = f.read()
        f.close()

        self._buffer.set_text(data)

    def save_file(self, filename=None):
        if filename is None:
            filename = self._filename

        if not os.path.exists(filename):
            self._filename = filename

            f = open(filename, 'w+')
            start, end = self._buffer.get_bounds()
            f.write(self._buffer.get_text(start, end))
            f.close()
        else:
            print 'File exists already, not overwritten'

    def _highlight_result(self, startofs, endofs):
        start = self._buffer.get_iter_at_offset(startofs)
        end = self._buffer.get_iter_at_offset(endofs)
        self._buffer.apply_tag(self._find_tag, start, end)
        self._source_view.scroll_to_iter(start, 0.25)

    def _prepare_find(self):
        start, end = self._buffer.get_bounds()
        self._buffer.remove_tag(self._find_tag, start, end)
        buftext = self._buffer.get_text(start, end)
        return buftext

    def _do_find(self, text, backward=False):
        buftext = self._prepare_find()
        ofs = self._buffer.props.cursor_position
        self._find_string = text

        if backward:
            ofs = buftext.rfind(self._find_string, 0, ofs)
        else:
            ofs = buftext.find(self._find_string, ofs)

        if ofs != -1:
            self._highlight_result(ofs, ofs + len(text))
            self._find_ofs = ofs

    def _do_find_next(self):
        if len(self._find_string) == 0:
            return

        buftext = self._prepare_find()
        ofs = buftext.find(self._find_string, self._find_ofs + 1)

        if ofs != -1:
            self._highlight_result(ofs, ofs + len(self._find_string))
            self._find_ofs = ofs
        else:
            self._find_ofs = 0

    def _do_find_prev(self):
        if len(self._find_string) == 0:
            return

        buftext = self._prepare_find()
        ofs = buftext.rfind(self._find_string, 0, self._find_ofs - 1)

        if ofs != -1:
            self._highlight_result(ofs, ofs + len(self._find_string))
            self._find_ofs = ofs
        else:
            self._find_ofs = len(buftext)

    def _find_cb(self, sender):
        dialog = gtk.Dialog(title=_L('Find'), parent=self,
                            flags=gtk.DIALOG_MODAL,
                            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                            gtk.STOCK_OK, gtk.RESPONSE_OK))
        vbox = dialog.vbox
        entry = gtk.Entry()
        vbox.pack_start(entry, False, False)
        vbox.show_all()
        res = dialog.run()
        if res == gtk.RESPONSE_OK:
            text = entry.get_text()
            self._do_find(text)

        dialog.destroy()

    def _find_next_cb(self, sender):
        self._do_find_next()

    def _find_prev_cb(self, sender):
        self._do_find_prev()

    def _run_clicked_cb(self, sender):
        fn = os.path.join(tempfile.gettempdir(), '%i.py' % time.time())
        f = open(fn, 'w+')
        start, end = self._buffer.get_bounds()
        f.write(self._buffer.get_text(start, end))
        f.close()

        qtrun_thread(fn)

#        os.remove(fn)

