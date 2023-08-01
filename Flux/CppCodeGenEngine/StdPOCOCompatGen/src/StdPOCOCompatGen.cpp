/**
 * Protocol Buffer Class Standard POCO Compatibility Generator Plugin
 * 
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <FluxFileUtil.h>

class StdPOCOCompatGen: public FluxCodeGenerator 
{
	public:
		void PrintField   (io::Printer &printer, const FieldDescriptor &field) const;
		void PrintMessage   (const Descriptor & message, OutputDirectory* output_director, std::string output_filenamey) const;
		void PrintMessages  (const FileDescriptor & file, OutputDirectory* output_directory) const;
		bool HasDateTime (const FileDescriptor & file)const;
		
		StdPOCOCompatGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void StdPOCOCompatGen::PrintField	(io::Printer &printer, const FieldDescriptor &field) const
{
	map<std::string, std::string> variables;

	//Fill the map with all that is needed
	variables["name"]                = field.name();
	variables["accessor_name"]       = ProtoCppVariableAccessorName(field);
	variables["capitalized_name"]    = UnderscoresToCapitalizedCamelCase(field);
	variables["default"]             = DefaultValueAsString(field);
	variables["comment"]             = field.DebugString();
	variables["cpp_type"]            = CppDataType(field);

	bool isComplex = false;
	switch (field.type()) 
	{
		case FieldDescriptor::TYPE_MESSAGE:
		case FieldDescriptor::TYPE_GROUP:
			variables["TypeName"] = (*field.message_type()).name();
			variables["qualified_type_name"] = QualifiedCppClassOrEnumName(*field.message_type()) + " ";
			isComplex = true;
			break;
		case FieldDescriptor::TYPE_ENUM:
			variables["cpp_type"] = QualifiedCppClassOrEnumName(*field.enum_type());
			break;
		default:
			variables["type"] = "";
	}

	if (field.is_repeated()) 
	{
		// Repeated field
		//Complex or Simple these 2 methods are same
		//Print GetLength method:
		printer.Print(variables,"size_t Get`capitalized_name`Length() const ");//No newline on purpose, this is one line method
		printer.Print(variables,"{ return `accessor_name`_size(); }\n");
		//Print IsObjectSet method
		printer.Print(variables, "void Is`capitalized_name`Set()\n");
		printer.Print(variables, "{ return (0 != `accessor_name`_size()? true: false; }\n");

		if(isComplex)
		{
			//Print Get Method
			printer.Print(variables,"`cpp_type`* Get`capitalized_name`(int index)");//No newline on purpose, this is one line method
			printer.Print(variables,"{ return mutable_`accessor_name`(index); }\n");
			//Print Set Methods
			printer.Print(variables,"void set`capitalized_name`(int index, `qualified_type_name`* value)\n");
			printer.Print("{\n");
			printer.Indent();
				printer.Print(variables,"if(index < `accessor_name`_size())\n");
				printer.Print("{\n");
				printer.Indent();
					printer.Print(variables,"::google::protobuf::RepeatedPtrField< `qualified_type_name` >* `name`_ = mutable_`accessor_name`();\n");
					printer.Print(variables,"`name`_->AddAllocated(value);\n");
					printer.Print(variables,"`name`_->SwapElements(index, `accessor_name`_size()-1);\n");
					printer.Print("RemoveLast();\n");
				printer.Outdent();
				printer.Print("}\n");
				printer.Print("else\n");
				printer.Print("{\n");
				printer.Indent();
					printer.Print("throw \"invalid index passed!!\";\n");
				printer.Outdent();
				printer.Print("}\n");
			printer.Outdent();
			printer.Print("}\n");

			//Print Add Method
			printer.Print(variables,"void Add`capitalized_name`(`qualified_type_name`* value)\n");
			printer.Print("{\n");
			printer.Indent();
				printer.Print(variables,"::google::protobuf::RepeatedPtrField< `qualified_type_name` >* `name`_ = mutable_`accessor_name`();\n");
				printer.Print(variables,"`name`_->AddAllocated(value);\n");
			printer.Outdent();
			printer.Print("}\n");
		}
		else
		{
			//Repeated but not complex
			//Print Get Method
			printer.Print(variables,"`cpp_type` Get`capitalized_name`(int index)");//No newline on purpose, this is one line method
			printer.Print(variables,"{ return mutable_`accessor_name`(index); }\n");
			//Print Set Methods
			printer.Print(variables,"void set`capitalized_name`(int index, `qualified_type_name` value)\n");
			printer.Print("{\n");
			printer.Indent();
				printer.Print(variables,"if(index < `accessor_name`_size())\n");
				printer.Print("{\n");
				printer.Indent();
					printer.Print(variables,"mutable_`accessor_name`(index) = value;\n");
				printer.Outdent();
				printer.Print("}\n");
				printer.Print("else\n");
				printer.Print("{\n");
				printer.Indent();
					printer.Print("throw \"invalid index passed!!\";\n");
				printer.Outdent();
				printer.Print("}\n");
			printer.Outdent();
			printer.Print("}\n");
			//Print Add Method
			printer.Print(variables,"void Add`capitalized_name`(`cpp_type` value)");//No newline on purpose, this is one line method
			printer.Print(variables,"{ /*TODO - This needs to be implemented*/ }\n");
		}
	}
	else 
	{
		// Non repeated field
		//Complex or Simple this method is common
		//Print IsSet method
		printer.Print(variables, "void Is`capitalized_name`Set()\n");
		printer.Print(variables, "{ return has_`name`(); }\n");

		if(isComplex)
		{
			//Print Set Method
			printer.Print(variables,"void Set`capitalized_name`(`qualified_type_name`* value) { /* NOP */ }\n");
			//Print Get Method
			printer.Print(variables,"`qualified_type_name`* Get`capitalized_name`() const ");//No newline on purpose, this is one line method
			printer.Print(variables,"{ return mutable_`accessor_name`(); }\n");
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
					//GetDefault
					printer.Print(variables,"static const char * GetDefault`capitalized_name`() { return \"\"; }\n");
					//Get
					printer.Print(variables,"static const char * Get`capitalized_name`() { return `accessor_name`().c_str(); }\n");
					//Set
					printer.Print(variables,"void Set`capitalized_name`(const char * value) { *(mutable_`accessor_name`()) = value; }\n");
					break;
				case FieldDescriptor::TYPE_ENUM:
					//GetDefault
					printer.Print(variables,"static `cpp_type` GetDefault`capitalized_name`()");//No newline on purpose, this is one line method
					printer.Print(variables,"{ return (`cpp_type`)0; }\n");
					//Get
					printer.Print(variables,"`cpp_type` Get`capitalized_name`()const { return `accessor_name`(); }\n");
					//Set
					printer.Print(variables,"void Set`capitalized_name`(`cpp_type` value)const { set_`accessor_name`(value); }\n");
					break;
				case FieldDescriptor::TYPE_INT64:
				{
					//Get Default
					//An int64 can or can not be a date time. If its a datetime field, it should have FluxFldValDateTime option set
					std::string strFluxFldTestVal=field.options().GetExtension(FluxFldValDateTime);
					if(0 != strFluxFldTestVal.length())
					{
						//This is a date time field, handle it like that - we would have imported time-support already
						printer.Print(variables,"static timeval GetDefault`capitalized_name`() { return Time::GetDefaultTime(); }\n");
					}//No else required, just fall through to the default, this is a regular field
					//Get Method
					printer.Print(variables,"timeval Get`capitalized_name`()const\n");
					printer.Print("{\n");
					printer.Indent();
						printer.Print(variables,"{ /*TODO - This needs to be implemented for now return default*/ return GetDefault`capitalized_name`();}\n");
					printer.Outdent();
					printer.Print("}\n");
					//Set Method
					printer.Print(variables,"void Set`capitalized_name`(timeval value)const\n");
					printer.Print("{\n");
					printer.Indent();
						printer.Print(variables,"{ /*TODO - This needs to be implemented for now NOP*/ }\n");
					printer.Outdent();
					printer.Print("}\n");
				}
				default:
					//GetDefault
					printer.Print(variables,"static `cpp_type` GetDefault`capitalized_name`() { return 0; }\n");
					//Get
					printer.Print(variables,"`cpp_type` Get`capitalized_name`()const { return `accessor_name`(); }\n");
					//Set
					printer.Print(variables,"void Set`capitalized_name`(`cpp_type` value)const { set_`accessor_name`(value); }\n");
			}
		}
	}
}

