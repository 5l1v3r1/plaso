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
"""This file contains all the error classes used by plaso."""


class Error(Exception):
  """Base error class."""


class TimestampNotCorrectlyFormed(Error):
  """Raised when there is an error adding a timestamp to an EventObject."""


class NotAnEventContainerOrObject(Error):
  """Expect an EventContainer/EventObject yet don't get it it's faulty."""


class UnableToParseFile(Error):
  """Raised when a parser is not designed to parse a file."""


class WrongProtobufEntry(Error):
  """Raised when an EventObject cannot be serialized as a protobuf."""


class UnableToOpenFile(Error):
  """Raised when a PlasoFile class attempts to open a file it cannot open."""


class SameFileType(Error):
  """Raised when a PFile is being evaluated against the same driver type."""


class BadConfigOption(Error):
  """Raised when the engine is started with a faulty parameter."""


class PreProcessFail(Error):
  """Raised when a preprocess module is unable to gather information."""


class PathNotFound(Error):
  """Raised when a preprocessor fails to fill in a path variable."""
