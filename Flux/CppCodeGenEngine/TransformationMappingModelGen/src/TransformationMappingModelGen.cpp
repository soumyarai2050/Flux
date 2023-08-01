/**
 * Protocol Buffer Class Standard POCO Compatibility Generator Plugin
 *
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

class TransformationMappingModelGen: public FluxCodeGenerator
{
	public:
		void PrintField (io::Printer &printer,const FieldDescriptor &field,
						std::map<std::string, std::string> & fieldAttributeMap) const;
		void PrintEnum (const EnumDescriptor & enumDescriptor, io::Printer & printer) const;
		void PrintMessage (const Descriptor & messageDescriptor, io::Printer & printer) const;
		void PrintMessages (const FileDescriptor & fileDescriptor, io::Printer & printer) const;

		TransformationMappingModelGen() {}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
		void ValidateMessage(const Descriptor & messageDescriptor, io::Printer & printer) const;
};

void TransformationMappingModelGen::PrintField (io::Printer &printer, const FieldDescriptor &field, std::map<std::string, std::string> & fieldAttributeMap) const
{
	printer.Print(fieldAttributeMap, "optional `unqualified_type` `field_name`_attr = `field_ordinal`[(FluxFldMappingSrcType) = \"`src_type`\"];\n");
}

void TransformationMappingModelGen::PrintMessage(const Descriptor & messageDescriptor, io::Printer & printer) const
{
	//4.1 For each field in the Message:
	// - Iterate over all fields we have in this message
	// - In each iteration Find field's Name, its DataType and populate attribute map (create new attrbute map in each iteration)
	// - 
	//4.1
	//iterate over all fields we have and call Printfield to do the job
	ValidateMessage(messageDescriptor, printer);
	map<string, string>vars;

	vars["name"] = messageDescriptor.name();
	printer.Print(vars, "message `name`Mapping\n");
	printer.Print("{\n");
	{
		Indentation a(printer);
		for(int i=0; i<messageDescriptor.field_count(); ++i)
		{
			std::map<std::string, std::string> fieldAttributeMap;
			const FieldDescriptor &field( *messageDescriptor.field(i));
			char fldNumber[10];
			sprintf(fldNumber, "%d",field.number());
			fieldAttributeMap["field_ordinal"] = fldNumber;
			fieldAttributeMap["field_name"] = field.name();
			std::string mappingAttribute = getenv("MAPPING_ATTRIBUTE")?getenv("MAPPING_ATTRIBUTE"):"Attribute";
			//If field is of a complex type or enum type, we need unqualified_type name along with qualified_cpp_type name for the field
			if(ProtoCppDataType(field) == "enum")
			{
				fieldAttributeMap["src_type"] = (*field.enum_type()).name();
				fieldAttributeMap["unqualified_type"] = std::string("flux.attribute.") + mappingAttribute;
			}
			else if(ProtoCppDataType(field) == "message")
			{
				fieldAttributeMap["src_type"] = (*field.message_type()).name();
				fieldAttributeMap["unqualified_type"] = (*field.message_type()).name() + "Mapping";
			}
			else
			{
				fieldAttributeMap["src_type"] = ProtoCppDataType(field);
				fieldAttributeMap["unqualified_type"] = std::string("flux.attribute.") + mappingAttribute;
			}
			
			PrintField(printer, field, fieldAttributeMap);
		}
	}
	printer.Print(vars, "}\n");
}

void TransformationMappingModelGen::ValidateMessage(const Descriptor & messageDescriptor, io::Printer & printer) const
{
	int fieldCount = messageDescriptor.field_count();
	for(int j=0; j<fieldCount; j++)
	{
		if((*messageDescriptor.field(j)).type() == FieldDescriptor::TYPE_GROUP)
		{
			printer.Print("Groups not supported as field type. Exiting...");
			exit(1); 
		}
	}
}

void TransformationMappingModelGen::PrintEnum (const EnumDescriptor & enumDescriptor, io::Printer & printer) const
{
	//6.a For each Repeat Complex or Simple TypeType data member
	// - Generate "ReturnObjectPointer* GetMessag()" methods with their implementation calling equivalent non-std accessor
	// - Generate "void SetMessage(InputObject* ptrObject)" method with its implementation calling equivalent non-std accessor

	//Now generate code for all fields in this message
	// iterate over all fields we have and call PrintField to do the Job
	/* std::map<std::string, std::string> enumAttributeMap;
	for(int i = 0; i < enumDescriptor.value_count(); ++i)
	{
		const EnumValueDescriptor & enumValueDescriptor(*enumDescriptor.value(i));
		enumAttributeMap["enum_value_name"] = enumValueDescriptor.name();
		//This is an enum value, handle here
		printer.Print(enumAttributeMap, "enum_value_name: `enum_value_name`\n");
	}*/
}

