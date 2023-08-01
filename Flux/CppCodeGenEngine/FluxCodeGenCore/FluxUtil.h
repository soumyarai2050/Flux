/**
 * CodeGenerator Utility Functions
 * 
 *
 */
#ifndef FluxUtil_h
#define FluxUtil_h 1

#include "strutil.h" 

#include <map>
#include <set>
#include <vector>
#include <string>
#include <algorithm>
#include <fstream>
#include <boost/archive/tmpdir.hpp>

#include <boost/archive/text_iarchive.hpp>
#include <boost/archive/text_oarchive.hpp>
#include <boost/serialization/map.hpp>
#include <boost/serialization/set.hpp>
#include <boost/serialization/vector.hpp>

#include <google/protobuf/descriptor.h>
#include <google/protobuf/io/printer.h>

using namespace google::protobuf;
using namespace google::protobuf::internal;

class Indentation
{
        io::Printer &mPrinter;
        public:
                Indentation(io::Printer &printer):mPrinter(printer)
                {
                        mPrinter.Indent();
                }
                ~Indentation()
                {
                        mPrinter.Outdent();
                }
};

inline std::string TimeStampAsString(void)
{
	time_t rawtime;
	struct tm * timeinfo;
	time ( &rawtime );
	timeinfo = localtime ( &rawtime );
	std::string curTime = asctime (timeinfo);
	//Strip all spaces out
	curTime.erase(std::remove(curTime.begin(),curTime.end(),'\n'), curTime.end());
	std::string timeZone = timeinfo->tm_zone;
	return (curTime + " " + timeZone);
}

inline std::string UnderscoresToCamelCaseImpl(const std::string& input, bool cap_next_letter)
{
  std::string result;
  // Note:	I distrust ctype.h due to locales.
  for (unsigned int i = 0; i < input.size(); i++) 
  {
	if ('a' <= input[i] && input[i] <= 'z') 
	{
	  if (cap_next_letter) 
	  {
		result += input[i] + ('A' - 'a');
	  } 
	  else 
	  {
		result += input[i];
	  }
	  cap_next_letter = false;
	} 
	else if ('A' <= input[i] && input[i] <= 'Z') 
	{
	  if (i == 0 && !cap_next_letter) 
	  {
		// Force first letter to lower-case unless explicitly told to
		// capitalize it.
		result += input[i] + ('a' - 'A');
	  } 
	  else 
	  {
		// Capital letters after the first are left as-is.
		result += input[i];
	  }
	  cap_next_letter = false;
	} 
	else if ('0' <= input[i] && input[i] <= '9') 
	{
	  result += input[i];
	  cap_next_letter = true;
	} 
	else 
	{
	  cap_next_letter = true;
	}
  }
  return result;
}



inline std::string UnderscoresToCamelCase(const std::string & str) {
  return UnderscoresToCamelCaseImpl(str, false);
}

inline std::string UnderscoresToCamelCase(const Descriptor & message) {
  return UnderscoresToCamelCaseImpl(message.name(), false);
}

inline std::string UnderscoresToCamelCase(const FieldDescriptor & field) {
  return UnderscoresToCamelCaseImpl(field.name(), false);
}

inline std::string UnderscoresToCapitalizedCamelCase(const std::string & str) {
  return UnderscoresToCamelCaseImpl(str, true);
}

inline std::string UnderscoresToCapitalizedCamelCase(const Descriptor & message) {
  return UnderscoresToCamelCaseImpl(message.name(), true);
}

inline std::string UnderscoresToCapitalizedCamelCase(const FieldDescriptor & field) {
  return UnderscoresToCamelCaseImpl(field.name(), true);
}

std::string ToLowerCaseUnderscoreSeparated(std::string varName)
{
	bool isPredCharCapital = false;
	std::string result = "";
	if(0)//This if code is to be used for Enum Value Gen
	{
		bool isPredCharNumber = false;
		for (unsigned int i = 0; i < varName.length(); i++) 
		{
			if ('A' <= varName[i] && varName[i] <= 'Z') 
			{
				if (!isPredCharCapital) 
				{
					//This is capital char with pred non-capital
					//In this case We need to prefix and '_' if this not first charector of var name
					if(0 != i)
					{
						result += "_";
					}
				} 
				result += varName[i];
				//Set isPredCharCapital to true for subsiquent runs
				isPredCharCapital = true;
				isPredCharNumber = false;
			}
			else if (('0' <= varName[i] && varName[i] <= '9')) 
			{
				if (!isPredCharNumber) 
				{
					//This is number char with pred non-number
					//In this case We need to prefix and '_' even if this first charector of var name (cannot start with number)
					result += "_";
				}
				result += varName[i];
				isPredCharCapital = false;
				isPredCharNumber = true;
			}
			else if('a' <= varName[i] && varName[i] <= 'z')
			{
				//capitalize it
				result += varName[i] - ('a' - 'A');
				isPredCharCapital = false;
				isPredCharNumber = false;
			}
			else 
			{
				throw "Special charector(s) not allowed in enum value names";
			}
		}
	}
	else
	{
		for (unsigned int i = 0; i < varName.length(); i++) 
		{
			if ('A' <= varName[i] && varName[i] <= 'Z') 
			{
				if (!isPredCharCapital) 
				{
					//This is capital char with pred non-capital
					//In this case We need to prefix and '_' if this not first charector of var name
					if(0 != i)
					{
						result += "_";
					}
				} 
				//Now We need to convert letter to lower-case irrespective to comply with style guide
				result += varName[i] + ('a' - 'A');
				//Set isPredCharCapital to true for subsiquent runs
				isPredCharCapital = true;
			}
			else if (('0' <= varName[i] && varName[i] <= '9') || ('a' <= varName[i] && varName[i] <= 'z') || '_' == varName[i]) 
			{
				//Just continue as-is, set isPredCharCapital = false
				result += varName[i];
				isPredCharCapital = false;
			} 
			else 
			{
				throw "Special charector(s) not allowed in variable names";
			}
		}
	}
	return result;
}

