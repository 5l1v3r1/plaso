#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2014 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.
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
"""The parser context object."""

import os

from dfvfs.lib import definitions as dfvfs_definitions

from plaso.lib import utils


class ParserContext(object):
  """Class that implements the parser context."""

  def __init__(self, event_queue_producer, knowledge_base):
    """Initializes a parser context object.

    Args:
      event_queue_producer: the event object producer (instance of
                            EventObjectQueueProducer).
      knowledge_base: A knowledge base object (instance of KnowledgeBase),
                      which contains information from the source data needed
                      for parsing.
    """
    super(ParserContext, self).__init__()
    self._event_queue_producer = event_queue_producer
    self._filter_object = None
    self._knowledge_base = knowledge_base
    self._mount_path = None
    self._text_prepend = None

    self.number_of_produced_events = 0

  @property
  def codepage(self):
    """The codepage."""
    return self._knowledge_base.codepage

  @property
  def hostname(self):
    """The hostname."""
    return self._knowledge_base.hostname

  @property
  def knowledge_base(self):
    """The knowledge base."""
    return self._knowledge_base

  @property
  def platform(self):
    """The platform."""
    return self._knowledge_base.platform

  @property
  def timezone(self):
    """The timezone object."""
    return self._knowledge_base.timezone

  @property
  def year(self):
    """The year."""
    return self._knowledge_base.year

  def GetDisplayName(self, file_entry):
    """Retrieves the display name for the file entry.

    Args:
      file_entry: a file entry object (instance of dfvfs.FileEntry).

    Returns:
      A string containing the display name.
    """
    relative_path = self.GetRelativePath(file_entry)
    if not relative_path:
      return file_entry.name

    return u'{0:s}:{1:s}'.format(
        file_entry.path_spec.type_indicator, relative_path)

  def GetRelativePath(self, file_entry):
    """Retrieves the relative path of the file entry.

    Args:
      file_entry: a file entry object (instance of dfvfs.FileEntry).

    Returns:
      A string containing the relative path or None.
    """
    path_spec = getattr(file_entry, 'path_spec', None)
    if not path_spec:
      return

    # TODO: Solve this differently, quite possibly inside dfVFS using mount
    # path spec.
    file_path = getattr(path_spec, 'location', None)

    if path_spec.type_indicator != dfvfs_definitions.TYPE_INDICATOR_OS:
      return file_path

    # If we are parsing a mount point we don't want to include the full
    # path to file's location here, we are only interested in the relative
    # path to the mount point.
    if self._mount_path:
      _, _, file_path = file_path.partition(self._mount_path)

    return file_path

  def MatchesFilter(self, event_object):
    """Checks if the event object matces the filter.

    Args:
      event_object: the event object (instance of EventObject).

    Returns:
      A boolean value indicating if the event object matches the filter.
    """
    return self._filter_object and self._filter_object.Matches(event_object)

  def ProcessEvent(self, name, event_object, file_entry=None):
    """Processes an event before it is emitted to the event queue.

    Args:
      name: the name of the parser or plugin.
      event_object: the event object (instance of EventObject).
      file_entry: optional file entry object (instance of dfvfs.FileEntry).
                  The default is None.
    """
    if not getattr(event_object, 'parser', None) and name:
      event_object.parser = name

    # TODO: deperecate text_prepend in favor of an event tag.
    if not getattr(event_object, 'text_prepend', None) and self._text_prepend:
      event_object.text_prepend = self._text_prepend

    display_name = None
    if file_entry:
      event_object.pathspec = file_entry.path_spec

      if not getattr(event_object, 'filename', None):
        event_object.filename = self.GetRelativePath(file_entry)

      if not display_name:
        # TODO: dfVFS refactor: move display name to output since the path
        # specification contains the full information.
        display_name = self.GetDisplayName(file_entry)

      stat_object = file_entry.GetStat()
      inode_number = getattr(stat_object, 'ino', None)
      if not hasattr(event_object, 'inode') and inode_number:
        # TODO: clean up the GetInodeValue function.
        event_object.inode = utils.GetInodeValue(inode_number)

    if not getattr(event_object, 'display_name', None) and display_name:
      event_object.display_name = display_name

    if not getattr(event_object, 'hostname', None) and self.hostname:
      event_object.hostname = self.hostname

    if not getattr(event_object, 'username', None):
      user_sid = getattr(event_object, 'user_sid', None)
      username = self._knowledge_base.GetUsernameByIdentifier(user_sid)
      if username:
        event_object.username = username

  def ProduceEvent(self, name, event_object, file_entry=None):
    """Produces an event onto the event queue.

    Args:
      name: the name of the parser or plugin.
      event_object: the event object (instance of EventObject).
      file_entry: optional file entry object (instance of dfvfs.FileEntry).
                  The default is None.
    """
    self.ProcessEvent(name, event_object, file_entry=file_entry)

    if self.MatchesFilter(event_object):
      return

    self._event_queue_producer.ProduceEventObject(event_object)
    self.number_of_produced_events += 1

  def ProduceEvents(self, name, event_objects, file_entry=None):
    """Produces events onto the event queue.

    Args:
      name: the name of the parser or plugin.
      event_objects: a list or generator of event objects (instances of
                     EventObject).
      file_entry: optional file entry object (instance of dfvfs.FileEntry).
                  The default is None.
    """
    for event_object in event_objects:
      self.ProduceEvent(name, event_object, file_entry=file_entry)

  def SetFilterObject(self, filter_object):
    """Sets the filter object.

    Args:
      filter_object: the filter object (instance of objectfilter.Filter).
    """
    self._filter_object = filter_object

  def SetMountPath(self, mount_path):
    """Sets the mount path.

    Args:
      mount_path: string containing the mount path.
    """
    # Remove a trailing path separator from the mount path so the relative
    # paths will start with a path separator.
    if mount_path and mount_path.endswith(os.sep):
      mount_path = mount_path[:-1]

    self._mount_path = mount_path

  def SetTextPrepend(self, text_prepend):
    """Sets the text prepend.

    Args:
      text_prepend: string that contains the text to prepend to every event.
    """
    self._text_prepend = text_prepend
