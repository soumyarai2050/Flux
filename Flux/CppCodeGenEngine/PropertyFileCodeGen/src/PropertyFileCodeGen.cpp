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

class PropertyFileCodeGen: public FluxCodeGenerator {
	protected:
		void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;
		
	public:

		PropertyFileCodeGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};



void PropertyFileCodeGen::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
	map<std::string,std::string> variables;
	variables["project_name"]= GetProjectName();
	printer.Print("jdbc.driverClassName=com.mysql.jdbc.Driver\n");
	printer.Print(variables,"jdbc.url=jdbc:mysql://localhost:3306/`project_name`_uat\n");
	printer.Print(variables,"jdbc.username=`project_name`_test\n");
	printer.Print(variables,"jdbc.password=`project_name`_testpass\n");
}


bool PropertyFileCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

	std::string output_filename ("jdbc.properties");

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
	PropertyFileCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