inline std::string LowerString(const std::string & s) {
  std::string newS (s);
  LowerString(&newS);
  return newS;
}

inline std::string UpperString(const std::string & s) {
  std::string newS (s);
  UpperString(&newS);
  return newS;
}

std::string ReplaceDotWithFullColon(const std::string& input){
	std::string result="";
	for (unsigned int i = 0; i < input.size(); i++) 
	{
		if (input[i]=='.') 
			result+=':';
		else
			result+=input[i];
	}
	return result;
}

std::string ReplaceDotWithSlash(const std::string& input){
	std::string result="";
	for (unsigned int i = 0; i < input.size(); i++) 
	{
		if (input[i]=='.') 
			result+='/';
		else
			result+=input[i];
	}
	return result;
}

//Utility Template Method to Write a std::map to a file
template <typename KeyType, typename ValueType>
void WriteStdMapToFile ( const std::map<KeyType,ValueType> &map, const char* fileName)
{
        std::ofstream s(fileName);
        boost::archive::text_oarchive oa(s);
        oa << map;
        return;
}

//Utility Template Method to Write a std::map to a file
template <typename KeyType, typename ValueType>
void ReadStdMapFromFile ( std::map<KeyType,ValueType> &map, const char* fileName)
{
        // open the archive
        std::ifstream ifs(fileName);
        boost::archive::text_iarchive ia(ifs);
        // restore the schedule from the archive
        ia >> map;
        return;
}

//Utility Template Method to Write a std::map to a file
template <typename KeyType, typename ValueType>
void WriteStdMapToFile ( const std::map<KeyType, ValueType*> &oMap, const char* fileName)
{
        std::ofstream s(fileName);
        boost::archive::text_oarchive oa(s);
        typedef typename std::map<KeyType, ValueType*>::const_iterator MapCIter;
        MapCIter cIter;
        std::map<KeyType,ValueType> tempMap;
        for (cIter = oMap.begin(); cIter != oMap.end(); cIter++)
        {
                tempMap[cIter->first] = *(cIter->second);
        }
        oa << ( const std::map<KeyType, ValueType> )tempMap;
        return;
}

//Utility Template Method to Write a std::map to a file
template <typename KeyType, typename ValueType>
void ReadStdMapFromFile ( std::map<KeyType,ValueType*> &iMap, const char* fileName)
{
        // open the archive
        std::ifstream ifs(fileName);
        boost::archive::text_iarchive ia(ifs);
        // restore the schedule from the archive
        std::map<KeyType,ValueType> tempMap;
        ia >> tempMap;
        typedef typename std::map<KeyType, ValueType>::const_iterator MapCIter;
        MapCIter cIter;
        for (cIter = tempMap.begin(); cIter != tempMap.end(); cIter++)
        {
                iMap[cIter->first] = new ValueType(cIter->second);
        }
        return;
}

//Utility Template Method to Write a std::set to a file
template <typename KeyType>
void WriteStdSetToFile ( const std::set<KeyType> &set, const char* fileName)
{
	std::ofstream s(fileName);
	boost::archive::text_oarchive oa(s);
	oa << set;
        return;
}

//Utility Template Method to Read a std::set from a file
template <typename KeyType>
void ReadStdSetFromFile ( std::set<KeyType> &set, const char* fileName)
{
	// open the archive
	std::ifstream ifs(fileName);
	boost::archive::text_iarchive ia(ifs);
	// restore the schedule from the archive
	ia >> set;
	return;
}

inline std::string GetProjectName()
{
	//get Projcet Name
	return (getenv("PROJECT_NAME")?getenv("PROJECT_NAME"):"UNKNOWN_PROJECT");
}

inline std::string GetUnderscoresToCamelCaseProjectName()
{
	return (UnderscoresToCamelCase(GetProjectName()));
}

inline std::string GetUnderscoresToCapitalizedCamelCaseProjectName()
{
	return (UnderscoresToCapitalizedCamelCase(GetProjectName()));
}

#endif //FluxUtil_h
