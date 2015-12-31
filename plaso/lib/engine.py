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
"""The processing engine."""

import abc
import logging
import sys

from dfvfs.helpers import file_system_searcher
from dfvfs.lib import definitions as dfvfs_definitions
from dfvfs.resolver import resolver as path_spec_resolver

from plaso import preprocessors
from plaso.collector import collector
from plaso.lib import errors
from plaso.lib import queue
from plaso.lib import worker
from plaso.preprocessors import interface as preprocess_interface


class EngineInputReader(object):
  """Class that implements the input reader interface for the engine."""

  @abc.abstractmethod
  def Read(self):
    """Reads a string from the input.

    Returns:
      A string containing the input.
    """


class EngineOutputWriter(object):
  """Class that implements the output writer interface for the engine."""

  @abc.abstractmethod
  def Write(self, string):
    """Wtites a string to the output.

    Args:
      string: A string containing the output.
    """


class StdinEngineInputReader(object):
  """Class that implements a stdin input reader."""

  def Read(self):
    """Reads a string from the input.

    Returns:
      A string containing the input.
    """
    return sys.stdin.readline()


class StdoutEngineOutputWriter(object):
  """Class that implements a stdout output writer."""

  def Write(self, string):
    """Wtites a string to the output.

    Args:
      string: A string containing the output.
    """
    sys.stdout.write(string)


