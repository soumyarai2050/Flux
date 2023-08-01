/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <set>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class AllPackageDependencySetGen: public FluxCodeGenerator 
{
	protected:
		void PrintMessages(const FileDescriptor & file) const;		
	public:
		mutable std::set<std::string> is; 
		AllPackageDependencySetGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};


void AllPackageDependencySetGen::PrintMessages( const FileDescriptor & file) const {

      ifstream ifile("../temp/AllPackageDependencyStore.txt");
      if (ifile)
            ReadStdSetFromFile(is,"../temp/AllPackageDependencyStore.txt");
      std::string qualifiedPackageName=file.package();
      is.insert(qualifiedPackageName);
      WriteStdSetToFile(is,"../temp/AllPackageDependencyStore.txt");
}


bool AllPackageDependencySetGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {
	PrintMessages(*file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	AllPackageDependencySetGen generator;
	return PluginMain(argc, argv, &generator);
}
