#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2012 Google Inc. All Rights Reserved.
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
"""This file contains log2timeline, the friendly front-end to plaso."""

import argparse
import os
import logging
import sys

from plaso.lib import engine

# The number of bytes in a Mb.
BYTES_IN_A_MB = 1024 * 1024


if __name__ == '__main__':
  arg_parser = argparse.ArgumentParser(
      description=('log2timeline is the main frontend to the plaso backend, used'
                   ' to collect and correlate events extracted from the filesystem')) 

  arg_parser.add_argument(
      '-z', '--zone', dest='tzone', action='store', type=str, default='UTC',
      help='Define the timezone of the IMAGE (not the output).')

  arg_parser.add_argument(
      '-p', '--preprocess', dest='preprocess', action='store_true', default=False,
      help='Turn on pre-processing. Pre-processing is turned on by default in image parsing')

  arg_parser.add_argument(
      '--buffer-size', '--bs', dest='buffer_size', action='store', default=0,
      help='The buffer size for the output (defaults to 256Mb).')

  arg_parser.add_argument(
      '--workers', dest='workers', action='store', type=int, default=10,
      help='The number of worker threads [default 10].')

  arg_parser.add_argument(
      '-i', '--image', dest='image', action='store_true',
      default=False, help='Indicates that this is an image instaed of a regular file.')

  arg_parser.add_argument(
      '--vss', dest='parse_vss', action='store_true', default=False,
      help=('Collect data from VSS. Off by default, this should be used on Windows systems'
            ' that have active VSS (Volume Shadow Copies) that need to be included in the '
            'analyzis.'))

  arg_parser.add_argument(
      '--single-thread', dest='single_thread', action='store_true', default=False,
       help='Indicate that the tool should run in a single thread.')

  arg_parser.add_argument(
      '--open-files', dest='open_files', action='store_true', default=False,
      help=('Indicate that the tool should try to open files to extract embedded files '
            'within them, for instance to extract files from compressed containers, etc.'))

  arg_parser.add_argument(
      '--noopen-files', dest='open_files', action='store_false',
      help=('Indicate that the tool should NOT try to '
            'open files to extract embedded files within them.'))

  arg_parser.add_argument(
      '-o', '--offset', dest='image_offset', action='store', default=0, type=int,
      help='The sector offset to the image in sector sizes (512 bytes).')

  arg_parser.add_argument(
      '--ob', '--offset_bytes', dest='image_offset_bytes', action='store', default=0,
      type=int, help='The bytes offset to the image')

  arg_parser.add_argument(
      '-d', '--debug', dest='debug', action='store_true', default=False,
      help='Turn on debug information in the tool.')

  arg_parser.add_argument(
      '-w', '--write', dest='output', action='store', required=True, metavar='STORAGE_FILE',
      help='The output file (needs to be defined).')

  arg_parser.add_argument(
      'filename', action='store', metavar='FILENAME_OR_MOUNT_POINT', default=None,
      help=('The path to the file, directory, image file or mount point that the tool'
            ' should parse. If this is a directory it will recursively go through it, '
            'same with an image file.'))

  options = arg_parser.parse_args()

  if options.tzone == 'list':
    print '=' * 40
    print '       ZONES'
    print '-' * 40
    for zone in engine.GetTimeZoneList():
      print '  %s' % zone
    print '=' * 40
    sys.exit(0)

  # This frontend only deals with local setup of the tool.
  options.local = True

  options.recursive = os.path.isdir(options.filename)

  if options.image_offset or options.image_offset_bytes:
    options.image = True

  format_str = '[%(levelname)s] (%(processName)-10s) %(message)s'
  if options.debug:
    logging.basicConfig(level=logging.DEBUG, format=format_str)
  else:
    logging.basicConfig(level=logging.INFO, format=format_str)

  if options.image:
    options.preprocess = True

  if options.buffer_size:
    if options.buffer_size[-1].lower() == 'm':
      options.buffer_size = int(options.buffer_size[:-1]) * BYTES_IN_A_MB
    else:
      try:
        options.buffer_size = int(options.buffer_size)
      except ValueError:
        logging.error(('Wrong usage: Buffer size needs to be an integer or'
                       ' end with M'))
        sys.exit(1)

  l2t = engine.Engine(options)
  try:
    l2t.Start()
    logging.info('Run completed.')
  except KeyboardInterrupt:
    logging.warning('Tool being killed.')
    l2t.StopThreads()
