/**
 * Protocol Buffer Class Standard POCO Compatibility Generator Plugin
 * 
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <FluxFileUtil.h>

class PrepareExtFileWithInsertPoints: public FluxCodeGenerator 
{
	public:
		void PrintFile	(const FileDescriptor & fileDescriptor, io::Printer & printer, std::ifstream & infile) const;		
		PrepareExtFileWithInsertPoints(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};


void PrepareExtFileWithInsertPoints::PrintFile	(const FileDescriptor & fileDescriptor, io::Printer & printer, std::ifstream & infile) const
{
	bool first = true;
	//Read from infile and Print with Pinter
	while(!infile.eof())
	{
		char buffer[MAX_LINE_LENGTH];
		infile.getline (buffer, MAX_LINE_LENGTH);
		if(true == first)
		{
			printer.Print("`buffer`", "buffer", buffer);
			first = false;
		}
		else
		{
			printer.Print("\n`buffer`", "buffer", buffer);
		}
	}
	//That's it we are done!!
}


bool PrepareExtFileWithInsertPoints::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	//Steps:
	//0. Open a Pre-existing file with name that we get from environment for reading and writing to output
	//1. Open output file with same name (this is open in output folder)
	//2. Create a Printer object attached with file we opened for output above
	//3. Call PrintFile with FileDescriptor reference and Printer reference

	//Step 0.
	std::string strFileName = getenv("INPUT_FILE")?getenv("INPUT_FILE"):"";
	if(0 == strFileName.length())
	{
		std::cout << "Unable to get input file name from environment variable: INPUT_FILE - calling  exit" << std::endl;
		exit(1);
	}
	else if(false == FileExists(strFileName.c_str()))
	{
		std::cout << "Unable to open input file: " << strFileName << " calling exit" << std::endl;
		exit(1);
	}
	std::ifstream infile;
	infile.open (strFileName.c_str(), std::ifstream::in);

	//All good, input file is available, now open for output file with same name
	//Step 1.
	scoped_ptr<io::ZeroCopyOutputStream> outputFileHandle(output_directory->Open(strFileName));//This is output dir

	//Step 2.	
	io::Printer printer(outputFileHandle.get(), '`');

	//Step 3.
	PrintFile(*file, printer, infile);	
	infile.close();

	return true;
}

int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	PrepareExtFileWithInsertPoints generator;
	return PluginMain(argc, argv, &generator);
}
