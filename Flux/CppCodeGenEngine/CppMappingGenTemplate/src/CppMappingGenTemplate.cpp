/**
* protocol Buffer Class Standard POCO Compatibility Generator Plugin
*
*
*/

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <FluxFileUtil.h>

class CppMappingGenTemplate: public FluxCodeGenerator
{
	public:
		void PrintInputField (const FieldDescriptor &fieldDescriptor, io::Printer &printer, const FieldDescriptor& fieldAttributeDescriptor) const;
		void PrintOutputField (const FieldDescriptor &fieldDescriptor, io::Printer & printer, const FieldDescriptor& fieldAttributeDescriptor) const;
		void PrintInputMessage (const Descriptor & messageDescriptor, io::Printer & printer, const protobuf::Message *mappingMessage,
			const protobuf::Message::Reflection *mappingMessageReflection, const Descriptor &mappingMessageDescriptor) const;
		void PrintOutputMessage (const Descriptor & messageDescriptor, io::Printer & printer, const protobuf::Message *mappingMessage,
			const protobuf::Message::Reflection *mappingMessageReflection, const Descriptor &mappingMessageDescriptor) const;
		CppMappingGenTemplate() {}
 		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void CppMappingGenTemplate::PrintInputField (const FieldDescriptor &fieldDescriptor, io::Printer &printer, const FieldDescriptor& fieldAttributeDescriptor) const
{
	//Now the real generation
	map<std::string, std::string> transformationElementMap; //Populate this with elements required for mapping
	if(fieldDescriptor.is_repeated())
	{
	}
	else
	{
		//Non repeated field
		//within simple type we have 4 cases to handle
		//strings
		//enums
		//rest of it
		//dateTime (Protobuf representation is long)
		/* Default Values - Handling Strings*/
		switch(fieldDescriptor.type())
		{
			case FieldDescriptor::TYPE_STRING:
			{
			}
			break;
			case FieldDescriptor::TYPE_ENUM:
			{
			}
			break;
			case FieldDescriptor::TYPE_INT64:
			{
				//Get Default
				//An int64 may or may-not be a date time.If its a datetime field, it should have FluxFIdValDateTime option set
				std::string strFluxFldTestVal=fieldDescriptor.options().GetExtension(FluxFldValDateTime);
				if(0 != strFluxFldTestVal.length())
				{
					//This is a date time field, handle it like that - we should have imported time-support already
				}
				else
				{
					//This is a int64 simple type field handle here

				}
				break;
			}
			default:
				//All other simple types fall in this case handle here
				{
					//This is any other simple type field, handle here
				}
		}
	}
}

void CppMappingGenTemplate::PrintOutputField (const FieldDescriptor &fieldDescriptor, io::Printer & printer, const FieldDescriptor& fieldAttributeDescriptor) const
{
	//Now the real generation
	map<std::string, std::string> transformationElementMap; //Populate this with elements required for mapping
	if (fieldDescriptor.is_repeated())
	{
	}
	else
	{
		//Non repeated field
		//within simple type we have 4 cases to handle
		//strings
		//enums
		//rest of it
		//DateTime (Protobuf representation is long)
		/* Default Values - Handling Strings*/
		switch(fieldDescriptor.type())
		{
			case FieldDescriptor::TYPE_STRING:
			{
			}
			break;
			case FieldDescriptor::TYPE_ENUM:
			{
			}
			break;
			case FieldDescriptor::TYPE_INT64:
			{
				//Get Default
				//An int64 can or cannot be a date time. If its a datetime field, it should have FluxFIdValDateTime option set
				std::string strFluxFldTestVal=fieldDescriptor.options().GetExtension(FluxFldValDateTime);
				if(0 != strFluxFldTestVal.length())
				{
					//This is a date time field, handle it like that - we should have imported time-support already
				}
				else
				{
					//This is a int64 simple type field handle here 
				}
				break;
			}
			default:
				//All other simple types fall in this case handle here
				{
					//This is any other simple type field, handle here
				}
			}
		}
}

void CppMappingGenTemplate::PrintInputMessage (const Descriptor & messageDescriptor, io::Printer & printer, const protobuf::Message *mappingMessage, const protobuf::Message::Reflection *mappingMessageReflection, const Descriptor &mappingMessageDescriptor) const
{
	//iterate over all fields we have and call PrintField to do the Job (if complex type then recurse)
	for(int i=0; i< messageDescriptor.field_count(); ++i)
	{
		const FieldDescriptor &fieldDescriptor (*messageDescriptor.field(i));
		const FieldDescriptor& fieldAttributeDescriptor = *(mappingMessageDescriptor.FindFieldByName(fieldDescriptor.name()+ MAPPING_ATTRIBUTE_SUFFIX));
		if(fieldDescriptor.type() == FieldDescriptor::TYPE_MESSAGE)
		{
			//This field is a complex type, get sub message out from message
			const Descriptor & nestedMessageDescriptor = (*fieldDescriptor.message_type());
			const protobuf::Message & nestedMappingMessage = mappingMessageReflection -> GetMessage(*mappingMessage, &fieldAttributeDescriptor);
			const protobuf::Message::Reflection *nestedMappingMessageReflection = nestedMappingMessage.GetReflection();
			const Descriptor & nestedMappingMessageDescriptor = (*fieldAttributeDescriptor.message_type());
			PrintInputMessage(nestedMessageDescriptor, printer, &nestedMappingMessage, nestedMappingMessageReflection, nestedMappingMessageDescriptor);
		}
		else
		{
			//This field ia a simple type or enum type, both handled same way
			PrintInputField(fieldDescriptor, printer, fieldAttributeDescriptor);
		}
	}
}

void CppMappingGenTemplate::PrintOutputMessage ( const Descriptor & messageDescriptor, io::Printer & printer, const protobuf::Message *mappingMessage, const protobuf::Message::Reflection *mappingMessageReflection, const Descriptor &mappingMessageDescriptor) const
{
	//iterate over all fields we have and call PrintField to do the job ( if complex type then recurse)
	for(int i=0; i<messageDescriptor.field_count(); ++i)
	{
		const FieldDescriptor &fieldDescriptor(*messageDescriptor.field(i));
		const FieldDescriptor& fieldAttributeDescriptor = *(mappingMessageDescriptor.FindFieldByName(fieldDescriptor.name() + MAPPING_ATTRIBUTE_SUFFIX));
		if(fieldDescriptor.type() == FieldDescriptor::TYPE_MESSAGE)
		{
			//This field is a complex type, get sub message out from message
			const Descriptor & nestedMessageDescriptor = (*fieldDescriptor.message_type());
			const protobuf::Message &nestedMappingMessage = mappingMessageReflection -> GetMessage(*mappingMessage, &fieldAttributeDescriptor);
			const protobuf::Message::Reflection *nestedMappingMessageReflection = nestedMappingMessage.GetReflection();
			const Descriptor & nestedMappingMessageDescriptor = (*fieldAttributeDescriptor.message_type());
			PrintOutputMessage(nestedMessageDescriptor, printer, &nestedMappingMessage, nestedMappingMessageReflection, nestedMappingMessageDescriptor);
		}
		else
		{
			//this field is a simple type or enum type, both handled same way
			PrintOutputField(fieldDescriptor, printer, fieldAttributeDescriptor);
		}
	}	
}

//Local to file (may be can make local to function)
namespace{
	class DescriptorHolder
	{
		public:
			const Descriptor *descriptor;
			bool isRequest;
			bool isResponse;
			DescriptorHolder():descriptor(0), isRequest(false),isResponse(false){}
			DescriptorHolder(const Descriptor * descriptor_, bool isRequest_, bool isResponse_)
			:descriptor(descriptor_), isRequest(isRequest_), isResponse(isResponse_){}
	};
}
bool CppMappingGenTemplate::Generate(const FileDescriptor* fileDescriptor, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const
{
	std::map<std::string, std::map <std::string, DescriptorHolder>* > fileAndDescriptorMap;
	std::map<std::string, std::map <std::string, DescriptorHolder>* >::iterator fileAndDescriptorMapItr;
	std::map<std::string, DescriptorHolder>::iterator msgMapItr;
	for(int i=0; i<fileDescriptor->service_count(); ++i)
	{
		const ServiceDescriptor *serviceDesc = fileDescriptor->service(i);
		for(int j=0; j<serviceDesc->method_count(); ++j)
		{
			const Descriptor *inputDescriptor = serviceDesc->method(j)->input_type();
			const Descriptor *outputDescriptor = serviceDesc->method(j)->output_type();
			//handle input first
			if(0 != inputDescriptor->field_count())
			{
				std::map <std::string, DescriptorHolder>* msgMap = fileAndDescriptorMap[GetFileNameFromFileDescriptor(inputDescriptor->file())];
			if(0 == msgMap)
			{
				fileAndDescriptorMap[GetFileNameFromFileDescriptor(inputDescriptor->file())] = msgMap = new std::map <std::string, DescriptorHolder>;
				(*msgMap) [inputDescriptor->full_name()] = DescriptorHolder(inputDescriptor, true/*Inout*/, false/*Output*/);
			}
			else
			{
				DescriptorHolder descriptorHolder = (*msgMap) [ inputDescriptor->full_name()];
				if(0 == descriptorHolder.descriptor)
				{
					(*msgMap)[inputDescriptor->full_name()] = DescriptorHolder(inputDescriptor, true /*Inout*/, false/*Output*/);
				}
				else
				{
					descriptorHolder.isRequest = true;
					(*msgMap) [ inputDescriptor->full_name()] = descriptorHolder;
				}
			}
		}
		//Now handle output
		if(0 != outputDescriptor->field_count())
		{
			std::map <std::string, DescriptorHolder>* msgMap = fileAndDescriptorMap[GetFileNameFromFileDescriptor(outputDescriptor->file())];
		if(0 == msgMap)
		{
			fileAndDescriptorMap[GetFileNameFromFileDescriptor(outputDescriptor->file())] = msgMap = new std::map <std::string, DescriptorHolder >;
			(*msgMap) [outputDescriptor->full_name()] = DescriptorHolder(outputDescriptor, false/*Input*/, true/*Output*/);
		}
		else
		{
			DescriptorHolder descriptorHolder = (*msgMap) [outputDescriptor->full_name()];
			if(0 == descriptorHolder.descriptor)
			{
				(*msgMap)[outputDescriptor->full_name()] = DescriptorHolder(outputDescriptor, false /*Inout*/, true/*Ouput*/);
			}
			else
			{
				descriptorHolder.isResponse = true;
				(*msgMap)[outputDescriptor->full_name()] = descriptorHolder;
			}
		}
	}
	}
}

	//Now iterate over fildescriptorMap and process one file at a time
	for(fileAndDescriptorMapItr = fileAndDescriptorMap.begin(); fileAndDescriptorMapItr != fileAndDescriptorMap.end(); fileAndDescriptorMapItr++)
	{
		std::string strMappingModelFileName = fileAndDescriptorMapItr->first + "_" + MAPPING_MODEL_SUFFIX + ".proto";
		
		//create an object of the DynamicMessagefactory
		protobuf::DescriptorPool mappingDescriptorPool;
		protobuf::FileDescriptorProto mappingFileDescriptorProto;
		if(!OpenProto(strMappingModelFileName.c_str(), GetMappingModelFilePath(), mappingFileDescriptorProto, mappingDescriptorPool))
		{
			std::string warning = std::string("OpenProto failed for: ") + strMappingModelFileName + " Skipping - Assuming no transformation required";
			cout << warning << std::endl;
			continue; // this file does not need generation
		}
		//Pool is ready, lets create a factory
		protobuf::DynamicMessageFactory factory(&mappingDescriptorPool);
		std::string strOutputFileName = fileAndDescriptorMapItr->first + "_MappingTemplateOutput.cpp";
		scoped_ptr<io::ZeroCopyOutputStream> outputFileHandle(output_directory->Open(strOutputFileName));
		io::Printer printer(outputFileHandle.get(), '`');
		
		//Now loop and process all message in this file (stored in set)
		std::map < std::string, DescriptorHolder>* msgMap = fileAndDescriptorMapItr->second;
		for(msgMapItr = msgMap->begin(); msgMapItr != msgMap->end(); msgMapItr++)
		{
			const Descriptor &messageDescriptor = *(msgMapItr->second.descriptor);
			const Descriptor &mappingMessageDescriptor = *(mappingDescriptorPool.FindMessageTypeByName (messageDescriptor.full_name() +MAPPING_MESSAGE_SUFFIX));
			//use the mappingMessageDescriptor to dynamically, craete a new object through the DynamicMessageFactory
			protobuf::Message *mappingMessage = factory.GetPrototype(&mappingMessageDescriptor)->New();
			//create message specific reflection object
			const protobuf::Message::Reflection *mappingMessageReflection = mappingMessage->GetReflection();
			LoadMappingInMessage(mappingMessage, mappingMessageDescriptor);
			//Now we have all the messageDescriptor or PrintInputMessage to Print mapped Transformation
			if(true == msgMapItr->second.isRequest)//this is inout
			{
				PrintInputMessage(messageDescriptor, printer, mappingMessage, mappingMessageReflection, mappingMessageDescriptor);
			}
			else if(true == msgMapItr->second.isResponse)// this is ouptu message
			{
				PrintOutputMessage(messageDescriptor, printer, mappingMessage, mappingMessageReflection, mappingMessageDescriptor);
			}
		}
	}
	return true;
}

int main(int argc, char* argv[])
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	CppMappingGenTemplate generator;
	return PluginMain(argc, argv, &generator);
}

