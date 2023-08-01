/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-1
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class RevAjaxInterfaceCodeGen: public FluxCodeGenerator {
	protected:
               void PrintMessages(io::Printer &printer, const FileDescriptor & file) const;
               void PrintMessage(io::Printer &printer, const FileDescriptor & file,const Descriptor & message,std::string &file_name) const ;
               std::string VariableGetterName(const FieldDescriptor & field) const;
	public:

		RevAjaxInterfaceCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

std::string RevAjaxInterfaceCodeGen::VariableGetterName(const FieldDescriptor & field) const {
	return (std::string("get") + UnderscoresToCapitalizedCamelCase(field));
}

void RevAjaxInterfaceCodeGen::PrintMessage(io::Printer &printer, const FileDescriptor & file,const Descriptor & message,std::string &file_name) const 
{

	map<std::string,std::string> variables;
	variables["file_name"]=file_name;
	variables["object_name"]=UnderscoresToCamelCase(file_name);

	size_t p=QualifiedJavaClassOrEnumName(message).find_last_of('.');
	std::string actual_name=QualifiedJavaClassOrEnumName(message).substr(0,p);
	variables["ClassName"]=actual_name;
	variables["ReqsUnqualifiedClassOrEnumOrFieldName"]=UnqualifiedClassOrEnumOrFieldName(message);
	variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
	printer.Print("\n");
	std::string strResponse=ResponseNameCheckerAndGenerator(message);
	if(0 != strResponse.length())
	{
		variables["strResponse"]=strResponse;
		variables["response"]=UnderscoresToCamelCase(strResponse);
		for (int i = 0; i < file.message_type_count(); ++i) 
		{
			const Descriptor & newmessage(*file.message_type(i));
			if(UnqualifiedClassOrEnumOrFieldName(newmessage)==variables["strResponse"])
			{
				variables["UnqualifiedClassOrEnumOrFieldName"]=UnqualifiedClassOrEnumOrFieldName(newmessage);
				size_t pl=QualifiedJavaClassOrEnumName(newmessage).find_last_of('.');
				std::string actual_name=QualifiedJavaClassOrEnumName(newmessage).substr(0,pl);
				variables["qualified_class_name"]=actual_name;
				printer.Print(variables,"public abstract `qualified_class_name`.dto.`UnqualifiedClassOrEnumOrFieldName`Dto  `className`Dto(`ClassName`.dto.`ReqsUnqualifiedClassOrEnumOrFieldName`Dto `className`Dto);\n");
			}
		}   
	}

}


void RevAjaxInterfaceCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{
	
         std::string cpp_filename ( file.name());
         size_t slashposition=cpp_filename.find_last_of ('/');
         size_t pos1 = cpp_filename.find_first_of ('.');
         std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
         size_t pos = sbstring.find_first_of ('.');
         std::string file_name=sbstring.substr(0,pos);
         map<std::string,std::string> variables;
         //find package name where pojo files resides
         variables["ClassName"]=file.package();
         std::string package=file.package();
         size_t p = package.find_last_of('.');
         //find package name for the java file generated
         std::string name = package.substr(0,p);
         printer.Print("package `name`.services;\n","name",name);
         printer.Print(variables,"import `ClassName`.*;\n\n");
         printer.Print("public interface I`file_name`\n{\n","file_name",file_name);
         printer.Indent();
         
 		 for (int i = 0; i < file.message_type_count(); ++i) 
 		 {
 		   PrintMessage(printer,file,*file.message_type(i),file_name);
 		 }
         bool notifyAnnotation=isReverseAjaxEnable(file);
         if(notifyAnnotation)
		 {
		      printer.Print("public void subscribeAlertService();\n");
		      printer.Print("public void unSubscribeAlertService();\n");
		 }
         printer.Outdent();
         printer.Print("\n}\n");
}


bool RevAjaxInterfaceCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{                                   
	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open(GetPackageDirectoryName(file) + "/services/I" + GetFileNameFromFileDescriptor(file) + ".java")
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}



int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxInterfaceCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
