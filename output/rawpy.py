#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Represents an EventObject as a string."""
import pprint

from plaso.lib import output


class Rawpy(output.FileLogOutputFormatter):
  """Prints out a "raw" interpretation of the EventObject."""
  # TODO: Revisit the name of this class, perhaps rename it to
  # something more closely similar to what it is doing now, as in
  # "native" or something else.

  def Start(self):
    """Set up the pretty printer."""
    self.printer = pprint.PrettyPrinter(indent=8)

  def Usage(self):
    """Return usage information."""
    return ('Returns a raw representation of the EventObject. Useful for'
            ' debugging.')

  def EventBody(self, evt):
    """String representation of an EventObject object.

    Args:
      evt: The EventObject.

    Returns:
      String representation of an EventObject.
    """

    out_write = []
    out_write.append('+-' * 80)
    # TODO: There is no difference made between a "regular" attribute and an
    # additional one. Perhaps look into the RESERVED_VARIABLES list and display
    # them differently than others? As in indent others?
    for attr_key in sorted(evt.GetAttributes()):
      out_write.append(u'{key}: {value}'.format(
          key=attr_key, value=self.printer.pformat(
              getattr(evt, attr_key, None))))
    out_write.append('')

    self.filehandle.write('\n'.join(out_write).encode('utf-8'))
