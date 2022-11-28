from protogen import Message, Registry, Enum


class ExtendedRegistry(Registry):

    def __init__(self):
        super().__init__()

    def _register_message(self, message: "Message"):
        # @@@ Overriden: T: Removing "." from beginning of message name as custom datatypes have "." in
        # the beginning in full name attribute of self. This .message_name gets saved as key to
        # message object in registry and this leads to exception at the time of accessing message
        # object by full name attribute with "." stripped off from beginning.
        if message.full_name.startswith("."):
            self._messages_by_name[message.full_name[1:]] = message
        else:
            self._messages_by_name[message.full_name] = message

    def _register_enum(self, enum: "Enum"):
        # @@@ Overriden: T: Removing "." from beginning of enum name as custom datatypes have "." in
        # the beginning in full name attribute of self. This .enum_name gets saved as key to
        # enum object in registry and this leads to exception at the time of accessing enum
        # object by full name attribute with "." stripped off from beginning.
        if enum.full_name.startswith("."):
            self._enums_by_name[enum.full_name[1:]] = enum
        else:
            self._enums_by_name[enum.full_name] = enum
