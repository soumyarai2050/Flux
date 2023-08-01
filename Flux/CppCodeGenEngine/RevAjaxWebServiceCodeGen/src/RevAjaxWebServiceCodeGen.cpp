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

class RevAjaxWebServiceCodeGen: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
	public:
		RevAjaxWebServiceCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

void RevAjaxWebServiceCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const {

      std::string cpp_filename (file.name());
      size_t slashposition=cpp_filename.find_last_of ('/');
      size_t pos1 = cpp_filename.find_first_of ('.');
      std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
      size_t pfirst = sbstring.find_first_of ('.');
      std::string file_name=sbstring.substr(0,pfirst);
       //find package name.
      std::string package=file.package();
      size_t pf=package.find_first_of('.');
      size_t pl= package.find_last_of('.');
      printer.Print("package `name`.webservice;\n","name",package.substr(0,pf));
      printer.Print("import `name`.services.I`file_name`;\n","name",package.substr(0,pl),"file_name",file_name);
      map<std::string,std::string> variables;
      variables["ClassName"]= UnderscoresToCapitalizedCamelCase(package);
      variables["file_name"]=file_name;
      variables["capitalToLower"]=UnderscoresToCamelCase(file_name);
      printer.Print(variables,"public class `ClassName`WebService\n{\n");
      printer.Indent();
      printer.Print(variables,"private static `ClassName`WebService instance =new `ClassName`WebService();\n");
      printer.Print(variables,"I`file_name` `capitalToLower` = null;\n ");
      printer.Print(variables,"private `ClassName`WebService()\n{\n");
      printer.Print(variables,"}\n");
      printer.Print(variables,"public static `ClassName`WebService getInstance()\n{\n");
      printer.Indent();
      printer.Print(variables,"if(instance==null)\n");
      printer.Print(variables,"\tinstance = new  `ClassName`WebService();\n");
      printer.Print(variables,"return instance;\n");
      printer.Outdent();
      printer.Print("}\n\n");
      printer.Print("public static void removeInsatnce()\n{\n\tinstance = null;\n");
      printer.Print("}\n\n");
      printer.Print(variables,"public I`file_name` get`file_name`()\n{\n");
      printer.Print(variables,"\treturn `capitalToLower`;\n");
      printer.Print("}\n\n");
      printer.Print(variables,"public void set`file_name`(I`file_name`  `capitalToLower` )\n{\n");
      printer.Indent();
      printer.Print(variables,"this.`capitalToLower` = `capitalToLower`;\n");
      printer.Outdent();
      printer.Print("\n}\n");
      printer.Outdent();
      printer.Print("}\n");
}


bool RevAjaxWebServiceCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

            std::string cpp_filename ( file->name());
            size_t pos = cpp_filename.find_first_of ('.');
            std::string file_name = cpp_filename.substr(0,pos);
            //find package name which contains generated file
            std::string package=file->package();
            size_t pf = package.find_first_of('.');
            std::string name = package.substr(0,pf);
            scoped_ptr<io::ZeroCopyOutputStream> output(
            output_directory->Open(name+"/webservice/"+ UnderscoresToCapitalizedCamelCase(package)+"WebService.java")
            );

            io::Printer printer(output.get(), '`');
            PrintMessages  (printer, *file);
            return true;

}



int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxWebServiceCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
