# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: cyoda-cloud-api.proto
# Protobuf Python Version: 5.26.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import cloudevents_pb2 as cloudevents__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x15\x63yoda-cloud-api.proto\x12\x18org.cyoda.cloud.api.grpc\x1a\x11\x63loudevents.proto2h\n\x12\x43loudEventsService\x12R\n\x0estartStreaming\x12\x1d.io.cloudevents.v1.CloudEvent\x1a\x1d.io.cloudevents.v1.CloudEvent(\x01\x30\x01\x42\x02P\x01\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'cyoda_cloud_api_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'P\001'
  _globals['_CLOUDEVENTSSERVICE']._serialized_start=70
  _globals['_CLOUDEVENTSSERVICE']._serialized_end=174
# @@protoc_insertion_point(module_scope)
