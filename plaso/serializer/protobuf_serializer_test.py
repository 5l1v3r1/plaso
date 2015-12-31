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
"""Tests for the serializer object implementation using protobuf."""

import unittest

from plaso.lib import event
from plaso.proto import plaso_storage_pb2
from plaso.proto import transmission_pb2
from plaso.serializer import protobuf_serializer


class ProtobufAnalysisReportSerializerTest(unittest.TestCase):
  """Tests for the protobuf analysis report serializer object."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    # TODO: add an analysis report test.
    pass

  def testReadSerialized(self):
    """Test the read serialized functionality."""
    # TODO: add an analysis report test.
    pass

  def testWriteSerialized(self):
    """Test the write serialized functionality."""
    # TODO: add an analysis report test.
    pass


class ProtobufEventContainerSerializerTest(unittest.TestCase):
  """Tests for the protobuf event container serializer object."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    # TODO: add an event container test.
    pass

  def testReadSerialized(self):
    """Test the read serialized functionality."""
    # TODO: add an event container test.
    pass

  def testWriteSerialized(self):
    """Test the write serialized functionality."""
    # TODO: add an event container test.
    pass


class ProtobufEventObjectSerializerTest(unittest.TestCase):
  """Tests for the protobuf event object serializer object."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    proto = plaso_storage_pb2.EventObject()

    proto.data_type = 'test:event2'
    proto.timestamp = 1234124
    proto.timestamp_desc = 'Written'

    serializer = protobuf_serializer.ProtobufEventAttributeSerializer

    proto_attribute = proto.attributes.add()
    serializer.WriteSerializedObject(proto_attribute, 'zero_integer', 0)

    proto_attribute = proto.attributes.add()
    dict_object = {
        'a': 'not b', 'c': 34, 'list': ['sf', 234], 'an': [234, 32]}
    serializer.WriteSerializedObject(proto_attribute, 'my_dict', dict_object)

    proto_attribute = proto.attributes.add()
    tuple_object = (
        'some item', [234, 52, 15], {'a': 'not a', 'b': 'not b'}, 35)
    serializer.WriteSerializedObject(proto_attribute, 'a_tuple', tuple_object)

    proto_attribute = proto.attributes.add()
    list_object = ['asf', 4234, 2, 54, 'asf']
    serializer.WriteSerializedObject(proto_attribute, 'my_list', list_object)

    proto_attribute = proto.attributes.add()
    serializer.WriteSerializedObject(
        proto_attribute, 'unicode_string', u'And I\'m a unicorn.')

    proto_attribute = proto.attributes.add()
    serializer.WriteSerializedObject(proto_attribute, 'integer', 34)

    proto_attribute = proto.attributes.add()
    serializer.WriteSerializedObject(proto_attribute, 'string', 'Normal string')

    proto.uuid = '5a78777006de4ddb8d7bbe12ab92ccf8'

    self._proto_string = proto.SerializeToString()

  def testReadSerialized(self):
    """Test the read serialized functionality."""
    serializer = protobuf_serializer.ProtobufEventObjectSerializer
    event_object = serializer.ReadSerialized(self._proto_string)

    # An integer value containing 0 should get stored.
    self.assertTrue(hasattr(event_object, 'zero_integer'))

    attribute_value = getattr(event_object, 'integer', 0)
    self.assertEquals(attribute_value, 34)

    attribute_value = getattr(event_object, 'my_list', [])
    self.assertEquals(len(attribute_value), 5)

    attribute_value = getattr(event_object, 'string', '')
    self.assertEquals(attribute_value, 'Normal string')

    attribute_value = getattr(event_object, 'unicode_string', u'')
    self.assertEquals(attribute_value, u'And I\'m a unicorn.')

    attribute_value = getattr(event_object, 'a_tuple', ())
    self.assertEquals(len(attribute_value), 4)

  def testWriteSerialized(self):
    """Test the write serialized functionality."""
    event_object = event.EventObject()

    event_object.data_type = 'test:event2'
    event_object.timestamp = 1234124
    event_object.timestamp_desc = 'Written'
    # Prevent the event object for generating its own UUID.
    event_object.uuid = '5a78777006de4ddb8d7bbe12ab92ccf8'

    event_object.empty_string = u''
    event_object.zero_integer = 0
    event_object.integer = 34
    event_object.string = 'Normal string'
    event_object.unicode_string = u'And I\'m a unicorn.'
    event_object.my_list = ['asf', 4234, 2, 54, 'asf']
    event_object.my_dict = {
        'a': 'not b', 'c': 34, 'list': ['sf', 234], 'an': [234, 32]}
    event_object.a_tuple = (
        'some item', [234, 52, 15], {'a': 'not a', 'b': 'not b'}, 35)
    event_object.null_value = None

    serializer = protobuf_serializer.ProtobufEventObjectSerializer
    proto_string = serializer.WriteSerialized(event_object)
    self.assertEquals(proto_string, self._proto_string)

    event_object = serializer.ReadSerialized(proto_string)

    # An empty string should not get stored.
    self.assertFalse(hasattr(event_object, 'empty_string'))

    # A None (or Null) value should not get stored.
    self.assertFalse(hasattr(event_object, 'null_value'))


class ProtobufEventPathSpecSerializerTest(unittest.TestCase):
  """Tests for the protobuf event path specification serializer object."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    proto = transmission_pb2.PathSpec()

    proto.file_path = u'/tmp/nowhere'
    # Type 0 = OS.
    proto.type = 0

    nested_path_spec_proto = transmission_pb2.PathSpec()
    nested_path_spec_proto.container_path = u'SomeFilePath'
    # Type 2 = ZIP.
    nested_path_spec_proto.type = 2
    nested_path_spec_proto.file_path = u'My.zip'
    nested_path_spec_proto.image_offset = 35
    nested_path_spec_proto.image_inode = 6124543

    proto.nested_pathspec.MergeFrom(nested_path_spec_proto)

    self._proto_string = proto.SerializeToString()

  def testReadSerialized(self):
    """Test the read serialized functionality."""
    serializer = protobuf_serializer.ProtobufEventPathSpecSerializer
    event_path_spec = serializer.ReadSerialized(self._proto_string)

    self.assertEquals(event_path_spec.type, 'OS')
    self.assertEquals(event_path_spec.file_path, u'/tmp/nowhere')
    self.assertTrue(hasattr(event_path_spec, 'nested_pathspec'))

    nested_event_path_spec = event_path_spec.nested_pathspec

    self.assertEquals(nested_event_path_spec.container_path, u'SomeFilePath')
    self.assertEquals(nested_event_path_spec.image_offset, 35)
    self.assertEquals(nested_event_path_spec.image_inode, 6124543)
    self.assertEquals(nested_event_path_spec.type, 'ZIP')

  def testWriteSerialized(self):
    """Test the write serialized functionality."""
    event_path_spec = event.EventPathSpec()

    event_path_spec.type = 'OS'
    event_path_spec.file_path = u'/tmp/nowhere'
    event_path_spec.nested_pathspec = event.EventPathSpec()

    event_path_spec.nested_pathspec.type = 'ZIP'
    event_path_spec.nested_pathspec.file_path = u'My.zip'
    event_path_spec.nested_pathspec.container_path = u'SomeFilePath'
    event_path_spec.nested_pathspec.image_offset = 35
    event_path_spec.nested_pathspec.image_inode = 6124543

    serializer = protobuf_serializer.ProtobufEventPathSpecSerializer
    proto_string = serializer.WriteSerialized(event_path_spec)
    self.assertEquals(proto_string, self._proto_string)


