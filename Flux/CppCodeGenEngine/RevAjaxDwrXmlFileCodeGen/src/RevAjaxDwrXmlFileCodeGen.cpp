/**
 * Protocol Buffer Data Hierarchy Text Generator Plugin for protoc
 * By Dev-2
 *
 */

#include <FluxUtil.h>
#include <map>
#include <set>

class RevAjaxDwrXmlFileCodeGen
{
	protected:
		void PrintMessages  (const std::string strTargetDirectoryName) const;
	public:
		RevAjaxDwrXmlFileCodeGen(){}		
		mutable std::map<std::string,std::string> serviceNameDelegateMap;
		mutable std::set<std::string> messageQualifiedNameSet;
		mutable std::set<std::string> enumQualifiedNameSet;
		bool Generate(const std::string strTargetDirectoryName) const;
};

void RevAjaxDwrXmlFileCodeGen::PrintMessages(const std::string strTargetDirectoryName) const 
{
	//First read Service Name - Service Deligate Map into respective map
	{
		ifstream ifile("../temp/ServiceNameDeligateMap.txt");
		if (ifile)
			ReadStdMapFromFile(serviceNameDelegateMap,"../temp/ServiceNameDeligateMap.txt");
	}
	//then read Messagefile Set into respective set
	{
		ifstream iFile("../temp/MessageQualifiedDtoNameSet.txt");
		if (iFile)
			ReadStdSetFromFile(messageQualifiedNameSet,"../temp/MessageQualifiedDtoNameSet.txt");
	}
	//finally read Enum file Set into respective set
	{
		ifstream iFile("../temp/EnumQualifiedNameSet.txt");
		if (iFile)
			ReadStdSetFromFile(enumQualifiedNameSet,"../temp/EnumQualifiedNameSet.txt");
	}

	//Map and Both sets are ready, now generate DWR.xml
	//Open dwr.xml file to write in output directory provided
	std::string strOutputFileName = "dwr.xml";
	if(0 != strTargetDirectoryName.length() && '/' != strTargetDirectoryName[strTargetDirectoryName.length()-1])
	{
		strOutputFileName = strTargetDirectoryName + "/" + strOutputFileName;
	}
	else
	{
		strOutputFileName = strTargetDirectoryName + strOutputFileName;
	}
	ofstream oFile(strOutputFileName.c_str());
	if(oFile)
	{
		//All set start generation
		//Print Header
		oFile << "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" << std::endl;
		oFile << "		<!DOCTYPE dwr PUBLIC" << std::endl;
		oFile << "			\"-//GetAhead Limited//DTD Direct Web Remoting 3.0//EN\"" << std::endl;
		oFile << "			\"http://getahead.org/dwr/dwr30.dtd\">" << std::endl;
		oFile << "		<dwr>" << std::endl;
		oFile << "		  <allow>" << std::endl;

	}

	//Now add all Service Creators 
	//(1): TODO: Add all Service Creators here - We need to read ServiceNameSet and do this, e.g.:
	//<create creator="new" javascript="adminService" >
	//		  <param name="class" value="com.services.delegate.AdminServiceDelegate"/>
	//		</create>
	for (std::map<std::string,std::string>::const_iterator it = serviceNameDelegateMap.begin(); it != serviceNameDelegateMap.end(); it++)
	{
		oFile << "			<create creator=\"new\" javascript=\"" << UnderscoresToCamelCase(it->first) << "\" >"<< std::endl;
		oFile << "			  <param name=\"class\" value=\"" << it->second << "\"/>" << std::endl;
		oFile << "			</create>" << std::endl;
	}
	oFile << std::endl;
	
	// Now add all dto_class convertors
	for (std::set<std::string>::const_iterator itm = messageQualifiedNameSet.begin(); itm != messageQualifiedNameSet.end(); itm++)
	{
		oFile << "			<convert match=\"" << *itm << "\" converter=\"bean\"/>" << std::endl;
	}
	oFile << std::endl;

	// Now add enum convertors
	for (set<std::string>::const_iterator enum_it=enumQualifiedNameSet.begin(); enum_it!=enumQualifiedNameSet.end(); enum_it++)
	{
		oFile << "                  <convert match=\"" << *enum_it << "\" converter=\"enum\"/>" << std::endl;
	}

	//Finally add Footer
	oFile << "		  </allow>" << std::endl;
	oFile << "		</dwr>" << std::endl;

	//Done!!
}

bool RevAjaxDwrXmlFileCodeGen::Generate(const std::string strTargetDirectoryName) const 
{
	PrintMessages (strTargetDirectoryName);
	return true;
}


int main(int argc, char* argv[]) {
        if(getenv("DEBUG_ENABLE"))
		sleep(30);
	RevAjaxDwrXmlFileCodeGen generator;
	if(1 < argc)
	{
		generator.Generate((const char*)(argv[1]));
	}
	else
	{
		generator.Generate("");
	}
}

