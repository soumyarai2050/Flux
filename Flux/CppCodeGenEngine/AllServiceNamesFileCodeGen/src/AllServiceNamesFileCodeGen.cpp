/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include<set>
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class AllServiceNamesFileCodeGen: public FluxCodeGenerator 
{
	protected:
		void PrintMessages(const FileDescriptor & file) const;		
	public:
		mutable std::set<std::string> is; 
		AllServiceNamesFileCodeGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};


void AllServiceNamesFileCodeGen::PrintMessages( const FileDescriptor & file) const {

      ifstream ifile("../temp/AllServiceNamesStore.txt");
      if (ifile)
            ReadStdSetFromFile(is,"../temp/AllServiceNamesStore.txt");
      std::string cpp_filename ( file.name());
      size_t pos1 = cpp_filename.find_last_of ('/');
      size_t pos2 = cpp_filename.find_first_of ('.');
      std::string name = cpp_filename.substr(pos1+1,pos2);
      pos2 = name.find_first_of ('.');
      name = name.substr(0,pos2);
      std::string qualifiedName=file.package()+"."+name;
      is.insert(qualifiedName);
      WriteStdSetToFile(is,"../temp/AllServiceNamesStore.txt");
}


bool AllServiceNamesFileCodeGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {
	PrintMessages(*file);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	AllServiceNamesFileCodeGen generator;
	return PluginMain(argc, argv, &generator);
}
