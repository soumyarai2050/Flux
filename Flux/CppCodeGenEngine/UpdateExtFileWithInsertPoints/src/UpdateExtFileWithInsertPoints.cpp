/**
 * Protocol Buffer Class Name Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <FluxFileUtil.h>

class UpdateExtFileWithInsertPoints: public FluxCodeGenerator 
{
	public:

		UpdateExtFileWithInsertPoints(){}

		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

bool UpdateExtFileWithInsertPoints::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{				
	std::string output_filename = getenv("INPUT_FILE")?getenv("INPUT_FILE"):"";
	if(0 == output_filename.length())
	{
		std::cout << "Unable to get input file name from environment variable: INPUT_FILE - calling  exit" << std::endl;
		GOOGLE_LOG(FATAL) << "Unable to get input file name from environment variable: INPUT_FILE - calling  exit";
		exit(1);
	}

	std::string strInsertPointName = "NAME";
	if(false == FileExists(output_filename.c_str()))
	{
		// Could not find the desired file !!
		std::cout << "Unable to find output file: " << output_filename << " calling exit!" << std::endl;
		GOOGLE_LOG(FATAL) << "Unable to find output file: " << output_filename << " calling exit!";
		exit(1);
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
	UpdateExtFileWithInsertPoints generator;
	return PluginMain(argc, argv, &generator);
}

