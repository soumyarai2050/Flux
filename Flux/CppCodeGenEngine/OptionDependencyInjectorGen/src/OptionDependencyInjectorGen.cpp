/**
 * Flux Option Dependency Injector
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <set>

class OptionDependencyInjectorGen
{
	protected:
		void PrintMessages(const std::string strTargetDirectoryNameExt) const;		
	public:
		mutable std::set<std::string> is; 
		OptionDependencyInjectorGen(){}
		bool Generate(const std::string strTargetDirectoryName) const;
};


void OptionDependencyInjectorGen::PrintMessages(const std::string strTargetDirectoryNameExt) const 
{
	std::string strTargetDirectoryName = strTargetDirectoryNameExt;
	ifstream iFile("../temp/AllPackageDependencyStore.txt");
	if (iFile)
		ReadStdSetFromFile(is,"../temp/AllPackageDependencyStore.txt");
	//We have all package dependencies in the set is
	//Lets create OptionDependencyInjector script
	std::string strOutputFileName;
	if(0 != strTargetDirectoryName.length() && '/' != strTargetDirectoryName[strTargetDirectoryName.length()-1])
	{
		strTargetDirectoryName += "/";
		strOutputFileName = strTargetDirectoryName + "OptionDependencyInjector.sh";
	}
	else
	{
		strOutputFileName = strTargetDirectoryName + "OptionDependencyInjector.sh";
	}
	ofstream oFile(strOutputFileName.c_str());
	if(oFile)
	{
		//All set start generation
		oFile << "#!/bin/bash" << std::endl;
		oFile << "source " << strTargetDirectoryName << "${PROJECT_NAME}Core.sh" << std::endl;
		oFile << std::endl;
		oFile << "if [ \"$1\" != \"\" ] ; then" << std::endl;
		oFile << "	" << strTargetDirectoryName << "AllProto.sh $1" << std::endl;
		//Now iterate over the set and inject dependency in each element
		for (std::set<std::string>::iterator it = is.begin(); it != is.end(); it++)
		{
			oFile << std::endl;
			std::string strDirectoryName = "../output/" + ReplaceDotWithSlash(*it) + "/";
			oFile << "	cp -p ${CODE_GEN_ENGINE_HOME}/FluxCodeGenCore/FluxOptions.java " << strDirectoryName << std::endl;
			oFile << "	cd " << strDirectoryName << std::endl;
			oFile << "	sed '1i \\ package " << *it << "; ' FluxOptions.java > $$" << std::endl;
			oFile << "	mv $$ FluxOptions.java" << std::endl;
			oFile << "	cd -" << std::endl;
		}
		oFile << "fi" << std::endl;
	}
}


bool OptionDependencyInjectorGen::Generate(const std::string strTargetDirectoryName) const {
	PrintMessages(strTargetDirectoryName);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	OptionDependencyInjectorGen generator;
	if(1 < argc)
	{
		generator.Generate((const char*)(argv[1]));
	}
	else
	{
		generator.Generate("");
	}
}
