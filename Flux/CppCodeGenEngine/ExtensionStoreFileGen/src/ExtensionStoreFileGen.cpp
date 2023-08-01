/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-2
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <vector>
#include <set>
#include <list>
#include <boost/serialization/vector.hpp>
#include <boost/serialization/set.hpp>

class ExtensionStoreFileGen: public FluxCodeGenerator 
{
	protected:
		void PrintMessages(const FileDescriptor & file) const;
	public:
		ExtensionStoreFileGen(){}
		mutable std::map<std::string, std::set<std::string>* > im;
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};


void ExtensionStoreFileGen::PrintMessages(const FileDescriptor & file) const 
{
	int i=0;
	//Iterate therough list of all field descriotprs and find there scope, insert them into im
	for(; i < file.extension_count(); i++)
	{
		 const FieldDescriptor* ptrExtensionFieldDescriptor = file.extension(i);
		 const Descriptor *ptrContainorDescriptor = ptrExtensionFieldDescriptor->containing_type();
		 std::map<std::string, std::set<std::string>* >::const_iterator itr = im.find(ptrContainorDescriptor->name());
		 if(im.end() == itr)
		 {
		 	//This Containor Type does not exist, create its set and insert in the DS
		 	im[ptrContainorDescriptor->name()] = new std::set<std::string>;
		 }
		 //Now extract the contaionr's set and insert data in that
		 (im[ptrContainorDescriptor->name()])->insert(ptrExtensionFieldDescriptor->name());
	}
	//Check if extensions defined in this file
	if(0 != i)
	{
		//Now im has data. Write data to Store	
		std::string strStoreName = "../temp/ExtensionOptionStore.txt";
		ifstream ifile(strStoreName.c_str());
		WriteStdMapToFile(im,strStoreName.c_str());
	}//There are no extensions in this file
}

bool ExtensionStoreFileGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {
    
            PrintMessages (*file);
            return true;
}

int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	ExtensionStoreFileGen generator;
	return PluginMain(argc, argv, &generator);
}