class ProtobufEventPathBundleSerializerTest(unittest.TestCase):
  """Tests for the protobuf event path bundle serializer object."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    proto = transmission_pb2.PathBundle()
    proto.pattern = '/tmp/.+'

    path_spec_proto = transmission_pb2.PathSpec()
    path_spec_proto.file_path = u'/tmp/nowhere'
    # Type 0 = OS.
    path_spec_proto.type = 0

    nested_path_spec_proto = transmission_pb2.PathSpec()
    nested_path_spec_proto.container_path = u'SomeFilePath'
    # Type 2 = ZIP.
    nested_path_spec_proto.type = 2
    nested_path_spec_proto.file_path = u'My.zip'
    nested_path_spec_proto.image_offset = 35
    nested_path_spec_proto.image_inode = 6124543

    path_spec_proto.nested_pathspec.MergeFrom(nested_path_spec_proto)

    path_spec_proto_add = proto.pathspecs.add()
    path_spec_proto_add.MergeFrom(path_spec_proto)

    path_spec_proto = transmission_pb2.PathSpec()
    # Type 1 = TSK.
    path_spec_proto.type = 1
    path_spec_proto.container_path = u'myimage.raw'
    path_spec_proto.image_inode = 124
    path_spec_proto.image_offset = 12345

    path_spec_proto_add = proto.pathspecs.add()
    path_spec_proto_add.MergeFrom(path_spec_proto)

    self._proto_string = proto.SerializeToString()

  def testReadSerialized(self):
    """Test the read serialized functionality."""
    serializer = protobuf_serializer.ProtobufEventPathBundleSerializer
    event_path_bundle = serializer.ReadSerialized(self._proto_string)

    path_specs = list(event_path_bundle.GetPathspecs())
    self.assertEquals(len(path_specs), 2)
    self.assertEquals(len(list(event_path_bundle.ListFiles())), 2)
    self.assertEquals(event_path_bundle.pattern, '/tmp/.+')

    nested_hash = u'-:-:-:-:/tmp/nowhere:SomeFilePath:35:-:6124543:My.zip:'
    event_path_spec = event_path_bundle.GetPathspecFromHash(nested_hash)
    self.assertNotEquals(event_path_spec, None)

    self.assertEquals(event_path_spec.type, 'OS')
    self.assertEquals(event_path_spec.file_path, u'/tmp/nowhere')

  def testWriteSerialized(self):
    """Test the write serialized functionality."""
    event_path_bundle = event.EventPathBundle()

    event_path_bundle.pattern = '/tmp/.+'

    event_path_spec = event.EventPathSpec()

    event_path_spec.type = 'OS'
    event_path_spec.file_path = u'/tmp/nowhere'
    event_path_spec.nested_pathspec = event.EventPathSpec()

    event_path_spec.nested_pathspec.type = 'ZIP'
    event_path_spec.nested_pathspec.file_path = u'My.zip'
    event_path_spec.nested_pathspec.container_path = u'SomeFilePath'
    event_path_spec.nested_pathspec.image_offset = 35
    event_path_spec.nested_pathspec.image_inode = 6124543

    event_path_bundle.AppendPathspec(event_path_spec)

    event_path_spec = event.EventPathSpec()

    event_path_spec.type = 'TSK'
    event_path_spec.container_path = u'myimage.raw'
    event_path_spec.image_offset = 12345
    event_path_spec.image_inode = 124

    event_path_bundle.AppendPathspec(event_path_spec)

    serializer = protobuf_serializer.ProtobufEventPathBundleSerializer
    proto_string = serializer.WriteSerialized(event_path_bundle)
    self.assertEquals(proto_string, self._proto_string)


class ProtobufEventTagSerializerTest(unittest.TestCase):
  """Tests for the protobuf event tag serializer object."""

  def setUp(self):
    """Sets up the needed objects used throughout the test."""
    proto = plaso_storage_pb2.EventTagging()
    proto.store_number = 234
    proto.store_index = 18
    proto.comment = u'My first comment.'
    proto.color = u'Red'
    proto_tag = proto.tags.add()
    proto_tag.value = u'Malware'
    proto_tag = proto.tags.add()
    proto_tag.value = u'Common'

    self._proto_string = proto.SerializeToString()

  def testReadSerialized(self):
    """Test the read serialized functionality."""
    serializer = protobuf_serializer.ProtobufEventTagSerializer
    event_tag = serializer.ReadSerialized(self._proto_string)

    self.assertEquals(event_tag.color, u'Red')
    self.assertEquals(event_tag.comment, u'My first comment.')
    self.assertEquals(event_tag.store_index, 18)
    self.assertEquals(len(event_tag.tags), 2)
    self.assertEquals(event_tag.tags, [u'Malware', u'Common'])

  def testWriteSerialized(self):
    """Test the write serialized functionality."""
    event_tag = event.EventTag()

    event_tag.store_number = 234
    event_tag.store_index = 18
    event_tag.comment = u'My first comment.'
    event_tag.color = u'Red'
    event_tag.tags = [u'Malware', u'Common']

    serializer = protobuf_serializer.ProtobufEventTagSerializer
    proto_string = serializer.WriteSerialized(event_tag)
    self.assertEquals(proto_string, self._proto_string)


if __name__ == '__main__':
  unittest.main()
