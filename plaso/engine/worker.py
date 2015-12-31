#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2012 The Plaso Project Authors.
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
"""The event extraction worker."""

import logging
import os
import pdb
import threading

from dfvfs.lib import definitions as dfvfs_definitions
from dfvfs.resolver import context
from dfvfs.resolver import resolver as path_spec_resolver

from plaso.engine import classifier
from plaso.lib import errors
from plaso.lib import queue
from plaso.lib import utils


class EventExtractionWorker(queue.PathSpecQueueConsumer):
  """Class that extracts events for files and directories.

  This class is designed to watch a queue for path specifications of files
  and directories (file entries) for which events need to be extracted.

  The event extraction worker needs to determine if a parser suitable
  for parsing a particular file is available. All extracted event objects
  are pushed on a storage queue for further processing.
  """

  def __init__(
      self, identifier, process_queue, storage_queue_producer, pre_obj,
      parsers, rpc_proxy=None):
    """Initializes the event extraction worker object.

    Args:
      identifier: A thread identifier, usually an incrementing integer.
      process_queue: the process queue (instance of Queue).
      storage_queue_producer: the storage queue producer (instance of
                              EventObjectQueueProducer).
      pre_obj: A preprocess object containing information collected from
               image (instance of PreprocessObject).
      parsers: A list of parser objects to use for processing.
      rpc_proxy: A proxy object (instance of proxy.ProxyServer) that can be
                 used to setup RPC functionality for the worker. This is
                 optional and if not provided the worker will not listen to RPC
                 requests. The default value is None.
    """
    super(EventExtractionWorker, self).__init__(process_queue)
    self._debug_mode = False
    self._filter_object = None
    self._identifier = identifier
    self._mount_path = None
    self._open_files = False
    self._parsers = parsers
    self._pre_obj = pre_obj
    self._rpc_proxy = rpc_proxy

    # We need a resolver context per process to prevent multi processing
    # issues with file objects stored in images.
    self._resolver_context = context.Context()
    self._single_process_mode = False
    self._storage_queue_producer = storage_queue_producer
    self._text_prepend = None

    # Few attributes that contain the current status of the worker.
    self._counter_of_extracted_events = 0
    self._current_working_file = u''
    self._is_running = False

    if pre_obj:
      self._user_mapping = pre_obj.GetUserMappings()
    else:
      self._user_mapping = {}

  def _ConsumePathSpec(self, path_spec):
    """Consumes a path specification callback for ConsumePathSpecs."""
    file_entry = path_spec_resolver.Resolver.OpenFileEntry(
        path_spec, resolver_context=self._resolver_context)

    if file_entry is None:
      logging.warning(u'Unable to open file entry: {0:s}'.format(
          path_spec.comparable))
      return

    try:
      self.ParseFile(file_entry)
    except IOError as exception:
      logging.warning(u'Unable to parse file: {0:s} with error: {1:s}'.format(
          path_spec.comparable, exception))

    if self._open_files:
      try:
        for sub_file_entry in classifier.Classifier.SmartOpenFiles(file_entry):
          self.ParseFile(sub_file_entry)
      except IOError as exception:
        logging.warning(
            u'Unable to parse file: {0:s} with error: {1:s}'.format(
                file_entry.path_spec.comparable, exception))

  def _ParseEvent(self, event_object, file_entry, parser_name, stat_obj):
    """Adjust value of an extracted EventObject before storing it."""
    # TODO: Make some more adjustments to the event object.
    # Need to apply time skew, and other information extracted from
    # the configuration of the tool.

    # TODO: deperecate text_prepend in favor of an event tag.
    if self._text_prepend:
      event_object.text_prepend = self._text_prepend

    file_path = getattr(file_entry.path_spec, 'location', file_entry.name)
    # If we are parsing a mount point we don't want to include the full
    # path to file's location here, we are only interested in the relative
    # path to the mount point.

    # TODO: Solve this differently, quite possibly inside dfVFS using mount
    # path spec.
    type_indicator = file_entry.path_spec.type_indicator
    if (type_indicator == dfvfs_definitions.TYPE_INDICATOR_OS and
        self._mount_path):
      if self._mount_path:
        _, _, file_path = file_path.partition(self._mount_path)

    # TODO: dfVFS refactor: move display name to output since the path
    # specification contains the full information.
    event_object.display_name = u'{0:s}:{1:s}'.format(
        file_entry.path_spec.type_indicator, file_path)

    if not getattr(event_object, 'filename', None):
      event_object.filename = file_path
    event_object.pathspec = file_entry.path_spec
    event_object.parser = parser_name

    if hasattr(self._pre_obj, 'hostname'):
      event_object.hostname = self._pre_obj.hostname
    if not hasattr(event_object, 'inode') and hasattr(stat_obj, 'ino'):
      event_object.inode = utils.GetInodeValue(stat_obj.ino)

    # Set the username that is associated to the record.
    if getattr(event_object, 'user_sid', None) and self._user_mapping:
      username = self._user_mapping.get(event_object.user_sid, None)
      if username:
        event_object.username = username

    if not self._filter_object or self._filter_object.Matches(event_object):
      self._storage_queue_producer.ProduceEventObject(event_object)
      self._counter_of_extracted_events += 1

  def ParseFile(self, file_entry):
    """Run through classifier and appropriate parsers.

    Args:
      file_entry: A file entry object.
    """
    logging.debug(u'[ParseFile] Parsing: {0:s}'.format(
        file_entry.path_spec.comparable))

    self._current_working_file = getattr(
        file_entry.path_spec, u'location', file_entry.name)

    # TODO: Not go through all parsers, just the ones
    # that the classifier classifies the file as.
    # Do this when classifier is ready.
    # The classifier will return a "type" back, which refers
    # to a key in the self._parsers dict. If the results are
    # inconclusive the "all" key is used, or the key is not found.
    # key = self._parsers.get(classification, 'all')
    stat_obj = file_entry.GetStat()
    for parsing_object in self._parsers['all']:
      logging.debug(u'Checking [{0:s}] against: {1:s}'.format(
          file_entry.name, parsing_object.parser_name))
      try:
        for event_object in parsing_object.Parse(file_entry):
          if not event_object:
            continue

          self._ParseEvent(
              event_object, file_entry, parsing_object.parser_name, stat_obj)

      except errors.UnableToParseFile as exception:
        logging.debug(u'Not a {0:s} file ({1:s}) - {2:s}'.format(
            parsing_object.parser_name, file_entry.name, exception))

      except IOError as exception:
        logging.debug(
            u'[{0:s}] Unable to parse: {1:s} with error: {2:s}'.format(
                parsing_object.parser_name, file_entry.path_spec.comparable,
                exception))

      # Casting a wide net, catching all exceptions. Done to keep the worker
      # running, despite the parser hitting errors, so the worker doesn't die
      # if a single file is corrupted or there is a bug in a parser.
      except Exception as exception:
        logging.warning(
            u'[{0:s}] Unable to process file: {1:s} with error: {2:s}.'.format(
                parsing_object.parser_name, file_entry.path_spec.comparable,
                exception))
        logging.debug(
            u'The path specification that caused the error: {0:s}'.format(
                file_entry.path_spec.comparable))
        logging.exception(exception)

        # Check for debug mode and single process mode, then we would like
        # to debug this problem.
        if self._single_process_mode and self._debug_mode:
          pdb.post_mortem()

    logging.debug(u'Done parsing: {0:s}'.format(
        file_entry.path_spec.comparable))

  def GetStatus(self):
    """Returns a status dictionary for the worker process."""
    return {
        'is_running': self._is_running,
        'identifier': u'Worker_{0:d}'.format(self._identifier),
        'current_file': self._current_working_file,
        'counter': self._counter_of_extracted_events}

  def Run(self):
    """Start the worker, monitor the queue and parse files."""
    self.pid = os.getpid()
    logging.info(
        u'Worker {0:d} (PID: {1:d}) started monitoring process queue.'.format(
        self._identifier, self.pid))

    self._counter_of_extracted_events = 0
    self._is_running = True

    if self._rpc_proxy:
      try:
        self._rpc_proxy.SetListeningPort(self.pid)
        self._rpc_proxy.Open()
        self._rpc_proxy.RegisterFunction('status', self.GetStatus)

        proxy_thread = threading.Thread(
            name='rpc_proxy', target=self._rpc_proxy.StartProxy)
        proxy_thread.start()
      except errors.ProxyFailedToStart as exception:
        logging.error(
            u'Unable to setup a RPC server for the worker: {0:d} [PID {1:d}] '
            u'with error: {2:s}'.format(self._identifier, self.pid, exception))

    self.ConsumePathSpecs()

    logging.info(
        u'Worker {0:d} (PID: {1:d}) stopped monitoring process queue.'.format(
        self._identifier, os.getpid()))

    self._is_running = False
    self._current_working_file = u''

    self._resolver_context.Empty()

    if self._rpc_proxy:
      # Close the proxy, free up resources so we can shut down the thread.
      self._rpc_proxy.Close()

      if proxy_thread.isAlive():
        proxy_thread.join()

  def SetDebugMode(self, debug_mode):
    """Sets the debug mode.

    Args:
      debug_mode: boolean value to indicate if the debug mode should
                  be enabled.
    """
    self._debug_mode = debug_mode

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

  # TODO: rename this mode.
  def SetOpenFiles(self, open_files):
    """Sets the open files mode.

    Args:
      file_files: boolean value to indicate if the worker should scan for
                  sun file entries inside files.
    """
    self._open_files = open_files

  def SetSingleProcessMode(self, single_process_mode):
    """Sets the single process mode.

    Args:
      single_process_mode: boolean value to indicate if the single process mode
                          should be enabled.
    """
    self._single_process_mode = single_process_mode

  def SetTextPrepend(self, text_prepend):
    """Sets the text prepend.

    Args:
      text_prepend: string that contains the text to prepend to every
                    event object.
    """
    self._text_prepend = text_prepend
