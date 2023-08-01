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

class FinalWebServiceCodeGen: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
	public:

                mutable std::set<std::string> os; 
		FinalWebServiceCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

void FinalWebServiceCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
      ReadStdSetFromFile(os,"../temp/AllServiceNamesStore.txt");
      set<std::string>::const_iterator it;
             
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
      printer.Print("import `name`.services.*;\n","name",package.substr(0,pl));
      map<std::string,std::string> variables;
      variables["ClassName"]=GetProjectName();
      variables["file_name"]=file_name;
      variables["capitalToLower"]=UnderscoresToCamelCase(file_name);
      printer.Print(variables,"public class `ClassName`Service\n{\n");
      printer.Indent();
      printer.Print(variables,"private static `ClassName`Service instance =new `ClassName`Service();\n");
      for ( it=os.begin() ; it != os.end(); it++ ){
                 
         std::string strServiceName= *it;
         size_t last_pos=strServiceName.find_last_of('.');
         std::string file_name=strServiceName.substr(last_pos+1);
         variables["capitalToLower"]=UnderscoresToCamelCase(file_name);
         variables["file_name"]=file_name;
         printer.Print(variables,"I`file_name` `capitalToLower` = null;\n ");
           
          
      }
      
      printer.Print(variables,"private `ClassName`Service(){\n");
      printer.Print(variables,"}\n");
      printer.Print(variables,"public static `ClassName`Service getInstance(){\n");
      printer.Indent();
      printer.Print(variables,"if(instance==null)\n");
      printer.Print(variables,"\tinstance = new  `ClassName`Service();\n");
      printer.Print(variables,"return instance;\n");
      printer.Outdent();
      printer.Print("}\n\n");
      printer.Print("public static void removeInsatnce(){\n\tinstance = null;\n");
      printer.Print("}\n\n");
       for ( it=os.begin() ; it != os.end(); it++ ){
                 
         std::string strServiceName= *it;
         size_t last_pos=strServiceName.find_last_of('.');
         std::string file_name=strServiceName.substr(last_pos+1);
         variables["capitalToLower"]=UnderscoresToCamelCase(file_name);
         variables["file_name"]=file_name;
         printer.Print(variables,"public I`file_name` get`file_name`(){\n");
         printer.Print(variables,"          return `capitalToLower`;\n");
         printer.Print("}\n");
         printer.Print(variables,"public void set`file_name`(I`file_name`  `capitalToLower` ){\n");
         printer.Print(variables,"           this.`capitalToLower` = `capitalToLower`;\n");
         printer.Print("}\n");
      }
      printer.Outdent();
      printer.Print("}\n");
}


bool FinalWebServiceCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
			//This gives only until com
            std::string package=file->package();
            size_t pf = package.find_first_of('.');
            std::string name = package.substr(0,pf);
            
            scoped_ptr<io::ZeroCopyOutputStream> output(
            output_directory->Open(name+"/webservice/"+ GetProjectName() +"Service.java")
            );

            io::Printer printer(output.get(), '`');
            PrintMessages(printer, *file);
            return true;

}



int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	FinalWebServiceCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
