#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests for the storage media tool object."""

import argparse
import unittest

from plaso.cli import storage_media_tool
from plaso.lib import errors

from tests.cli import test_lib


class StorageMediaToolTest(test_lib.CLIToolTestCase):
  """Tests for the storage media tool object."""

  _EXPECTED_OUTPUT_CREDENTIAL_OPTIONS = u'\n'.join([
      u'usage: storage_media_tool_test.py [--credential TYPE:DATA]',
      u'',
      u'Test argument parser.',
      u'',
      u'optional arguments:',
      u'  --credential TYPE:DATA',
      (u'                        Define a credentials that can be used to '
       u'unlock'),
      (u'                        encrypted volumes e.g. BitLocker. The '
       u'credential is'),
      (u'                        defined as type:data e.g. '
       u'"password:BDE-test".'),
      (u'                        Supported credential types are: key_data, '
       u'password,'),
      (u'                        recovery_password, startup_key. Binary '
       u'key data is'),
      u'                        expected to be passed in BASE-16 encoding',
      (u'                        (hexadecimal). WARNING credentials passed '
       u'via command'),
      (u'                        line arguments can end up in logs, so use '
       u'this option'),
      u'                        with care.',
      u''])

  _EXPECTED_OUTPUT_FILTER_OPTIONS = u'\n'.join([
      u'usage: storage_media_tool_test.py [-f FILE_FILTER]',
      u'',
      u'Test argument parser.',
      u'',
      u'optional arguments:',
      u'  -f FILE_FILTER, --file_filter FILE_FILTER, --file-filter FILE_FILTER',
      (u'                        List of files to include for targeted '
       u'collection of'),
      (u'                        files to parse, one line per file path, '
       u'setup is'),
      (u'                        /path|file - where each element can contain '
       u'either a'),
      (u'                        variable set in the preprocessing stage or '
       u'a regular'),
      u'                        expression.',
      u''])

  _EXPECTED_OUTPUT_STORAGE_MEDIA_OPTIONS = u'\n'.join([
      u'usage: storage_media_tool_test.py [--partition PARTITION_NUMBER]',
      u'                                  [-o IMAGE_OFFSET]',
      u'                                  [--sector_size BYTES_PER_SECTOR]',
      u'                                  [--ob IMAGE_OFFSET_BYTES]',
      u'',
      u'Test argument parser.',
      u'',
      u'optional arguments:',
      u'  --partition PARTITION_NUMBER',
      (u'                        Choose a partition number from a disk image. '
       u'This'),
      (u'                        partition number should correspond to the '
       u'partition'),
      (u'                        number on the disk image, starting from '
       u'partition 1.'),
      u'                        All partitions can be defined as: "all".',
      u'  -o IMAGE_OFFSET, --offset IMAGE_OFFSET',
      (u'                        The offset of the volume within the storage '
       u'media'),
      (u'                        image in number of sectors. A sector is 512 '
       u'bytes in'),
      (u'                        size by default this can be overwritten with '
       u'the'),
      u'                        --sector_size option.',
      u'  --sector_size BYTES_PER_SECTOR, --sector-size BYTES_PER_SECTOR',
      (u'                        The number of bytes per sector, which is 512 '
       u'by'),
      u'                        default.',
      (u'  --ob IMAGE_OFFSET_BYTES, --offset_bytes IMAGE_OFFSET_BYTES, '
       u'--offset_bytes IMAGE_OFFSET_BYTES'),
      (u'                        The offset of the volume within the storage '
       u'media'),
      u'                        image in number of bytes.',
      u''])

  _EXPECTED_OUTPUT_VSS_PROCESSING_OPTIONS = u'\n'.join([
      (u'usage: storage_media_tool_test.py [--no_vss] '
       u'[--vss_stores VSS_STORES]'),
      u'',
      u'Test argument parser.',
      u'',
      u'optional arguments:',
      (u'  --no_vss, --no-vss    Do not scan for Volume Shadow Snapshots '
       u'(VSS). This'),
      (u'                        means that VSS information will not be '
       u'included in the'),
      u'                        extraction phase.',
      u'  --vss_stores VSS_STORES, --vss-stores VSS_STORES',
      (u'                        Define Volume Shadow Snapshots (VSS) (or '
       u'stores that'),
      (u'                        need to be processed. A range of stores can '
       u'be defined'),
      (u'                        as: "3..5". Multiple stores can be defined '
       u'as: "1,3,5"'),
      (u'                        (a list of comma separated values). Ranges '
       u'and lists'),
      (u'                        can also be combined as: "1,3..5". The '
       u'first store is'),
      u'                        1. All stores can be defined as: "all".',
      u''])

  def testAddCredentialOptions(self):
    """Tests the AddCredentialOptions function."""
    argument_parser = argparse.ArgumentParser(
        prog=u'storage_media_tool_test.py',
        description=u'Test argument parser.',
        add_help=False)

    test_tool = storage_media_tool.StorageMediaTool()
    test_tool.AddCredentialOptions(argument_parser)

    output = argument_parser.format_help()
    self.assertEqual(output, self._EXPECTED_OUTPUT_CREDENTIAL_OPTIONS)

  def testAddFilterOptions(self):
    """Tests the AddFilterOptions function."""
    argument_parser = argparse.ArgumentParser(
        prog=u'storage_media_tool_test.py',
        description=u'Test argument parser.',
        add_help=False)

    test_tool = storage_media_tool.StorageMediaTool()
    test_tool.AddFilterOptions(argument_parser)

    output = argument_parser.format_help()
    self.assertEqual(output, self._EXPECTED_OUTPUT_FILTER_OPTIONS)

  def testAddStorageMediaImageOptions(self):
    """Tests the AddStorageMediaImageOptions function."""
    argument_parser = argparse.ArgumentParser(
        prog=u'storage_media_tool_test.py',
        description=u'Test argument parser.',
        add_help=False)

    test_tool = storage_media_tool.StorageMediaTool()
    test_tool.AddStorageMediaImageOptions(argument_parser)

    output = argument_parser.format_help()
    self.assertEqual(output, self._EXPECTED_OUTPUT_STORAGE_MEDIA_OPTIONS)

  def testAddVSSProcessingOptions(self):
    """Tests the AddVSSProcessingOptions function."""
    argument_parser = argparse.ArgumentParser(
        prog=u'storage_media_tool_test.py',
        description=u'Test argument parser.',
        add_help=False)

    test_tool = storage_media_tool.StorageMediaTool()
    test_tool.AddVSSProcessingOptions(argument_parser)

    output = argument_parser.format_help()
    self.assertEqual(output, self._EXPECTED_OUTPUT_VSS_PROCESSING_OPTIONS)

  def testParseOptions(self):
    """Tests the ParseOptions function."""
    test_tool = storage_media_tool.StorageMediaTool()

    options = test_lib.TestOptions()

    with self.assertRaises(errors.BadConfigOption):
      test_tool.ParseOptions(options)

    options.source = self._GetTestFilePath([u'ímynd.dd'])

    test_tool.ParseOptions(options)

    # TODO: improve this test.


if __name__ == '__main__':
  unittest.main()
