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

class RevAjaxWebServiceListener: public FluxCodeGenerator {
	protected:
                  void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
                  template <class DescriptorType>
                  std::string JavaPackageName(const DescriptorType & descriptor) const;
	public:

		RevAjaxWebServiceListener(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

 template <class DescriptorType>
   std::string RevAjaxWebServiceListener::JavaPackageName(const DescriptorType & descriptor) const {
	std::string tempName(descriptor.full_name());
	size_t pos = tempName.find_last_of('.');
	std::string name = tempName.substr(0,pos);
	return name;
}


void RevAjaxWebServiceListener::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
            std::string cpp_filename ( file.name());
            size_t slashposition=cpp_filename.find_last_of ('/');
            size_t pos1 = cpp_filename.find_first_of ('.');
            std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
            size_t pf = sbstring.find_first_of ('.');
            std::string file_name=sbstring.substr(0,pf);
            map<std::string,std::string> variables;
            variables["ClassName"]= UnderscoresToCapitalizedCamelCase(file.package());
            variables["file_name"]=file_name;
            variables["capitalToLower"]=UnderscoresToCamelCase(file_name);
            //print package name
            std::string package=file.package();
            size_t p = package.find_first_of('.');
            std::string packagename = package.substr(0,p);
            printer.Print("package `name`.listener;\n","name",packagename);
            //print interface package name
            size_t ps=package.find_last_of(".");
            printer.Print("import `name`.services.*;\n","name",package.substr(0,ps));
            //import webservice containing package
            printer.Print("import `packagename`.webservice.*;\n","packagename",packagename);
            
            printer.Print("\nimport javax.servlet.ServletContextEvent;\n ");
            printer.Print("import javax.servlet.ServletContextListener;\n");
            printer.Print("import org.springframework.context.ApplicationContext;\n");
            printer.Print("import org.springframework.web.context.support.WebApplicationContextUtils;\n\n");
            printer.Print(variables,"public class `ClassName`WebServiceListener implements ServletContextListener\n{\n");
            printer.Indent();
            printer.Print("");
            printer.Print("\npublic void contextInitialized(ServletContextEvent serContextEvent) \n{\n");
            printer.Indent();
            printer.Print("//All the Services will lookup at the time of application deployment\n//will be add more service\n");
            printer.Print("ApplicationContext context = WebApplicationContextUtils.getWebApplicationContext(serContextEvent.getServletContext());\n");
            printer.Print(variables,"I`file_name` `capitalToLower` = (I`file_name`)context.getBean(\"`capitalToLower`\");\n");
            printer.Print(variables,"`ClassName`WebService.getInstance().set`file_name`(`capitalToLower`);\n");
            printer.Outdent();
            printer.Print("\n}\n");
            printer.Print("\n\n");
            printer.Print("public void contextDestroyed(ServletContextEvent serContextEvent) \n{\n");
            printer.Indent();
            printer.Print(variables,"`ClassName`WebService.removeInsatnce();\n\n");
            printer.Outdent();
            printer.Print("}\n");
            printer.Outdent();
            printer.Print("}\n");

     
}


bool RevAjaxWebServiceListener::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	scoped_ptr<io::ZeroCopyOutputStream> output(
	output_directory->Open(GetPackageDirectoryName(file) + "/listener/" + UnderscoresToCamelCase(file->package()) + "WebServiceListener.java")
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxWebServiceListener generator;
	return PluginMain(argc, argv, &generator);
}
