#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""This file contains tests for the format specification classes."""
import unittest

from plaso.classifier import specification


class SpecificationStoreTest(unittest.TestCase):
  """Class to test SpecificationStore."""

  def testAddSpecification(self):
    """Function to test the AddSpecification function."""
    store = specification.SpecificationStore()

    format_regf = specification.Specification("REGF")
    format_regf.AddSignature("regf", offset=0)

    format_esedb = specification.Specification("ESEDB")
    format_esedb.AddSignature("\xef\xcd\xab\x89", offset=4)

    store.AddSpecification(format_regf)
    store.AddSpecification(format_esedb)

    self.assertRaises(ValueError, store.AddSpecification, format_regf)


if __name__ == "__main__":
  unittest.main()
