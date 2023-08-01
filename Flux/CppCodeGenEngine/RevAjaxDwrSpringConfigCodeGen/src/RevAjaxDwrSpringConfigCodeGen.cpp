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

class RevAjaxDwrSpringConfigCodeGen: public FluxCodeGenerator {
	protected:
                  void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
                  template <class DescriptorType>
                  std::string JavaPackageName(const DescriptorType & descriptor) const;
		
	public:

		RevAjaxDwrSpringConfigCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};



 template <class DescriptorType>
   std::string RevAjaxDwrSpringConfigCodeGen::JavaPackageName(const DescriptorType & descriptor) const {
	std::string tempName(descriptor.full_name());
	size_t pos = tempName.find_last_of('.');
	std::string name = tempName.substr(0,pos);
	return name;
}

void RevAjaxDwrSpringConfigCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{
            std::string cpp_filename ( file.name());
            size_t slashposition=cpp_filename.find_last_of ('/');
            size_t pos1 = cpp_filename.find_first_of ('.');
            std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
            size_t pf = sbstring.find_first_of ('.');
            std::string file_name=sbstring.substr(0,pf);
            map<std::string,std::string> variables;
            variables["ClassName"]=UnderscoresToCapitalizedCamelCase(file.package());
            variables["file_name"]=file_name;
            variables["capitalToLower"]=UnderscoresToCamelCase(file_name);
            std::string package=file.package();
            size_t pl=package.find_last_of('.');
            variables["implclasspackage"]=package.substr(0,pl);
            printer.Print("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
           
            printer.Print("<beans xmlns=\"http://www.springframework.org/schema/beans\"\n");
            printer.Indent();
            printer.Print("xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n");
            //printer.Print("xmlns:aop=\"http://www.springframework.org/schema/aop\"\n");
            printer.Print("xsi:schemaLocation=\"");
            printer.Outdent();
            printer.Print("http://www.springframework.org/schema/beans \nhttp://www.springframework.org/schema/beans/spring-beans-2.5.xsd\">\n");
           
            printer.Print(variables,"<bean id=\"`capitalToLower`\" class=\" `implclasspackage`.services.impl.`file_name`TestImpl\">\n");
            printer.Print("</bean>\n");
            printer.Print("</beans>\n");

}


bool RevAjaxDwrSpringConfigCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

            std::string cpp_filename ( file->name());
         size_t slashposition=cpp_filename.find_last_of ('/');
         size_t pos1 = cpp_filename.find_first_of ('.');
         std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
         size_t pf = sbstring.find_first_of ('.');
         std::string file_name=sbstring.substr(0,pf);
            
            scoped_ptr<io::ZeroCopyOutputStream> output(
            output_directory->Open(file_name+"-SpringConfig.xml")
            );

            io::Printer printer(output.get(), '`');
            PrintMessages (printer, *file);
            return true;

}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxDwrSpringConfigCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
