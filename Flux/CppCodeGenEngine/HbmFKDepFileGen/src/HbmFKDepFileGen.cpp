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
#include <boost/serialization/vector.hpp>
#include <boost/serialization/set.hpp>

class HbmFKDepFileGen: public FluxCodeGenerator 
{
	protected:
		void PrintComplexMessage   (const Descriptor & message,const std::string& prefix) const;
		void PrintMessages(const FileDescriptor & file) const;
	public:
		HbmFKDepFileGen(){}
		mutable std::map<std::string, std::set<std::string>* > im;
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void HbmFKDepFileGen::PrintComplexMessage(const Descriptor & message,const std::string &prefix) const 
{
	std::map<std::string,set<std::string>* >::const_iterator itr;
	for (int i = 0; i < message.field_count(); ++i) 
	{
		bool isComplex = false;
		const FieldDescriptor &field(*message.field(i));
		std::set<std::string> *ptrFKSet = new std::set<std::string>;
		map<std::string, std::string> variables;
		switch (field.type()) 
		{
			case FieldDescriptor::TYPE_MESSAGE:
			case FieldDescriptor::TYPE_GROUP:
				variables["type"] = QualifiedCppClassOrEnumName(*field.message_type()) + " ";
				isComplex = true;
				break;
			default:
				variables["type"]="";
		}
		if (field.is_repeated()) 
		{
			// Repeated field
			if(isComplex)
			{
				for( itr = im.begin(); itr != im.end(); ++itr )
				{
					if(itr->first==UnqualifiedClassOrEnumOrFieldName(*field.message_type()))
						ptrFKSet = itr->second;
				}
				ptrFKSet->insert(QualifiedJavaClassOrEnumName(message));
				im[UnqualifiedClassOrEnumOrFieldName(*field.message_type())]= ptrFKSet;
			}
		}
	}
}


void HbmFKDepFileGen::PrintMessages(const FileDescriptor & file) const 
{
	ifstream ifile("../temp/RepeatedFieldDependencyMapSet.txt");
	if (ifile)
		ReadStdMapFromFile(im,"../temp/RepeatedFieldDependencyMapSet.txt");
	for (int i = 0; i < file.message_type_count(); ++i)
	{
		PrintComplexMessage(*file.message_type(i),file.name());
	}
	WriteStdMapToFile(im,"../temp/RepeatedFieldDependencyMapSet.txt");
}

bool HbmFKDepFileGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const {
    
            PrintMessages (*file);
            return true;
}

int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	HbmFKDepFileGen generator;
	return PluginMain(argc, argv, &generator);
}

