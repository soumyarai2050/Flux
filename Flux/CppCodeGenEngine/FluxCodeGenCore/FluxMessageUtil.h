
#ifndef FluxMessageUtil_h
#define FluxMessageUtil_h 1

#include <google/protobuf/wire_format.h>
#include <google/protobuf/wire_format_lite.h>
#include <google/protobuf/wire_format_lite_inl.h>


#include <google/protobuf/compiler/plugin.h>
#include <google/protobuf/compiler/code_generator.h>

#include <google/protobuf/io/printer.h>
#include <google/protobuf/io/zero_copy_stream.h>

#include "flux_options.pb.h"

inline const Descriptor* GetNestedMessageDescriptorFromMessage(const std::string& msgName, const Descriptor & message)
{
	for (int i = 0; i < message.field_count(); ++i) 
	{
		const FieldDescriptor &field ( *message.field(i) );
		if (field.type() == FieldDescriptor::TYPE_MESSAGE || field.type() == FieldDescriptor::TYPE_GROUP)
		{
			if(field.message_type()->name() == msgName)
			{
				return field.message_type();
			}
			else
			{
				const Descriptor *nestedDescriptor = GetNestedMessageDescriptorFromMessage(msgName,*field.message_type()); 
				if(0 != nestedDescriptor)
				{
					return nestedDescriptor;
				}
			}
		}
	}
	return 0;
}

inline const Descriptor* GetNestedMessageDescriptorFromFile(const std::string& msgName, const FileDescriptor & file)
{
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor *message = file.message_type(i);
		if(message->name() == msgName)
		{
			return message;
		}
		else
		{
			const Descriptor *nestedDescriptor = GetNestedMessageDescriptorFromMessage(msgName,*message); 
			if(0 != nestedDescriptor)
			{
				return nestedDescriptor;
			}
		}
	}
	return 0;
}

inline const FieldDescriptor* GetNestedFieldDescriptorFromMessage(const std::string& typeName, const std::string& varName, const Descriptor & message)
{
	for (int i = 0; i < message.field_count(); ++i) 
	{
		const FieldDescriptor &field ( *message.field(i) );
		if (field.type() == FieldDescriptor::TYPE_MESSAGE || field.type() == FieldDescriptor::TYPE_GROUP)
		{
			if(field.message_type()->name() == typeName && varName == field.name())
			{
				return &field;
			}//else not required, this message may contain its own type with matching variable name
			const FieldDescriptor *nestedFieldDescriptor = GetNestedFieldDescriptorFromMessage(typeName, varName, *field.message_type()); 
			if(0 != nestedFieldDescriptor)
			{
				return nestedFieldDescriptor;
			}
		}
	}
	return 0;
}

inline const bool IsNestedFieldRepeated(const std::string& strContainorTypeName, const std::string& nestedTypeName, const std::string& nestedVarName, const FileDescriptor & file)
{
	const Descriptor* ptrContainorTypeDescriptor = GetNestedMessageDescriptorFromFile(strContainorTypeName,file);
	const FieldDescriptor* ptrNestedFieldDescriptor = GetNestedFieldDescriptorFromMessage(nestedTypeName,nestedVarName,*ptrContainorTypeDescriptor);
	if(0 == ptrNestedFieldDescriptor)
		throw "Constraint Failed: ptrNestedFieldDescriptor not found!!";
	//All set now check the repeat
	return ptrNestedFieldDescriptor->is_repeated();
}


#endif //FluxMessageUtil_h

