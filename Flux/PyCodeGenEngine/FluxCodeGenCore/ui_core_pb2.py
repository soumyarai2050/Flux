# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: ui_core.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='ui_core.proto',
  package='',
  syntax='proto2',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\rui_core.proto\"E\n\x0cWidgetUIData\x12\t\n\x01i\x18\x01 \x02(\t\x12\t\n\x01x\x18\x02 \x01(\x05\x12\t\n\x01y\x18\x03 \x01(\x05\x12\t\n\x01w\x18\x04 \x01(\x05\x12\t\n\x01h\x18\x05 \x01(\x05\"\xfa\x01\n\x08UIButton\x12\x17\n\x0funpressed_color\x18\x01 \x01(\t\x12\x15\n\rpressed_color\x18\x02 \x01(\t\x12\x19\n\x11unpressed_caption\x18\x03 \x01(\t\x12\x17\n\x0fpressed_caption\x18\x04 \x01(\t\x12 \n\x0b\x62utton_type\x18\x05 \x01(\x0e\x32\x0b.ButtonType\x12 \n\x0b\x62utton_size\x18\x06 \x01(\x0e\x32\x0b.ButtonSize\x12\x17\n\x0fvalue_color_map\x18\x07 \x01(\t\x12\x0e\n\x06\x61\x63tion\x18\x08 \x01(\t\x12\x1d\n\x15pressed_value_as_text\x18\t \x02(\t*[\n\nButtonType\x12\x1b\n\x17\x42UTTON_TYPE_UNSPECIFIED\x10\x00\x12\x15\n\x11\x42UTTON_TYPE_ROUND\x10\x01\x12\x19\n\x15\x42UTTON_TYPE_RECTANGLE\x10\x02*o\n\nButtonSize\x12\x1b\n\x17\x42UTTON_SIZE_UNSPECIFIED\x10\x00\x12\x15\n\x11\x42UTTON_SIZE_SMALL\x10\x01\x12\x16\n\x12\x42UTTON_SIZE_MEDIUM\x10\x02\x12\x15\n\x11\x42UTTON_SIZE_LARGE\x10\x03*?\n\x05Theme\x12\x15\n\x11THEME_UNSPECIFIED\x10\x00\x12\x0e\n\nTHEME_DARK\x10\x01\x12\x0f\n\x0bTHEME_LIGHT\x10\x03'
)

_BUTTONTYPE = _descriptor.EnumDescriptor(
  name='ButtonType',
  full_name='ButtonType',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='BUTTON_TYPE_UNSPECIFIED', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='BUTTON_TYPE_ROUND', index=1, number=1,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='BUTTON_TYPE_RECTANGLE', index=2, number=2,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=341,
  serialized_end=432,
)
_sym_db.RegisterEnumDescriptor(_BUTTONTYPE)

ButtonType = enum_type_wrapper.EnumTypeWrapper(_BUTTONTYPE)
_BUTTONSIZE = _descriptor.EnumDescriptor(
  name='ButtonSize',
  full_name='ButtonSize',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='BUTTON_SIZE_UNSPECIFIED', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='BUTTON_SIZE_SMALL', index=1, number=1,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='BUTTON_SIZE_MEDIUM', index=2, number=2,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='BUTTON_SIZE_LARGE', index=3, number=3,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=434,
  serialized_end=545,
)
_sym_db.RegisterEnumDescriptor(_BUTTONSIZE)

ButtonSize = enum_type_wrapper.EnumTypeWrapper(_BUTTONSIZE)
_THEME = _descriptor.EnumDescriptor(
  name='Theme',
  full_name='Theme',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='THEME_UNSPECIFIED', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='THEME_DARK', index=1, number=1,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='THEME_LIGHT', index=2, number=3,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=547,
  serialized_end=610,
)
_sym_db.RegisterEnumDescriptor(_THEME)

Theme = enum_type_wrapper.EnumTypeWrapper(_THEME)
BUTTON_TYPE_UNSPECIFIED = 0
BUTTON_TYPE_ROUND = 1
BUTTON_TYPE_RECTANGLE = 2
BUTTON_SIZE_UNSPECIFIED = 0
BUTTON_SIZE_SMALL = 1
BUTTON_SIZE_MEDIUM = 2
BUTTON_SIZE_LARGE = 3
THEME_UNSPECIFIED = 0
THEME_DARK = 1
THEME_LIGHT = 3



_WIDGETUIDATA = _descriptor.Descriptor(
  name='WidgetUIData',
  full_name='WidgetUIData',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='i', full_name='WidgetUIData.i', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='x', full_name='WidgetUIData.x', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='y', full_name='WidgetUIData.y', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='w', full_name='WidgetUIData.w', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='h', full_name='WidgetUIData.h', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=17,
  serialized_end=86,
)


_UIBUTTON = _descriptor.Descriptor(
  name='UIButton',
  full_name='UIButton',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='unpressed_color', full_name='UIButton.unpressed_color', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='pressed_color', full_name='UIButton.pressed_color', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='unpressed_caption', full_name='UIButton.unpressed_caption', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='pressed_caption', full_name='UIButton.pressed_caption', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='button_type', full_name='UIButton.button_type', index=4,
      number=5, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='button_size', full_name='UIButton.button_size', index=5,
      number=6, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value_color_map', full_name='UIButton.value_color_map', index=6,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='action', full_name='UIButton.action', index=7,
      number=8, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='pressed_value_as_text', full_name='UIButton.pressed_value_as_text', index=8,
      number=9, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=89,
  serialized_end=339,
)

_UIBUTTON.fields_by_name['button_type'].enum_type = _BUTTONTYPE
_UIBUTTON.fields_by_name['button_size'].enum_type = _BUTTONSIZE
DESCRIPTOR.message_types_by_name['WidgetUIData'] = _WIDGETUIDATA
DESCRIPTOR.message_types_by_name['UIButton'] = _UIBUTTON
DESCRIPTOR.enum_types_by_name['ButtonType'] = _BUTTONTYPE
DESCRIPTOR.enum_types_by_name['ButtonSize'] = _BUTTONSIZE
DESCRIPTOR.enum_types_by_name['Theme'] = _THEME
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

WidgetUIData = _reflection.GeneratedProtocolMessageType('WidgetUIData', (_message.Message,), {
  'DESCRIPTOR' : _WIDGETUIDATA,
  '__module__' : 'ui_core_pb2'
  # @@protoc_insertion_point(class_scope:WidgetUIData)
  })
_sym_db.RegisterMessage(WidgetUIData)

UIButton = _reflection.GeneratedProtocolMessageType('UIButton', (_message.Message,), {
  'DESCRIPTOR' : _UIBUTTON,
  '__module__' : 'ui_core_pb2'
  # @@protoc_insertion_point(class_scope:UIButton)
  })
_sym_db.RegisterMessage(UIButton)


# @@protoc_insertion_point(module_scope)
