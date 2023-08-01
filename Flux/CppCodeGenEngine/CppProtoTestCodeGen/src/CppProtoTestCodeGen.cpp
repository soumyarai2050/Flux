/**
 * Protocol Buffer CPP Test Code Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class CppProtoTestCodeGen : public FluxCodeGenerator {
	protected:

		void PrintMessage   (io::Printer &printer, const Descriptor & message) const;
		void PrintComplexMessage   (io::Printer &printer, const Descriptor & message, 
										const std::string& prefix, bool isGetter = true) const;
		
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
		std::string VariableGetterName(const FieldDescriptor & field) const;
		std::string VariableSetterName(const FieldDescriptor & field) const;

	public:

		CppProtoTestCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};



std::string CppProtoTestCodeGen::VariableGetterName(const FieldDescriptor & field) const {
	return (std::string("mutable_") +UnderscoresToCamelCase(field));
}

std::string CppProtoTestCodeGen::VariableSetterName(const FieldDescriptor & field) const {
	return (std::string("set_") +UnderscoresToCamelCase(field));
}

void CppProtoTestCodeGen::PrintComplexMessage(io::Printer &printer, const Descriptor & message, 
													const std::string &prefix, bool isGetter) const 
{	
	std::string counterVar = GetUniqueIdentifierName();
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		const FieldDescriptor &field ( *message.field(i) );
		std::string strFieldComment = field.options().GetExtension(FluxFldCmnt);
                if(0 != strFieldComment.length())
                        printer.Print("//`fieldComment`\n","fieldComment",strFieldComment);

		map<std::string, std::string> variables;
		variables["name"]             = VariableName(field);
		variables["capitalized_name"] = UnderscoresToCapitalizedCamelCase(field);
		variables["actual_name"] 	  = UnderscoresToCamelCase(field);
		variables["default"]          = DefaultValueAsString(field);
		variables["comment"]          = field.DebugString();
		variables["getter_name"]      = VariableGetterName(field);
		variables["setter_name"]      = VariableSetterName(field);
		variables["prefix"]      	  = prefix;
		variables["DummyVal"]		  = TestValueAsString(field,false);
		variables["counterVar"]		  = counterVar;

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

		if(isGetter && !isComplex && !(field.is_repeated()))
			printer.Print(variables,"std::cout << ");

		if (field.is_repeated()) 
		{
			// Repeated field
			printer.Print(variables,
				"\n// `comment`\n"
				"for (int `counterVar` = 0; `counterVar` < "
			);
			if (isGetter) 
			{
				printer.Print(variables,
				"`prefix``name`size(); `counterVar`++)\n{\n"
				);
			}
			else
			{
				printer.Print(variables,
				"4; i++)\n{\n"
				);
			}
			printer.Indent();
			if(isGetter && !isComplex)
				printer.Print(variables,"std::cout << ");
			if(isComplex)
			{
				if (isGetter) 
				{
					std::string childPrefix = prefix + VariableGetterName(field) + "(" + counterVar + ")->";
					PrintComplexMessage(printer,*field.message_type(),childPrefix,isGetter);
				}
				else
				{
					printer.Print(variables,
						"`type` *ptr`capitalized_name` = `prefix`add_`actual_name`();\n"
					);
					std::string prefix = std::string ("ptr") + UnderscoresToCapitalizedCamelCase(field) + "->";
					PrintComplexMessage(printer,*field.message_type(),prefix,isGetter);
				}
			}
			else
			{
				if (isGetter) 
					printer.Print(variables,"`prefix``getter_name`(`counterVar`)");
				else
					printer.Print(variables,"`prefix``setter_name`(`counterVar`, `DummyVal`);\n");
			}
			if(isGetter && !isComplex)
				printer.Print(variables," << std::endl;\n");
			printer.Outdent();
			printer.Print(variables,
				"}\n"
			);
		} 
		else 
		{
			// Non repeated field
			if(isComplex)
			{
				std::string childPrefix = prefix + VariableGetterName(field) + "()->";
				PrintComplexMessage(printer,*field.message_type(),childPrefix,isGetter);
			}
			else
			{
				if (isGetter) 
					printer.Print(variables,"`prefix``getter_name`()");
				else
					printer.Print(variables,"`prefix``setter_name`(`DummyVal`);\n");
			}
		}
		if(isGetter && !isComplex && !(field.is_repeated()))
			printer.Print(variables," << std::endl;\n");
	}
}


void CppProtoTestCodeGen::PrintMessage(io::Printer &printer, const Descriptor & message) const 
{
	printer.Print(
	"void Print`name`(`qualified_name` *ptr`name`)\n"
	"{\n",
		  "name", UnqualifiedClassOrEnumOrFieldName(message),
		  "qualified_name", QualifiedCppClassOrEnumName(message)
	);
	printer.Indent();

	std::string prefix = std::string ("ptr") + UnqualifiedClassOrEnumOrFieldName(message) + "->";
	PrintComplexMessage(printer,message,prefix);
	printer.Outdent();
	printer.Print(
	"}\n\n"
	);

	
	printer.Print(
	"`qualified_name`* Write`name`(void)\n"
	"{\n",
		  "name", UnqualifiedClassOrEnumOrFieldName(message),
		  "qualified_name", QualifiedCppClassOrEnumName(message)
	);
	printer.Indent();
	printer.Print("`qualified_name` *ptr`name` = new `qualified_name`();\n",
		  			  "name", UnqualifiedClassOrEnumOrFieldName(message),
		  			  "qualified_name", QualifiedCppClassOrEnumName(message)
	);
	PrintComplexMessage(printer,message,prefix,false);
	printer.Print(
	"return ptr`name`;\n",
		  "name", UnqualifiedClassOrEnumOrFieldName(message)
	);

	printer.Outdent();
	printer.Print(
	"}\n\n"
	);
}

void CppProtoTestCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {
	//Print any file comment here if present
	std::string strFileComment = file.options().GetExtension(FluxFileCmnt);
	if(0 != strFileComment.length())
		printer.Print("//`fileComment`\n","fileComment",strFileComment);
	for (int i = 0; i < file.message_type_count(); ++i) {
		//Print any message comment here if present
		std::string strMessageComment = (*file.message_type(i)).options().GetExtension(FluxMsgCmnt);
		if(0 != strMessageComment.length())
			printer.Print("//`messageComment`\n","messageComment",strMessageComment);
		PrintMessage(printer, *file.message_type(i));
	}
}


bool CppProtoTestCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

	std::string output_filename ( file->name() + "_test.cpp" );

	// Generate main file.
	scoped_ptr<io::ZeroCopyOutputStream> output(
		output_directory->Open(output_filename)
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
                sleep(30);
	CppProtoTestCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