void TransformationMappingModelGen::PrintMessages (const FileDescriptor & fileDescriptor, io::Printer & printer) const
{
	//Steps:
	//4. For each message (same as class) in input model (.proto file you run the plugin with)
	// - Print Message's Un-Qualified and Qualified Name
	// - Indent by one level
	// - Call PrintMessage with Message Descriptor and Printer
	// - Outdent back
	//5. For each Enum Type member in input model (.proto file you run the plugin with)
	// - Print Enum's Unqualified and Qualified Name
	// Indent by one level
	// - Call PrintEnum with Enum Descriptor and Printer
	// - Outdent back

	// Step 4.
	for(int i=0; i<fileDescriptor.message_type_count(); ++i)
	{
		const Descriptor &messageDescriptor(*fileDescriptor.message_type(i));
		Indentation a(printer);
		PrintMessage(messageDescriptor, printer);
	}
	// Step 5.
}

bool TransformationMappingModelGen::Generate(const FileDescriptor* file, const std::string & parameter, OutputDirectory* output_directory, std::string* error) const
{
	//Steps:
	//0. Create a file name string with name that you want the output file to have
	//1. Open output file for writing
	//2. Create a Printer object attached with file we pened above
	//3. Print import for each import in src proto
	//4. Call Print Messages with FileDescriptor reference and Printer reference

	//Step 0. 
	std::string strOutputFileName = GetFileNameFromFileDescriptor(file) + "_Mapping.proto";
	//Step 1.
	scoped_ptr<io::ZeroCopyOutputStream> outputFileHandle(output_directory->Open(strOutputFileName));
	//Step 2.
	io::Printer printer(outputFileHandle.get(), '`');
	//Step 3.
	std::set < const FileDescriptor * > importedProtoFiles;
	std::string mappingAttribute = getenv("MAPPING_ATTRIBUTE")?getenv("MAPPING_ATTRIBUTE"):"Attribute";
	printer.Print("import \"`mapping_attribute`.proto\";\n", "mapping_attribute", mappingAttribute);
	printer.Print("import \"flux_options.proto\";\n");
	//Collect all imported proto file descriptors
	for(int i=0; i<file->dependency_count(); ++i)
	{
		const FileDescriptor *import = file->dependency(i);
		if(string::npos == import->name().find("descriptor.proto") && string::npos == import->name().find("flux_options.proto")) //TODO list other possible names here to avoid errors
		{
			importedProtoFiles.insert(import);
		}
	}
	std::map<std::string, std::string> vars;
	for (std::set<const FileDescriptor *>::iterator iter = importedProtoFiles.begin(); iter!=importedProtoFiles.end(); iter++)
	{
		const FileDescriptor *import = *iter;
		string importFile = GetFileNameFromFileDescriptor(import) + "_Mapping.proto";
		vars["importFile"] = importFile;
		printer.Print(vars, "import \"`importFile`\";\n");
	}
	printer.Print("\n");
	PrintMessages(*file, printer);
	return true;
}

int main(int argc, char* argv[])
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	TransformationMappingModelGen generator;
	return PluginMain(argc, argv, &generator);
}