class Engine(object):
  """Class that defines the processing engine."""

  def __init__(
      self, collection_queue, storage_queue, resolver_context=None):
    """Initialize the engine object.

    Args:
      collection_queue: the collection queue object (instance of Queue).
      storage_queue: the storage queue object (instance of Queue).
      resolver_context: Optional resolver context (instance of dfvfs.Context).
                        The default is None.
    """
    self._collection_queue = collection_queue
    self._resolver_context = resolver_context
    self._source = None
    self._source_path_spec = None
    self._source_file_entry = None
    self._storage_queue_producer = queue.EventObjectQueueProducer(storage_queue)

  def CreateCollector(
      self, include_directory_stat, vss_stores, filter_find_specs):
    """Creates a collector.

    Args:
      include_directory_stat: Boolean value to indicate whether directory
                              stat information should be collected.
      vss_stores: The range of VSS stores to include in the collection,
                  where 1 represents the first store. Set to None if no
                  VSS stores should be processed.
      filter_find_specs: List of filter find specifications (instances of
                         dfvfs.FindSpec).

    Raises:
      RuntimeError: if source path specification is not set.
    """
    if not self._source_path_spec:
      raise RuntimeError(u'Missing source.')

    collector_object = collector.Collector(
        self._collection_queue, self._storage_queue_producer, self._source,
        self._source_path_spec, resolver_context=self._resolver_context)

    collector_object.collect_directory_metadata = include_directory_stat

    if vss_stores:
      collector_object.SetVssInformation(vss_stores)

    if filter_find_specs:
      collector_object.SetFilter(filter_find_specs)

    return collector_object

  def CreateExtractionWorker(self, worker_number, pre_obj, parsers):
    """Creates an extraction worker object.

    Args:
      worker_number: number that identifies the worker.
      pre_obj: The preprocessing object (instance of PreprocessObject).
      parsers: A list of parser objects to use for processing.

    Returns:
      An extraction worker (instance of worker.ExtractionWorker).
    """
    return worker.EventExtractionWorker(
        worker_number, self._collection_queue, self._storage_queue_producer,
        pre_obj, parsers)

  def GetSourceFileSystemSearcher(self):
    """Retrieves the file system searcher of the source.

    Returns:
      The file system searcher object (instance of dfvfs.FileSystemSearcher).

    Raises:
      RuntimeError: if source path specification is not set.
    """
    if not self._source_path_spec:
      raise RuntimeError(u'Missing source.')

    file_system = path_spec_resolver.Resolver.OpenFileSystem(
        self._source_path_spec, resolver_context=self._resolver_context)

    type_indicator = self._source_path_spec.type_indicator
    if type_indicator == dfvfs_definitions.TYPE_INDICATOR_OS:
      mount_point = self._source_path_spec
    else:
      mount_point = self._source_path_spec.parent

    return file_system_searcher.FileSystemSearcher(file_system, mount_point)

  def PreprocessSource(self, pre_obj, platform):
    """Preprocesses the source and fills the preprocessing object.

    Args:
      pre_obj: the preprocessing object (instance of PreprocessObject).
      platform: string that indicates the platform (operating system).
    """
    searcher = self.GetSourceFileSystemSearcher()
    if not platform:
      platform = preprocess_interface.GuessOS(searcher)
    pre_obj.guessed_os = platform

    plugin_list = preprocessors.PreProcessList(pre_obj)

    for weight in plugin_list.GetWeightList(platform):
      for plugin in plugin_list.GetWeight(platform, weight):
        try:
          plugin.Run(searcher)
        except (IOError, errors.PreProcessFail) as exception:
          logging.warning((
              u'Unable to run preprocessor: {0:s} for attribute: {1:s} '
              u'with error: {2:s}').format(
                  plugin.plugin_name, plugin.ATTRIBUTE, exception))

  def SetSource(self, source_path_spec):
    """Sets the source.

    Args:
      source_path_spec: The source path specification (instance of
                        dfvfs.PathSpec) as determined by the file system
                        scanner. The default is None.
    """
    path_spec = source_path_spec
    while path_spec.parent:
      path_spec = path_spec.parent

    # Note that source should be used for output purposes only.
    self._source = getattr(path_spec, 'location', u'')
    self._source_path_spec = source_path_spec

    self._source_file_entry = path_spec_resolver.Resolver.OpenFileEntry(
       self._source_path_spec, resolver_context=self._resolver_context)

    if not self._source_file_entry:
      raise errors.BadConfigOption(
          u'No such device, file or directory: {0:s}.'.format(self._source))

    if (not self._source_file_entry.IsDirectory() and
        not self._source_file_entry.IsFile() and
        not self._source_file_entry.IsDevice()):
      raise errors.CollectorError(
          u'Source path: {0:s} not a device, file or directory.'.format(
              self._source))

    if self._source_path_spec.type_indicator in [
        dfvfs_definitions.TYPE_INDICATOR_OS,
        dfvfs_definitions.TYPE_INDICATOR_FAKE]:

      if self._source_file_entry.IsFile():
        logging.debug(u'Starting a collection on a single file.')
        # No need for multiple workers when parsing a single file.

      elif not self._source_file_entry.IsDirectory():
        raise errors.BadConfigOption(
            u'Source: {0:s} has to be a file or directory.'.format(
                self._source))

  def SignalEndOfInputStorageQueue(self):
    """Signals the storage queue no input remains."""
    self._storage_queue_producer.SignalEndOfInput()

  def SourceIsDirectory(self):
    """Determines if the source is a directory.

    Raises:
      RuntimeError: if source path specification is not set.
    """
    if not self._source_file_entry:
      raise RuntimeError(u'Missing source.')

    return (not self.SourceIsStorageMediaImage() and
            self._source_file_entry.IsDirectory())

  def SourceIsFile(self):
    """Determines if the source is a file.

    Raises:
      RuntimeError: if source path specification is not set.
    """
    if not self._source_file_entry:
      raise RuntimeError(u'Missing source.')

    return (not self.SourceIsStorageMediaImage() and
            self._source_file_entry.IsFile())

  def SourceIsStorageMediaImage(self):
    """Determines if the source is storage media image file or device.

    Raises:
      RuntimeError: if source path specification is not set.
    """
    if not self._source_path_spec:
      raise RuntimeError(u'Missing source.')

    return self._source_path_spec.type_indicator not in [
        dfvfs_definitions.TYPE_INDICATOR_OS,
        dfvfs_definitions.TYPE_INDICATOR_FAKE]
