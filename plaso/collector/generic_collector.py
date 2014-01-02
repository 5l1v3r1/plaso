#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013 The Plaso Project Authors.
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
"""Generic collector that supports both file system and image files."""

import hashlib
import logging

from plaso.collector import interface
from plaso.collector import os_collector
from plaso.collector import tsk_collector
from plaso.lib import collector_filter
from plaso.lib import errors
from plaso.lib import event
from plaso.lib import storage_helper
from plaso.lib import utils
from plaso.parsers import filestat
from plaso.pvfs import pfile_entry
from plaso.pvfs import pvfs
from plaso.pvfs import vss


class GenericCollector(interface.PfileCollector):
  """Class that implements a generic pfile-based collector object."""

  _SECTOR_SIZE = 512

  def __init__(self, process_queue, output_queue, source_path):
    """Initializes the collector object.

       The collector discovers all the files that need to be processed by
       the workers. Once a file is discovered it added to the process queue
       as a path specification (instance of event.EventPathSpec).

    Args:
      proces_queue: The files processing queue (instance of
                    queue.QueueInterface).
      output_queue: The event output queue (instance of queue.QueueInterface).
                    This queue is used as a buffer to the storage layer.
      source_path: Path of the source file or directory.
    """
    super(GenericCollector, self).__init__(
        process_queue, output_queue, source_path)
    self._byte_offset = None
    self._fscache = None
    self._hashlist = None
    self._process_image = None
    self._process_vss = None
    self._sector_offset = None
    self._vss_stores = None

  def _CalculateNTFSTimeHash(self, file_entry):
    """Return a hash value calculated from a NTFS file's metadata.

    Args:
      file_entry: The file entry (instance of TSKFileEntry).

    Returns:
      A hash value (string) that can be used to determine if a file's timestamp
    value has changed.
    """
    stat_object = file_entry.Stat()

    ret_hash = hashlib.md5()

    ret_hash.update('atime:{0}.{1}'.format(
        getattr(stat_object, 'atime', 0),
        getattr(stat_object, 'atime_nano', 0)))

    ret_hash.update('crtime:{0}.{1}'.format(
        getattr(stat_object, 'crtime', 0),
        getattr(stat_object, 'crtime_nano', 0)))

    ret_hash.update('mtime:{0}.{1}'.format(
        getattr(stat_object, 'mtime', 0),
        getattr(stat_object, 'mtime_nano', 0)))

    ret_hash.update('ctime:{0}.{1}'.format(
        getattr(stat_object, 'ctime', 0),
        getattr(stat_object, 'ctime_nano', 0)))

    return ret_hash.hexdigest()

  def _CopyPathToPathSpec(
      self, path_spec_type, path, inode_number=None, store_number=None):
    """Copies the path to a path specification equivalent."""
    path_spec = event.EventPathSpec()
    path_spec.type = path_spec_type
    path_spec.file_path = utils.GetUnicodeString(path)

    if path_spec_type in ['TSK', 'VSS']:
      path_spec.container_path = self._source_path
      path_spec.image_offset = self._GetImageByteOffset()
      if inode_number is not None:
        path_spec.image_inode = inode_number

    if path_spec_type == 'VSS':
      if store_number is not None:
        path_spec.vss_store_number = store_number

    return path_spec

  def _GetImageByteOffset(self):
    """Retrieves the image offset in bytes."""
    if self._byte_offset is None:
      if self._sector_offset is not None:
        self._byte_offset = self._sector_offset * self._SECTOR_SIZE
      else:
        self._byte_offset = 0

    return self._byte_offset

  def _GetVssStores(self):
    """Returns a list of VSS stores that need to be processed."""
    image_offset = self._GetImageByteOffset()

    list_of_vss_stores = []
    if not self._process_vss:
      return list_of_vss_stores

    logging.debug(u'Searching for VSS')
    vss_numbers = vss.GetVssStoreCount(self._source_path, image_offset)
    if self._vss_stores:
      for nr in self._vss_stores:
        if nr > 0 and nr <= vss_numbers:
          list_of_vss_stores.append(nr)
    else:
      list_of_vss_stores = range(0, vss_numbers)

    return list_of_vss_stores

  def _ProcessDirectory(self, file_entry):
    """Processes a directory and extract its metadata if necessary."""
    # Need to do a breadth-first search otherwise we'll hit the Python
    # maximum recursion depth.
    sub_directories = []

    for sub_file_entry in file_entry.GetSubFileEntries():
      if isinstance(sub_file_entry, pfile_entry.TSKFileEntry):
        # Work-around the limitation in TSKFileEntry that it needs to be open
        # to return stat information. This will be fixed by PyVFS.
        try:
          _  = sub_file_entry.Open()
        except AttributeError as e:
          logging.error(
              u'Unable to read file: {0:s} from image with error: {1:s}'.format(
                  sub_file_entry.pathspec.file_path, e))
          continue

      if not sub_file_entry.IsAllocated() or sub_file_entry.IsLink():
        continue

      if isinstance(sub_file_entry, pfile_entry.TSKFileEntry):
        # For TSK-based file entries only, ignore the virtual /$OrphanFiles
        # directory.
        if sub_file_entry.pathspec.file_path == u'/$OrphanFiles':
          continue

      if sub_file_entry.IsDirectory():
        if self.collect_directory_metadata:
          # TODO: solve this differently by putting the path specification
          # on the queue and have the filestat parser just extract the metadata.
          # self._queue.Queue(sub_file_entry.pathspec.ToProtoString())
          stat_object = sub_file_entry.Stat()
          stat_object.full_path = sub_file_entry.pathspec.file_path

          if isinstance(sub_file_entry, pfile_entry.TSKFileEntry):
            stat_object.display_path = u'{0:s}:{1:s}'.format(
                self._source_path, sub_file_entry.pathspec.file_path)

            try:
              _ = stat_object.display_path.decode('utf-8')
            except UnicodeDecodeError:
              logging.warning(
                  u'UnicodeDecodeError: stat_object.display_path: {0:s}'.format(
                      stat_object.display_path))
              stat_object.display_path = utils.GetUnicodeString(
                  stat_object.display_path)
          else:
            stat_object.display_path = sub_file_entry.pathspec.file_path

          storage_helper.SendContainerToStorage(
              filestat.GetEventContainerFromStat(stat_object), stat_object,
              self._storage_queue)

        sub_directories.append(sub_file_entry)

      elif sub_file_entry.IsFile():
        # If we are dealing with a VSS we want to calculate a hash
        # value based on available timestamps and compare that to previously
        # calculated hash values, and only include the file into the queue if
        # the hash does not match.
        if self._process_vss:
          hash_value = self._CalculateNTFSTimeHash(sub_file_entry)

          if sub_file_entry.pathspec.image_inode in self._hashlist:
            if hash_value in self._hashlist[
                sub_file_entry.pathspec.image_inode]:
              continue

          self._hashlist.setdefault(
              sub_file_entry.pathspec.image_inode, []).append(hash_value)

        self._queue.Queue(sub_file_entry.pathspec.ToProtoString())

    for sub_file_entry in sub_directories:
      self._ProcessDirectory(sub_file_entry)

  def _ProcessFileSystemWithFilter(self):
    """Processes the source path based on the collection filter."""
    preprocessor_collector = os_collector.FileSystemPreprocessCollector(
        self._pre_obj, self._source_path)
    filter_object = collector_filter.CollectionFilter(
        preprocessor_collector, self._filter_file_path)

    for pathspec_string in filter_object.GetPathSpecs():
      self._queue.Queue(pathspec_string)

  def _ProcessImage(self):
    """Processes the image."""
    image_offset = self._GetImageByteOffset()
    logging.debug(
        u'Collecting from image file: {0:s}'.format(self._source_path))

    # Check if we will in the future collect from VSS.
    if self._process_vss:
      self._hashlist = {}

    # Read the root dir, and move from there.
    try:
      file_system_container = self._fscache.Open(
          self._source_path, byte_offset=image_offset)
      # TODO: why was os.path.sep passed here instead of / but not for the VSS?
      root_path_spec = self._CopyPathToPathSpec(
          'TSK', u'/', inode_number=file_system_container.fs.info.root_inum)
      # TODO: do we need to set root here?
      root_file_entry = pfile_entry.TSKFileEntry(
          root_path_spec, root=None, fscache=self._fscache)

      # Work-around the limitation in TSKFileEntry that it needs to be open
      # to return stat information. This will be fixed by PyVFS.
      try:
        _  = root_file_entry.Open()
      except AttributeError as e:
        logging.error((
            u'Unable to read root file entry from image with error: '
            u'{0:s}').format(e))

      self._ProcessDirectory(root_file_entry)

    except errors.UnableToOpenFilesystem as e:
      logging.error(u'Unable to read image with error {0:s}.'.format(e))
      return

    vss_numbers = 0
    if self._process_vss:
      logging.info(u'Collecting from VSS.')
      vss_numbers = vss.GetVssStoreCount(self._source_path, image_offset)

    for store_number in self._GetVssStores():
      logging.info(u'Collecting from VSS store number: {0:d}/{1:d}'.format(
          store_number + 1, vss_numbers))
      self._ProcessVss(store_number)

    logging.debug(u'Simple Image Collector - Done.')

  def _ProcessImageWithFilter(self):
    """Processes the image with the collection filter."""
    image_offset = self._GetImageByteOffset()
    preprocessor_collector = tsk_collector.TSKFilePreprocessCollector(
        self._pre_obj, self._source_path, image_offset)

    try:
      filter_object = collector_filter.CollectionFilter(
          preprocessor_collector, self._filter_file_path)

      for pathspec_string in filter_object.GetPathSpecs():
        self._queue.Queue(pathspec_string)

      if self._process_vss:
        logging.debug(u'Searching for VSS')
        vss_numbers = vss.GetVssStoreCount(self._source_path, image_offset)
        for store_number in self._GetVssStores():
          logging.info(u'Collecting from VSS store number: {0:s}/{1:s}'.format(
              store_number + 1, vss_numbers))
          vss_collector = tsk_collector.VSSFilePreprocessCollector(
              self._pre_obj, self._source_path, store_number,
              byte_offset=image_offset)

          for pathspec_string in collector_filter.CollectionFilter(
              vss_collector, self._filter_file_path).GetPathSpecs():
            self._queue.Queue(pathspec_string)
    finally:
      logging.debug(u'Targeted Image Collector - Done.')

  def _ProcessVss(self, store_number):
    """Processes a Volume Shadow Snapshot (VSS) in the image.

    Args:
      store_number: The VSS store index number.
    """
    logging.debug(u'Collecting from VSS store {0:s}'.format(store_number))
    image_offset = self._GetImageByteOffset()

    try:
      file_system_container = self._fscache.Open(
          self._source_path, byte_offset=image_offset,
          store_number=store_number)
      root_path_spec = self._CopyPathToPathSpec(
          'VSS', u'/', inode_number=file_system_container.fs.info.root_inum,
          store_number=store_number)
      # TODO: do we need to set root here?
      root_file_entry = pfile_entry.TSKFileEntry(
          root_path_spec, root=None, fscache=self._fscache)

      # Work-around the limitation in TSKFileEntry that it needs to be open
      # to return stat information. This will be fixed by PyVFS.
      try:
        _  = root_file_entry.Open()
      except AttributeError as e:
        logging.error((
            u'Unable to read root file entry from image with error: '
            u'{0:s}').format(e))

      self._ProcessDirectory(root_file_entry)

    except errors.UnableToOpenFilesystem as e:
      logging.error(u'Unable to read filesystem with error: {0:s}.'.format(e))

    logging.debug(
        u'Collection from VSS store: {0:d} COMPLETED.'.format(store_number))

  def Collect(self):
    """Collects files from the source."""
    source_path_spec = self._CopyPathToPathSpec('OS', self._source_path)
    source_file_entry = pfile_entry.OsFileEntry(source_path_spec)

    if not source_file_entry.IsDirectory() and not source_file_entry.IsFile():
      raise errors.CollectorError(
          u'Source path: {0:s} not a file or directory.'.format(
              self._source_path))

    if self._process_image:
      if self._filter_file_path:
        self._ProcessImageWithFilter()

      else:
        self._ProcessImage()

    else:
      if self._filter_file_path:
        self._ProcessFileSystemWithFilter()

      elif source_file_entry.IsDirectory():
        self._ProcessDirectory(source_file_entry)

      else:
        self._queue.Queue(source_path_spec.ToProtoString())

  def SetImageInformation(
      self, sector_offset=None, byte_offset=None, fscache=None):
    """Sets the image information.

       This function will enable image collection.

    Args:
      sector_offset: Optional sector offset into the image file if this is a disk
                     image. The default is None.
      byte_offset: Optional byte offset into the image file if this is a disk
                   image. The default is None.
      fscache: Optional file system cache (instance of FilesystemCache).
    """
    self._process_image = True
    self._byte_offset = byte_offset
    self._fscache = fscache or pvfs.FilesystemCache()
    self._sector_offset = sector_offset

  def SetVssInformation(self, vss_stores=None):
    """Sets the Volume Shadow Snapshots (VSS) information.

       This function will enable VSS collection.

    Args:
      vss_stores: Optional range of VSS stores to include in the collection.
    """
    self._process_vss = True
    self._vss_stores = vss_stores
