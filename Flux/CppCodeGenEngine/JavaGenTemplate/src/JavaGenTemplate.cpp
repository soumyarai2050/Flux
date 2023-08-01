/**
 * Protocol Buffer Class Standard POCO Compatibility Generator Plugin
 * 
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <FluxFileUtil.h>

class JavaGenTemplate: public FluxCodeGenerator 
{
	public:
		void PrintField	(io::Printer &printer, const FieldDescriptor &field, 
						 std::map<std::string, std::string> & fieldAttributeMap) const;
		void PrintEnum   (const EnumDescriptor & enumDescriptor, io::Printer & printer) const;
		void PrintMessage   (const Descriptor & messageDescriptor, io::Printer & printer) const;
		void PrintMessages	(const FileDescriptor & fileDescriptor, io::Printer & printer) const;
		
		JavaGenTemplate(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void JavaGenTemplate::PrintField	(io::Printer &printer, const FieldDescriptor &field, 
										 std::map<std::string, std::string> & fieldAttributeMap) const
{
	bool isComplex = false;
	if (FieldDescriptor::TYPE_MESSAGE == field.type()) 
	{
		isComplex = true;
	}

	if (field.is_repeated()) 
	{
		if(isComplex)
		{
			printer.Print("This is a Repeated Complex Type field:\n");
			printer.Indent();
				printer.Print(fieldAttributeMap,"field_name: `field_name`\n");
				printer.Print(fieldAttributeMap,"unqualified_type: `unqualified_type`\n");
				printer.Print(fieldAttributeMap,"qualified_java_type: `qualified_java_type`\n");
			printer.Outdent();
		}
		else
		{
			printer.Print("This is a Repeated Simple Type field:\n");
			printer.Indent();
				printer.Print(fieldAttributeMap,"field_name: `field_name`\n");
				printer.Print(fieldAttributeMap,"qualified_java_type: `qualified_java_type`\n");
			printer.Outdent();			
		}
	}
	else 
	{
		// Non repeated field
		if(isComplex)
		{
			printer.Print("This is a Complex Type field:\n");
			printer.Indent();
				printer.Print(fieldAttributeMap,"field_name: `field_name`\n");
				printer.Print(fieldAttributeMap,"unqualified_type: `unqualified_type`\n");
				printer.Print(fieldAttributeMap,"qualified_java_type: `qualified_java_type`\n");
			printer.Outdent();
		}
		else
		{
			//Within simple type we have 4 cases to handle 
			//Strings
			//Enums
			//Rest of It
			//DateTime (Protobuf representation is long)
			/* Default Values - Handeling Strings*/
			switch(field.type())
			{
				case FieldDescriptor::TYPE_STRING:
					{
						printer.Print("This is a String Type field:\n");
						printer.Indent();
							printer.Print(fieldAttributeMap,"field_name: `field_name`\n");
							printer.Print(fieldAttributeMap,"qualified_java_type: `qualified_java_type`\n");
						printer.Outdent();			
					}
					break;
				case FieldDescriptor::TYPE_ENUM:
					{
						printer.Print("This is a Enum Type field:\n");
						printer.Indent();
							printer.Print(fieldAttributeMap,"field_name: `field_name`\n");
							printer.Print(fieldAttributeMap,"unqualified_type: `unqualified_type`\n");
							printer.Print(fieldAttributeMap,"qualified_java_type: `qualified_java_type`\n");
						printer.Outdent();
					}
					break;
				case FieldDescriptor::TYPE_INT64:
				{
					//Get Default
					//An int64 can or can not be a date time. If its a datetime field, it should have FluxFldValDateTime option set
					std::string strFluxFldTestVal=field.options().GetExtension(FluxFldValDateTime);
					if(0 != strFluxFldTestVal.length())
					{
						//This is a date time field, handle it like that - we should have imported time-support already
					}
					else
					{
						//This is a int64 simple type field handle here
						printer.Print("This is a Int64 Type field:\n");
						printer.Indent();
							printer.Print(fieldAttributeMap,"field_name: `field_name`\n");
							printer.Print(fieldAttributeMap,"qualified_java_type: `qualified_java_type`\n");
						printer.Outdent();			
					}
					break;
				}
				default:
					//All other simple types falll in this case handle here
					{
						//This is any other simple type field, handle here
						printer.Print("This is a Simple Type field:\n");
						printer.Indent();
							printer.Print(fieldAttributeMap,"field_name: `field_name`\n");
							printer.Print(fieldAttributeMap,"qualified_java_type: `qualified_java_type`\n");
						printer.Outdent();			
					}
			}
		}
	}
}