void StdPOCOCompatGen::PrintMessage   (const Descriptor & message, OutputDirectory* output_directory, std::string output_filename) const
{
	//Create Dynamic Insert Point String for this message
	std::string strInsertPointName = std::string("class_scope:") + message.full_name() ;
	//open with file with dynamic insert point
	scoped_ptr<io::ZeroCopyOutputStream> output(
		output_directory->OpenForInsert(output_filename,strInsertPointName)
	);
	
	io::Printer printer(output.get(), '`');
	//Now we have all we need lets generate code for this message
	printer.Print("//Class Specific Members:\n");
	printer.Print("const char* GetUriForMessage() { return `MessageName`::GetUri(); }\n", "MessageName", message.name());
	printer.Print("static const char* GetUri() { return \"`MessageURI`\"; }\n", "MessageURI", GetMessageURI(message));

	
	//Now generate code for all fields in this message 
	//iterate over all fields we have and call PrintField to do the Job
	for (int i = 0; i < message.field_count(); ++i) 
	{
		const FieldDescriptor &field ( *message.field(i) );
		printer.Print("\n//`comment`", "comment", field.DebugString());
		PrintField(printer, field);
	}
}

void StdPOCOCompatGen::PrintMessages	(const FileDescriptor & file, OutputDirectory* output_directory) const
{
	//Steps:
	//0. Find iif DateTime option is set on any int64 field, if yes then open file for insert at include section and include timesupport.h
	//1. Iterate through all messages in the file
	//2. Open input file for each mesage within input file with class insertion point
	//3. For each simple type data member generate: 
	//    - "static ReturnObject GetDefaultMessage()" method with its implementaiton calling equivalent non-std accessor
	//    - "ReturnObject GetMessage()" method with its implementaiton calling equivalent non-std accessor
	//    - "void SetMessage(InputObject variableName)" method with its implementaiton calling equivalent non-std accessor
	//4. For each complex type data member:
	//    - Generate "ReturnObjectPointer* GetMessag()" methods with their implementaiton calling equivalent non-std accessor
	//    - Generate "void SetMessage(InputObject* ptrObject)" method with its implementaiton as NOP
	//5. For each Repeat Complex or Simple TypeType data member
	//    - Generate "ReturnObjectPointer* GetMessag()" methods with their implementaiton calling equivalent non-std accessor
	//    - Generate "void SetMessage(InputObject* ptrObject)" method with its implementaiton calling equivalent non-std accessor

	std::string output_filename = GetFileNameFromFileDescriptor(&file) + ".pb.h";//Default Proto Generated File, for all insertions, we will open and cloe this file

	if(HasDateTime(file))
	{
		//Since date time is present, we need to include timesupport.h
		//Create Dynamic Insert Point String for this message
		std::string strInsertPointName = std::string("includes");
		//open with file with dynamic insert point
		scoped_ptr<io::ZeroCopyOutputStream> output(
			output_directory->OpenForInsert(output_filename,strInsertPointName)
		);
		io::Printer printer(output.get(), '`');
		printer.Print("#include \"timesupport.h\"\n");
	}
	// File exists, now we can start step 1
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		PrintMessage(*file.message_type(i), output_directory, output_filename);
	}
}

bool StdPOCOCompatGen::HasDateTime(const FileDescriptor & file)const
{
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		const Descriptor & message = *file.message_type(i);
		for (int j = 0; j < message.field_count(); ++j) 
		{
			const FieldDescriptor &field ( *message.field(j) );
			std::string strFluxFldTestVal=field.options().GetExtension(FluxFldValDateTime);
			if(0 != strFluxFldTestVal.length())
			{
				//This has a DateTime
				return true;
			}
		}
	}
	return false;
}

bool StdPOCOCompatGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

	//Principals: 
	//1. Do not use any Private members directly, private members in code gen
	//2. Private Members are subject to change
	//3. Accessor are guranteed not to break

	//Start Code generation
	PrintMessages(*file, output_directory);
	return true;
}

int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	StdPOCOCompatGen generator;
	return PluginMain(argc, argv, &generator);
}
