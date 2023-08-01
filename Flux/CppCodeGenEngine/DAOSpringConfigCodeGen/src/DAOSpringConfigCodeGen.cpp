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

class DAOSpringConfigCodeGen: public FluxCodeGenerator {
	protected:
                  void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
                  template <class DescriptorType>
                  std::string JavaPackageName(const DescriptorType & descriptor) const;
		
	public:

		DAOSpringConfigCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};



 template <class DescriptorType>
   std::string DAOSpringConfigCodeGen::JavaPackageName(const DescriptorType & descriptor) const {
	std::string tempName(descriptor.full_name());
	size_t pos = tempName.find_last_of('.');
	std::string name = tempName.substr(0,pos);
	return name;
}

void DAOSpringConfigCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const
{
            std::string cpp_filename ( file.name());
            size_t slashposition=cpp_filename.find_last_of ('/');
            size_t pos1 = cpp_filename.find_first_of ('.');
            std::string sbstring = cpp_filename.substr(slashposition+1,pos1);
            size_t pf = sbstring.find_first_of ('.');
            std::string file_name=sbstring.substr(0,pf);
            map<std::string,std::string> variables;
			variables["project_name"]= GetProjectName();
            variables["ClassName"]=UnderscoresToCapitalizedCamelCase(file.package());
            variables["file_name"]=file_name;
            variables["capitalToLower"]=UnderscoresToCamelCase(file_name);
            std::string package=file.package();
            size_t pl=package.find_last_of('.');
            variables["implclasspackage"]=package.substr(0,pl);
            printer.Print("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
            printer.Print("<beans xmlns=\"http://www.springframework.org/schema/beans\"\n");
            printer.Print("xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n");
            printer.Print("xsi:schemaLocation=\"http://www.springframework.org/schema/beans \n");
            printer.Print("http://www.springframework.org/schema/beans/spring-beans-2.5.xsd\">\n");
            printer.Indent();
            printer.Print(variables,"<bean id=\"`capitalToLower`Dao\"");
            printer.Print(variables," class=\"`implclasspackage`.dao.impl.`file_name`DaoImpl\"");
            printer.Print(" scope=\"prototype\">\n");
            printer.Indent();
            printer.Print(variables,"<property name=\"sessionFactory\" ref=\"`project_name`SessionFactory\"></property>\n");
            printer.Outdent();
            printer.Print("</bean>\n");
            printer.Print(variables,"<bean id=\"`capitalToLower`\" class=\"`implclasspackage`.services.impl.`file_name`TestImpl\">\n");
            printer.Indent();
            printer.Print(variables," <property name=\"`capitalToLower`Dao\">\n");
            printer.Indent();
            printer.Print(variables,"<ref local=\"`capitalToLower`Dao\" />\n");
            printer.Outdent();
            printer.Print("</property> \n");
            printer.Outdent();
            printer.Print("</bean>\n");
            printer.Outdent();
            printer.Print("</beans>\n");
          
}


bool DAOSpringConfigCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
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
	DAOSpringConfigCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