void JavaGenTemplate::PrintMessage   (const Descriptor & messageDescriptor, io::Printer & printer) const
{
	//4.1 For each field in the Message:
	//    - Iterate over all fields we have in this message
	//    - In each iteration Find field's Name, its DataType and populate attribute map (create new attribute map in each iteration)
	//    - 

	//4.1
	//iterate over all fields we have and call PrintField to do the Job
	for (int i = 0; i < messageDescriptor.field_count(); ++i) 
	{
		std::map<std::string, std::string> fieldAttributeMap;
		const FieldDescriptor &field ( *messageDescriptor.field(i) );

		fieldAttributeMap["field_name"] = VariableName(field);
		//If field is of a complex type or enum type, we need unqualified_type name along with qualified_java_type name for the field 
		if(field.type() == FieldDescriptor::TYPE_MESSAGE)
		{
			//This field is a complex type, it has an un-qualified type name as well
			fieldAttributeMap["unqualified_type"] = (*field.message_type()).name();
		}
		else if(field.type() == FieldDescriptor::TYPE_ENUM)
		{
			//This field is a enum type, it has an un-qualified type name as well
			fieldAttributeMap["unqualified_type"] = (*field.enum_type()).name();
		}
		//Both simple and complex type have Qualified Type Name
		fieldAttributeMap["qualified_java_type"] = QualifiedJavaTypeNameForField(field);
		
		PrintField(printer, field, fieldAttributeMap);
	}
}

void JavaGenTemplate::PrintEnum   (const EnumDescriptor & enumDescriptor, io::Printer & printer) const
{
	//6.a. For each Repeat Complex or Simple TypeType data member
	//    - Generate "ReturnObjectPointer* GetMessag()" methods with their implementaiton calling equivalent non-std accessor
	//    - Generate "void SetMessage(InputObject* ptrObject)" method with its implementaiton calling equivalent non-std accessor

	//Now generate code for all fields in this message 
	//iterate over all fields we have and call PrintField to do the Job
	std::map<std::string, std::string> enumAttributeMap;
	for (int i = 0; i < enumDescriptor.value_count(); ++i) 
	{
		 const EnumValueDescriptor & enumValueDescriptor(*enumDescriptor.value(i));	  
		 enumAttributeMap["enum_value_name"] = enumValueDescriptor.name();
		 //This is an enum value, handle here
		 printer.Print(enumAttributeMap,"enum_value_name: `enum_value_name`\n");
	}
}


void JavaGenTemplate::PrintMessages	(const FileDescriptor & fileDescriptor, io::Printer & printer) const
{
	//Steps:
	//4. For each message (same as class) in input model (.proto file you run the plugin with)
	//    - Print Message's Un-Qualified and Qualified Name 
	//    - Indent by one level
	//    - Call PrintMessage with Message Descriptor and Printer
	//	- Outdent back
	//5. For each Enum Type member in input model (.proto file you run the plugin with)
	//    - Print Enum's Un-Qualified and Qualified Name 
	//    - Indent by one level
	//    - Call PrintEnum with Enum Descriptor and Printer
	//	- Outdent back

	//Step 4.
	for (int i = 0; i < fileDescriptor.message_type_count(); ++i) 
	{
		const Descriptor &messageDescriptor(*fileDescriptor.message_type(i));
		printer.Print("We are handeling a class type:\n");
		printer.Indent();
		printer.Print("unqualified_name: `unqualified_name`\n", "unqualified_name", messageDescriptor.name());
		printer.Print("qualified_java_name: `qualified_java_name`\n", "qualified_java_name", QualifiedJavaClassOrEnumName(messageDescriptor));
		printer.Indent();
		PrintMessage(messageDescriptor, printer);
		printer.Outdent();
		printer.Outdent();
	}

	//Step 5.
	for (int i = 0; i < fileDescriptor.enum_type_count(); ++i) 
	{
		const EnumDescriptor &enumDescriptor(*fileDescriptor.enum_type(i));
		printer.Print("We are handeling an enum type:\n");
		printer.Indent();
		printer.Print("unqualified_name: `unqualified_name`\n", "unqualified_name", enumDescriptor.name());
		printer.Print("qualified_java_name: `qualified_java_name`\n", "qualified_java_name", QualifiedJavaClassOrEnumName(enumDescriptor));
		printer.Indent();
		PrintEnum(enumDescriptor, printer);
		printer.Outdent();
		printer.Outdent();
	}
}


bool JavaGenTemplate::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	//Steps:
	//0. Create a file name string with name that you want the output file to have
	//1. Open output file for writing
	//2. Create a Printer object attached with file we pened above
	//3. Call Print Messages with FileDescriptor refrence and Printer refrence

	//Step 0.
	std::string strOutputFileName = GetFileNameFromFileDescriptor(file) + "_java.your_suffix";
	//Step 1.
	scoped_ptr<io::ZeroCopyOutputStream> outputFileHandle(output_directory->Open(strOutputFileName));
	//Step 2.	
	io::Printer printer(outputFileHandle.get(), '`');
	//Step 3.
	PrintMessages(*file, printer);
	return true;
}

int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	JavaGenTemplate generator;
	return PluginMain(argc, argv, &generator);
}
