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

class RevAjaxDelegateCodeGen: public FluxCodeGenerator {
	protected:
               void PrintMessages(io::Printer &printer, const FileDescriptor & file) const;
               void PrintAlertService(io::Printer &printer, const FileDescriptor & file) const;
               void PrintMessage(io::Printer &printer, const FileDescriptor & file,const Descriptor & message,std::string &file_name) const ;
               std::string VariableGetterName(const FieldDescriptor & field) const;
               std::string VariableSetterName(const FieldDescriptor & field) const;
	public:

		RevAjaxDelegateCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

std::string RevAjaxDelegateCodeGen::VariableGetterName(const FieldDescriptor & field) const {
	return (std::string("get") + UnderscoresToCapitalizedCamelCase(field));
}

std::string RevAjaxDelegateCodeGen::VariableSetterName(const FieldDescriptor & field) const {
	return (std::string("set") + UnderscoresToCapitalizedCamelCase(field));
}

void RevAjaxDelegateCodeGen::PrintMessage(io::Printer &printer, const FileDescriptor & file,const Descriptor & message,std::string &file_name) const 
{
	map<std::string,std::string> variables;
	variables["file_name"]=file_name;
	variables["object_name"]=UnderscoresToCamelCase(file_name);
	variables["object_cap_name"]=UnderscoresToCapitalizedCamelCase(file_name);
	size_t p=QualifiedJavaClassOrEnumName(message).find_last_of('.');
	std::string actual_name=QualifiedJavaClassOrEnumName(message).substr(0,p);
	variables["ClassName"]=actual_name;
	variables["ReqsUnqualifiedClassOrEnumOrFieldName"]=UnqualifiedClassOrEnumOrFieldName(message);
	variables["className"]=UnderscoresToCamelCase(UnqualifiedClassOrEnumOrFieldName(message));
	variables["project_name"]=GetProjectName();
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
				printer.Print(variables,"public  `qualified_class_name`.dto.`UnqualifiedClassOrEnumOrFieldName`Dto  `className`Dto(`ClassName`.dto.`ReqsUnqualifiedClassOrEnumOrFieldName`Dto `className`Dto)\n{\n");
				printer.Print("\treturn `name`.webservice.","name",PackageNameUptoFirstDot(*file.message_type(0)));
				printer.Print(variables,"`project_name`Service.getInstance().get`object_cap_name`().`className`Dto(`className`Dto);");
				printer.Print("\n}\n\n");
			}
		}   
	}
}

void RevAjaxDelegateCodeGen::PrintAlertService(io::Printer &printer, const FileDescriptor & file) const
{
         map<std::string,std::string> variables;
         variables["project_name"]=GetProjectName();
         std::string cpp_filename ( file.name());
         size_t slashposition=cpp_filename.find_last_of ('/');
         size_t pos1 = cpp_filename.find_first_of ('.');
         std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
         size_t pos = sbstring.find_first_of ('.');
         std::string file_name=sbstring.substr(0,pos);
         variables["file_name"]=file_name;
         std::string packagename=file.package();
         size_t pf=packagename.find_first_of('.');
         variables["package"]=packagename.substr(0,pf);
        
         
         printer.Print("public void  subscribeAlertService()\n");
         printer.Print("{\n");
         printer.Indent();
         printer.Print(variables,"`package`.webservice.`project_name`Service.getInstance().get`file_name`().subscribeAlertService();\n");
         printer.Outdent();
	 printer.Print("\n}\n");
         printer.Print("public void  unSubscribeAlertService()\n");
         printer.Print("{\n");
         printer.Indent();
         printer.Print(variables,"`package`.webservice.`project_name`Service.getInstance().get`file_name`().unSubscribeAlertService();\n");
         printer.Outdent();
         printer.Print("}\n");

        
}
void RevAjaxDelegateCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{
	
         std::string cpp_filename ( file.name());
         size_t slashposition=cpp_filename.find_last_of ('/');
         size_t pos1 = cpp_filename.find_first_of ('.');
         std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
         size_t pos = sbstring.find_first_of ('.');
         std::string file_name=sbstring.substr(0,pos);
         map<std::string,std::string> variables;
         //find package name where dto files resides
         variables["ClassName"]=file.package();
         std::string package=file.package();
         size_t p = package.find_first_of('.');
         //find package name for the java file generated
         std::string name = package.substr(0,p);
         printer.Print("package `name`.services.delegate;\n","name",name);
         printer.Print(variables,"import `ClassName`.*;\n\n");
         printer.Print("public class `file_name`Delegate\n{\n","file_name",file_name);
         printer.Indent();
         for (int i = 0; i < file.message_type_count(); ++i) 
  		 {
  		   PrintMessage(printer,file,*file.message_type(i),file_name);
  		 }
         bool notifyAnnotation=isReverseAjaxEnable(file); 
         if(notifyAnnotation)
            PrintAlertService(printer,file);
         printer.Outdent();
         printer.Print("\n}\n");
}


bool RevAjaxDelegateCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {
                                   
         //This gives only until com
         std::string package=file->package();
         size_t pos = package.find_first_of('.');
         std::string name = ReplaceDotWithSlash(package.substr(0,pos));
		 
         scoped_ptr<io::ZeroCopyOutputStream> output(
         output_directory->Open(name+"/services/delegate/"+GetFileNameFromFileDescriptor(file)+"Delegate.java")
       );

       io::Printer printer(output.get(), '`');
       PrintMessages  (printer, *file);
       return true;

}



int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxDelegateCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
