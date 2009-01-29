# Copyright (c) 2008, Pablo Flouret <quuxbaz@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met: Redistributions of
# source code must retain the above copyright notice, this list of conditions and
# the following disclaimer. Redistributions in binary form must reproduce the
# above copyright notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
# Neither the name of the software nor the names of its contributors may be
# used to endorse or promote products derived from this software without specific
# prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import urwid

import keys

BADROWSMSG = "Widget %s at position %s within listbox calculated %d rows but rendered %d!"
BADFOCUSROWSMSG = "Focus widget %s at position %s within listbox " \
                  "calculated %d rows but rendered %d!"
BADCURSORMSG = "Focus Widget %s at position %s within listbox calculated cursor " \
               "coords %s but rendered cursor coords %s!"

class AttrListBox(urwid.ListBox):
  """A listbox with rows that can have attributes."""

  def __init__(self, body, attr=None, focus_attr=None, focus_str=None, row_attrs=None):
    self.__super.__init__(body)

    self.attr = attr
    self.focus_attr = focus_attr
    self.focus_str = focus_str
    self.row_attrs = row_attrs is not None and row_attrs or {}

  def get_row_attr(self, pos):
    # TODO: make better choice on which attr to apply (priority? merge func?)
    return self.row_attrs.get(pos, [self.attr])[-1]

  def set_row_attr(self, pos, attr, priority=0):
    self.row_attrs[pos] = [attr]

  def add_row_attr(self, pos, attr, priority=0):
    self.row_attrs.setdefault(pos, []).append(attr)

  def remove_row_attr(self, pos, attr):
    try:
      self.row_attrs[pos].remove(attr)
      if not self.row_attrs[pos]:
        del self.row_attrs[pos]
    except (KeyError, ValueError):
      pass

  def render(self, size, focus=False ):
    """Render listbox and return canvas. """
    (maxcol, maxrow) = size

    middle, top, bottom = self.calculate_visible((maxcol, maxrow), focus=focus)

    if middle is None:
      return urwid.SolidCanvas(" ", maxcol, maxrow)
    
    _ignore, focus_widget, focus_pos, focus_rows, cursor = middle
    trim_top, fill_above = top
    trim_bottom, fill_below = bottom

    combinelist = []
    rows = 0
    fill_above.reverse() # fill_above is in bottom-up order

    for widget,w_pos,w_rows in fill_above:
      canvas = widget.render((maxcol,))
      attr = self.get_row_attr(w_pos)
      if attr:
        canvas = urwid.CompositeCanvas(canvas)
        canvas.fill_attr(attr)
      if w_rows != canvas.rows():
        raise urwid.ListBoxError, BADROWSMSG % (`widget`,`w_pos`,w_rows, canvas.rows())
      rows += w_rows
      combinelist.append((canvas, w_pos, False))
    
    focus_canvas = focus_widget.render((maxcol,), focus=focus)

    focus_attr = None
    if focus_pos in self.row_attrs:
      focus_attr = self.get_row_attr(focus_pos)
      if focus and self.focus_str:
        focus_attr += self.focus_str
    elif focus:
      focus_attr = self.focus_attr

    if focus_attr:
      focus_canvas = urwid.CompositeCanvas(focus_canvas)
      focus_canvas.fill_attr(focus_attr)

    if focus_canvas.rows() != focus_rows:
      raise ListBoxError, BADFOCUSROWSMSG % (`focus_widget`, `focus_pos`,
                                             focus_rows, focus_canvas.rows())
    c_cursor = focus_canvas.cursor
    if cursor != c_cursor:
      raise urwid.ListBoxError, BADCURSORMSG % (`focus_widget`,`focus_pos`,`cursor`,`c_cursor`)
      
    rows += focus_rows
    combinelist.append((focus_canvas, focus_pos, True))
    
    for widget,w_pos,w_rows in fill_below:
      canvas = widget.render((maxcol,))
      attr = self.get_row_attr(w_pos)
      if attr:
        canvas = urwid.CompositeCanvas(canvas)
        canvas.fill_attr(attr)
      if w_rows != canvas.rows():
        raise urwid.ListBoxError, BADROWSMSG  % (`widget`,`w_pos`,w_rows, canvas.rows())
      rows += w_rows
      combinelist.append((canvas, w_pos, False))
    
    final_canvas = urwid.CanvasCombine(combinelist)
    
    if trim_top:	
      final_canvas.trim(trim_top)
      rows -= trim_top
    if trim_bottom:	
      final_canvas.trim_end(trim_bottom)
      rows -= trim_bottom
    
    assert rows <= maxrow
    
    if rows < maxrow:
      bottom_pos = focus_pos
      if fill_below:
        bottom_pos = fill_below[-1][1]
      assert trim_bottom==0 and self.body.get_next(bottom_pos) == (None,None)
      final_canvas.pad_trim_top_bottom(0, maxrow - rows)

    return final_canvas

  def keypress(self, size, keys):
    return self.__super.keypress(size, keys)

class MarkableListBox(AttrListBox):
  def __init__(self, body, ch=None):
    self._marked_data = {}

    if ch:
      ch.register_command(self, 'move-focus-top', lambda c, a: self.set_focus(0)),
      ch.register_command(self, 'move-focus-bottom', lambda c, a: self.set_focus_last()),
      ch.register_command(self, 'mark-and-move-up', lambda c, a: self._mark_and_move_rel(-1)),
      ch.register_command(self, 'mark-and-move-down', lambda c, a: self._mark_and_move_rel(1)),
      ch.register_command(self, 'unmark-all', lambda c, a: self.unmark_all())

      ch.register_keys(self, 'move-focus-top', keys.bindings['movement']['move-focus-top'])
      ch.register_keys(self, 'move-focus-bottom', keys.bindings['movement']['move-focus-bottom'])
      ch.register_keys(self, 'mark-and-move-up', keys.bindings['general']['mark-and-move-up'])
      ch.register_keys(self, 'mark-and-move-down', keys.bindings['general']['mark-and-move-down'])
      ch.register_keys(self, 'unmark-all', keys.bindings['general']['unmark-all'])

    self.__super.__init__(body, attr='default', focus_attr='focus', focus_str='-focus')

  marked_data = property(lambda self: self._marked_data)

  def get_mark_data(self, pos, w):
    return pos

  def set_focus_last(self):
    # FIXME: don't do anything here, let subclasses override
    if hasattr(self.body, 'set_focus_last'):
      self.body.set_focus_last()

  def toggle_focus_mark(self):
    w, pos = self.get_focus()

    if pos is not None:
      self.toggle_mark(pos, self.get_mark_data(pos, w))

  def toggle_mark(self, pos, data):
    if pos >= 0 and pos < len(self.body):
      if pos in self._marked_data:
        del self._marked_data[pos]
        self.remove_row_attr(pos, 'marked')
      else:
        self._marked_data[pos] = data
        self.add_row_attr(pos, 'marked')

  def unmark_all(self):
    self._marked_data.clear()
    for pos in self.row_attrs.keys():
      self.remove_row_attr(pos, 'marked')

  def _mark_and_move_rel(self, delta):
    w, pos = self.get_focus()
    if pos is not None:
      self.toggle_focus_mark()
      self.set_focus(pos+delta)


