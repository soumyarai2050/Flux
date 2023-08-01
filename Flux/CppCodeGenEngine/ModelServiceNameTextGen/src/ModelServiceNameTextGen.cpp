/**
 * Protocol Buffer Class Name Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <FluxFileUtil.h>

class ModelServiceNameTextGen: public FluxCodeGenerator 
{
	public:

		ModelServiceNameTextGen(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

bool ModelServiceNameTextGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {

	std::string output_filename = "../temp/" + file->name() + "_service_name.txt";
	std::string strInsertPointName = "file_name_insert_point_name";
	if(false == FileExists(output_filename.c_str()))
	{
		// Generate main file.
		scoped_ptr<io::ZeroCopyOutputStream> output(
			output_directory->Open(output_filename)
		);

		io::Printer printer(output.get(), '`');
		printer.Print("All Service Files:\n");		
		//Indent as required		
		printer.Indent();
		//Add Service File Name
		printer.Print("`file_name`\n", "file_name", output_filename);
		//Add insert Point
		printer.Print("// @@protoc_insertion_point(`insert_point_name`)\n", "insert_point_name", strInsertPointName);
		//Outdent
		printer.Outdent();
	}
	else 
	{
		// File exists, open with insert point
		scoped_ptr<io::ZeroCopyOutputStream> output(
			output_directory->OpenForInsert(output_filename,strInsertPointName)
		);

		io::Printer printer(output.get(), '`');
		//Add Service File Name - Indent not required, indent of insert point automatically picked
		printer.Print("`file_name`\n", "file_name", output_filename);
	}
	return true;
}

int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	ModelServiceNameTextGen generator;
	return PluginMain(argc, argv, &generator);
}
