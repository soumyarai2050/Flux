/**
 *Protocol Buffer Class Standard POCO Compatibility Generator Plugin
 *
 *
*/

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

class TransformationMappingGen: public FluxCodeGenerator
{
	public:
		TransformationMappingGen() {}
		void PrintField (const FieldDescriptor &field, io::Printer &printer, std::string parent_srcType) const;
		void PrintInnerMessage (const Descriptor &messageDescriptor, io::Printer &printer, std::string parent_srcType = "") const;
		void PrintMessage (const Descriptor & messageDescriptor, OutputDirectory* output_directory) const;
		void PrintMessages (const FileDescriptor & fileDescriptor, OutputDirectory* output_directory) const;
		bool Generate (const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
		void ValidateMessage(const Descriptor &messageDescriptor, io::Printer & printer) const;
		std::string GetSourceFieldCppType(const FieldDescriptor &field) const
		{
			return field.options().GetExtension(FluxFldMappingSrcType);
			//return "FluxFldMappingSrcType";
		}
};

void TransformationMappingGen::PrintField(const FieldDescriptor &field, io::Printer &printer, std::string parentSourceType) const
{
	std::map<std::string, std::string> fieldAttributeMap;
	std::string fieldName = field.name();
	std::string sourceType = GetSourceFieldCppType(field);
	fieldAttributeMap["field_name"] = fieldName;
	fieldAttributeMap["source_type"] = sourceType;
	if(field.cpp_type() == FieldDescriptor::CPPTYPE_MESSAGE && field.is_repeated())
	{
		printer.Print(fieldAttributeMap,"`field_name` :\n{ \n");
		{
			Indentation a(printer);
			PrintInnerMessage(*(field.message_type()), printer, sourceType);
		}
		printer.Print("}\n");
	}
	else if(field.cpp_type() == FieldDescriptor::CPPTYPE_MESSAGE && ! field.is_repeated())
	{
		printer.Print(fieldAttributeMap,"`field_name`\n{\n");
		{
			Indentation a(printer);
			PrintInnerMessage(*(field.message_type()), printer, sourceType);
		}
		printer.Print("}\n");
	}
	else
	{
		if( fieldName == "source_type")
		{
			fieldAttributeMap["parent_source_type"] = parentSourceType;
			printer.Print(fieldAttributeMap, "`field_name` : \"`parent_source_type`\"\n");
		}
	}
}

void TransformationMappingGen::PrintInnerMessage(const Descriptor & messageDescriptor, io::Printer &printer, std::string parent_srcType) const
{
	ValidateMessage(messageDescriptor, printer);
	int fieldCount = messageDescriptor.field_count();
	// add fields
	for(int j=0; j<fieldCount; j++)
	{
		const FieldDescriptor &fieldDescriptor = *(messageDescriptor.field(j));
		PrintField(fieldDescriptor, printer, parent_srcType);
	}
}	

void TransformationMappingGen::ValidateMessage(const Descriptor & messageDescriptor, io::Printer & printer) const
{
	for(int j=0; j<messageDescriptor.field_count(); j++)
	{
		const FieldDescriptor &field ( *messageDescriptor.field(j));
		if(field.type() == FieldDescriptor::TYPE_GROUP)
		{
			printer.Print("Groups not supported as field type. Exiting...");
			exit(1);
		}
	}
}

void TransformationMappingGen::PrintMessage (const Descriptor & messageDescriptor, OutputDirectory* output_directory) const
{
	std::string strOutputFileName = messageDescriptor.name() + ".Mapping";
	//Open output file
	scoped_ptr<io::ZeroCopyOutputStream> outputFileHandle(output_directory->Open(strOutputFileName));
	io::Printer printer(outputFileHandle.get(), '`');
	PrintInnerMessage(messageDescriptor, printer);
}

void TransformationMappingGen::PrintMessages (const FileDescriptor & fileDescriptor, OutputDirectory* output_directory) const
{
	//Steps:
	//4. For each message (same as class) in input model (.proto file you run the plugin with)
	// - Print Message's Un-Qualified and Qualified Name
	// - Indent by one level
	// - Call PrintMessage with Message Descriptor and Printer
	// - Outdent back
	//5. For each Enum Type member in input model (.proto file you run the plugin with)
	// - Print Enum's Un-Qualified and Qualified Name
	// - Indent by one level
	// - Call PrintEnum with Enum Descriptor and Printer
	// - Outdent back

	//Step 4:
	for(int i=0; i<fileDescriptor.message_type_count(); ++i)
	{
		const Descriptor &messageDescriptor(*fileDescriptor.message_type(i));
		//if(IsServiceMessage(msgDesc))
		PrintMessage(messageDescriptor,output_directory);
	}
	//Step 5.
}

bool TransformationMappingGen::Generate(const FileDescriptor* fileDescriptor, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const
{
/*	std::map<std::string, std::set<std::pair<const Descriptor *, bool > >* > fileNameDescriptorMap;
	std::map<std::string, std::set <std::pair<const Descriptor *, bool> >* >::iterator fileNameDescriptorMapItr;

	std::set<std::pair<const Descriptor *, bool > > inputDescriptorSet;
	std::set<std::pair<const Descriptor *, bool> > outputDescriptorSet;
	std::set<std::pair<const Descriptor *, bool> >::iterator descriptorSetItr;
	
	for(int i = 0; i < fileDescriptor->service_count(); ++i)
	{
		const ServiceDescriptor *serviceDesc = fileDescriptor->service(i);
		for(int j = 0; j < serviceDesc->method_count(); ++j)
		{
			const Descriptor * inputDescriptor = serviceDesc->method(j)->input_type();
			const Descriptor * outputDescriptor = serviceDesc->method(j)->output_type();
			inputDescriptorSet.insert(make_pair(inputDescriptor, true));
			outputDescriptorSet.insert(make_pair(outputDescriptor, false));
			fileNameDescriptorMap[(GetFileNameFromFileDescriptor(inputDescriptor->file()))] = &inputDescriptorSet;
			fileNameDescriptorMap[(GetFileNameFromFileDescriptor(outputDescriptor->file()))] = &inputDescriptorSet;
		}
	}	
	//Now iterate over fileNameDescriptorMap and process one file at a time
	for(fileNameDescriptorMapItr = fileNameDescriptorMap.begin(); fileNameDescriptorMapItr != fileNameDescriptorMap.end(); fileNameDescriptorMapItr++)
	{
		std::string strMappingFileName = fileNameDescriptorMapItr->first + "_" + MAPPING_FILE_SUFFIX + ".proto";
		//Create an object of the DynamicMessageFactory
		protobuf::DescriptorPool mappingDescriptorPool;
		protobuf::FileDescriptorProto mappingFileDescriptorProto;
		if(!OpenProto(strMappingFileName.c_str(), mappingFileDescriptorProto, mappingDescriptorPool))
		{
			std::string warning = "OpenProto failed for: " + strMappingFileName + " Skipping - Assuming no transformation required";
			cout << warning << std::endl;
			continue; // This file does not need generation
		}
		//Pool is ready, lets create a factory
		protobuf::DynamicMessageFactory factory(&mappingDescriptorPool);
	
		//Now loop and process all messages in this file (stored in set)
		std::set < std::pair<const Descriptor *, bool > >* descriptorSet = fileNameDescriptorMapItr->second;
		for(descriptorSetItr = descriptorSet->begin(); descriptorSetItr != descriptorSet->end(); descriptorSetItr++)
		{
			const Descriptor &messageDescriptor = *(descriptorSetItr->first);
			const Descriptor &mappingMessageDescriptor = *(mappingDescriptorPool FindMessageTypeByName(messageDescriptor.full_name() + MAPPING_MESSAGE_SUFFIX));
			PrintMessage(mappingMessageDescriptor, output_directory);
		}
	} */
	PrintMessages(*fileDescriptor, output_directory);
	return true;
}

int main(int argc, char *argv[])
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	TransformationMappingGen generator;
	return PluginMain(argc, argv, &generator);
}

