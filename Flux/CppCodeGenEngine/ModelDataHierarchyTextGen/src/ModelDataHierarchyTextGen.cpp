/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class ModelDataHierarchyTextGen: public FluxCodeGenerator 
{
	protected:
		void PrintMessage   (io::Printer &printer, const Descriptor & message) const;
		void PrintComplexMessage   (io::Printer &printer, const Descriptor & message, 
										const std::string& prefix, bool isGetter = true) const;
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
	public:
		ModelDataHierarchyTextGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};



void ModelDataHierarchyTextGen::PrintComplexMessage(io::Printer &printer, const Descriptor & message, 
													const std::string &prefix, bool isGetter) const 
{
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		const FieldDescriptor &field ( *message.field(i) );

		map<std::string, std::string> variables;
		variables["name"]             = VariableName(field);
		variables["capitalized_name"] = UnderscoresToCapitalizedCamelCase(field);
		variables["actual_name"] 	  = UnderscoresToCamelCase(field);
		variables["default"]          = DefaultValueAsString(field);
		variables["comment"]          = field.DebugString();
		variables["prefix"]      	  = prefix;
		variables["actual_types"]     = CppDataType(field);

		if (field.type() == FieldDescriptor::TYPE_GROUP) 
		{
			size_t p = variables["comment"].find ('{');
			if (p != std::string::npos)
				variables["comment"].resize (p - 1);
		}
		
		switch (field.type()) 
		{
			case FieldDescriptor::TYPE_MESSAGE:
			case FieldDescriptor::TYPE_GROUP:
				variables["type"] = QualifiedCppClassOrEnumName(*field.message_type()) + " ";
				isComplex = true;
				break;
			default:
				variables["type"] = "";
		}

		if (field.is_repeated()) 
		{
			// Repeated field
			if(isComplex)
			{
				printer.Print(variables,"repeated `capitalized_name`\n");
				printer.Indent();
				PrintComplexMessage(printer,*field.message_type(),"");
				printer.Outdent();
			}
			else
			{
				printer.Print(variables,"repeated `actual_types` `capitalized_name`\n");
			}
		} 
		else 
		{
			// Non repeated field
			if(isComplex)
			{
				printer.Print(variables,"`capitalized_name`\n");
				printer.Indent();
				PrintComplexMessage(printer,*field.message_type(),"");
				printer.Outdent();
			}
			else
			{
				printer.Print(variables,"`actual_types` `capitalized_name`\n");
			}
		}
	}
}


void ModelDataHierarchyTextGen::PrintMessage(io::Printer &printer, const Descriptor & message) const 
{
	printer.Indent();
	printer.Print("`name`\n", "name", UnqualifiedClassOrEnumOrFieldName(message));
	printer.Indent();
	PrintComplexMessage(printer,message,"",false);
	printer.Outdent();
	printer.Outdent();
}

void ModelDataHierarchyTextGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		PrintMessage(printer, *file.message_type(i));
	}
}


bool ModelDataHierarchyTextGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	std::string output_filename = "../temp/"+ file->name() + "_hierarchy.txt";

	// Generate main file.
	scoped_ptr<io::ZeroCopyOutputStream> output(
		output_directory->Open(output_filename)
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


int main(int argc, char* argv[]) 
{
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	ModelDataHierarchyTextGen generator;
	return PluginMain(argc, argv, &generator);
}
