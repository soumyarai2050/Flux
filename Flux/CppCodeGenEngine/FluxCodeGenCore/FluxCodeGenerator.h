/**
 * Protocol Buffer Code Generator Plugin Base Class for protoc
 * 
 *
 */
#ifndef FluxCodeGenerator_h
#define FluxCodeGenerator_h 1

#include <map>
#include <iostream>
#include <fstream>
#include <boost/archive/tmpdir.hpp>

#include <boost/archive/text_iarchive.hpp>
#include <boost/archive/text_oarchive.hpp>

#include <boost/serialization/map.hpp>

#include "FluxUtil.h"
#include "FluxORMUtil.h"
#include "FluxDTOUtil.h"
#include "FluxDAOUtil.h"
#include "FluxMessageUtil.h"


#include <google/protobuf/wire_format.h>
#include <google/protobuf/wire_format_lite.h>
#include <google/protobuf/wire_format_lite_inl.h>


#include <google/protobuf/compiler/plugin.h>
#include <google/protobuf/compiler/code_generator.h>

#include <google/protobuf/descriptor.h>
#include <google/protobuf/dynamic_message.h>
#include <google/protobuf/io/tokenizer.h>
#include <google/protobuf/compiler/parser.h>
#include <google/protobuf/text_format.h>

#include <google/protobuf/io/printer.h>
#include <google/protobuf/io/zero_copy_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl.h>

#include <flux_options.pb.h>

/*
  * FLUX_CODE_GEN_ERROR is to be printed for all unimplemented corner cases, the generated code error checker script searches this and 
  * complains if found. Once found the developer should talk to framework team to find fix for identified corner case
  */
#define FLUX_CODE_GEN_ERROR "ERRORORRE"

#ifndef __unix
	#define fileno _fileno
#endif //__unix

#define MAPPING_ATTRIBUTE_SUFFIX (getenv("MAPPING_ATTRIBUTE_SUFFIX")?getenv("MAPPING_ATTRIBUTE_SUFFIX"):"_attr")
#define MAPPING_MESSAGE_SUFFIX (getenv("MAPPING_MESSAGE_SUFFIX")?getenv("MAPPING_MESSAGE_SUFFIX"):"Mapping")
#define MAPPING_MODEL_SUFFIX MAPPING_MESSAGE_SUFFIX
#define MAPPING_FILE_EXTENSION MAPPING_MESSAGE_SUFFIX
#define MAPPING_DIR (getenv("MAPPING_DIR")?getenv("MAPPING_DIR"):"../mapping/")
#define MAX_LINE_LENGTH 10240

#ifndef __unix
#define MAPPING_MODEL_DIR (getenv("MAPPING_MODEL_DIR")?getenv("MAPPING_MODEL_DIR"):"\\..\\mapping_model\\")
#else //__unix
#define MAPPING_MODEL_DIR (getenv("MAPPING_MODEL_DIR")?getenv("MAPPING_MODEL_DIR"):"../mapping_model/")
#endif //__unix


using namespace google;
using namespace google::protobuf;
using namespace google::protobuf::compiler;
using namespace google::protobuf::internal;

class FluxCodeGenerator : public CodeGenerator 
{
	private:
		mutable char uniqueIdentifierSuffix[3];
		const std::string uniqueIdentifierPrefix;
	protected:		
		virtual void PrintMessage   (io::Printer &printer, const Descriptor & message) const;
		virtual void PrintMessages  (io::Printer &printer, const FileDescriptor & file) const;

	public:
		void LoadMappingInMessage(protobuf::Message *mappingMessage, const Descriptor & mappingMessageDescriptor) const;		
		std::string GetMappingModelFilePath() const;
		const protobuf::FileDescriptor * OpenProto( std::string fileName, std::string filePath, protobuf::FileDescriptorProto & fileDescriptorProto,
										protobuf::DescriptorPool & pool) const;
		std::string GetUniqueIdentifierName() const;
		std::string DefaultValueAsString(const FieldDescriptor & field, bool quote_string_type = true) const;
		std::string TestValueAsString(const FieldDescriptor & field, bool isJava = true, bool isJSP = false) const ;
		std::string ObjCDataType(const FieldDescriptor & field) const ;
		std::string JavaDataType(const FieldDescriptor & field) const ;
		std::string XmlDataType(const FieldDescriptor & field) const ;
		std::string CppDataType(const FieldDescriptor & field) const ;
		std::string ProtoCppDataType(const FieldDescriptor & field) const ;
		std::string ProtoDataType(const FieldDescriptor & field) const;
		std::string MySQLDataType(const FieldDescriptor & field, size_t size = 0) const ;
		std::string ResponseNameCheckerAndGenerator(const Descriptor & message) const;
		bool isReverseAjaxEnable(const FileDescriptor & file)const;
		std::string GetFileNameFromFileDescriptor(const FileDescriptor* fileDescriptor) const;
		std::string GetProtoFileNameFromFileDescriptor(const FileDescriptor& fileDescriptor) const;

		// Maps names into Package Names Upto First .
		template <class DescriptorType>
		std::string PackageNameUptoFirstDot(const DescriptorType & descriptor) const;
		// Maps names into Package Names
		template <class DescriptorType>
		std::string PackageName(const DescriptorType & descriptor) const;

		std::string GetMessageURI(const Descriptor & message)const;
		// Get's Package directory name from Message Descriptor
		std::string GetPackageDirectoryName(const Descriptor & message) const;
		// Get's Package directory name
		std::string GetPackageDirectoryName(const FileDescriptor* file) const;
		inline std::string GetComponentVariableName(std::string varName, std::string componentName)const;
		inline std::string GetComponentArtifactName(const Descriptor & message, std::string componentName)const;
		inline std::string GetComponentPackageName(const Descriptor & message, std::string componentName)const;
		inline std::string GetComponentDirectoryName(const Descriptor & message, std::string componentName)const;
		inline std::string GetJavaComponentFileName(const FileDescriptor & file, std::string componentName)const;
		inline std::string GetJavaComponentFileName(const Descriptor & message, std::string componentName)const;
		inline std::string GetJavaComponentFullPathFileName(const Descriptor & message, std::string componentName)const;

		//Util
		template <class DescriptorType>
		std::string      ClassName(const DescriptorType & descriptor) const;

		template <class DescriptorType>
		std::string LowerCaseDescriptorName(const DescriptorType & descriptor) const;

		// Maps names into Unqualified(package name not prefixed) Class names
		template <class DescriptorType>
		std::string UnqualifiedClassOrEnumOrFieldName(const DescriptorType & descriptor) const;

		// Maps names into Fully Qualified(package name prefixed) Class names
		template <class DescriptorType>
		std::string QualifiedCppClassOrEnumName(const DescriptorType & descriptor) const;

		// Maps names into Fully Qualified(package name prefixed) Class names
		template <class DescriptorType>
		std::string QualifiedJavaClassOrEnumName(const DescriptorType & descriptor) const;

		std::string QualifiedCppTypeNameForField(const FieldDescriptor & field) const;
		std::string QualifiedJavaTypeNameForField(const FieldDescriptor & field) const;

		std::string VariableName(const FieldDescriptor & field) const;
		std::string ProtoCppVariableAccessorName(const FieldDescriptor & field) const ;
		std::string VariableGetterName(const FieldDescriptor & field) const;
		std::string VariableSetterName(const FieldDescriptor & field) const;

		FluxCodeGenerator():uniqueIdentifierPrefix("fCG_")
		{
			uniqueIdentifierSuffix[0] = 'a';
			uniqueIdentifierSuffix[1] = 'a';
			uniqueIdentifierSuffix[2] = '\0';
		}
		
		virtual ~FluxCodeGenerator(){}

		virtual bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;

};

class FluxErrorCollector : public protobuf::DescriptorPool::ErrorCollector
{
public:
	FluxErrorCollector() : protobuf::DescriptorPool::ErrorCollector() {}

	virtual void AddError(const std::string & fileName, const std::string & element_name, const protobuf::Message * descriptor,
				ErrorLocation location, const std::string & message)
	{ std::cout << "Build: " << message.c_str() << std::endl; }
};

void FluxCodeGenerator::LoadMappingInMessage(protobuf::Message * mappingMessage, const Descriptor & mappingMessageDescriptor) const
{
	// Load mapping file - filename derived from mappingMessageDescriptor name
	FILE * mappingFileHandle = ::fopen((std::string(MAPPING_DIR) + "/" + mappingMessageDescriptor.name() + "." + MAPPING_FILE_EXTENSION).c_str(), "r");
	protobuf::io::FileInputStream fs(fileno(mappingFileHandle));
	protobuf::TextFormat::Parse(&fs, mappingMessage);
	fs.Close();
}

std::string FluxCodeGenerator::GetMappingModelFilePath() const
{
#ifndef __unix
	//prefix path relative to executable 
	char dir[1024];
	std::string filePath = std::string(_getcwd(dir, 1000)) + MAPPING_MODEL_DIR;
#else //__unix
	std::string filePath = std::string(MAPPING_MODEL_DIR) + "/";//Extra '/' is ok having no '/' at end may create problems
#endif //__unix
	return filePath;
}

const protobuf::FileDescriptor * FluxCodeGenerator::OpenProto( std::string fileName, std::string filePath, protobuf::FileDescriptorProto & fileDescriptorProto,
								protobuf::DescriptorPool & pool) const
{
	FluxErrorCollector error;

	//Construct path
	std::string fullFileName = filePath + fileName;
	//Now Open proto file
	FILE * fd = fopen(fullFileName.c_str(),"r");
	if(!fd)
	{
		std::cout << "Can't load proto file: " << fullFileName << std::endl;
		return 0;
	}

	//We have the fd, create a protoStream out of it and use it to create a tokenizer
	protobuf::io::FileInputStream protoStream(fileno(fd));
	protobuf::io::Tokenizer tokenizer(&protoStream, 0);
	//Use the Parser and create a FileDescriptoProto
	protobuf::compiler::Parser parser;
	if(!parser.Parse(&tokenizer, &fileDescriptorProto))
	{
		std::cout << "Invalid Proto File: " << fullFileName << std::endl;
		return 0;
	}
	fclose(fd);
	//Bug in FileDescriptorProto - need to set file name manually
	fileDescriptorProto.set_name(fileName);//Only the name not the fullFileName

	for (int i=0; i < fileDescriptorProto.dependency().size(); i++)
	{
		//If this dependency file descriptor is already in Pool then just continue to add next dependency
		if(0 != pool.FindFileByName(fileDescriptorProto.dependency(i).c_str()))
			continue;
		protobuf::FileDescriptorProto *newFileDescriptorProto = new protobuf::FileDescriptorProto();
		OpenProto(fileDescriptorProto.dependency(i).c_str(), filePath, *newFileDescriptorProto, pool);
		if(0 == newFileDescriptorProto)
			return 0;
	}
	return pool.BuildFileCollectingErrors(fileDescriptorProto, &error);
} 

inline std::string FluxCodeGenerator::ResponseNameCheckerAndGenerator(const Descriptor & message) const
{	
	std::string strRequest=UnqualifiedClassOrEnumOrFieldName(message);
	std::string strResponse = message.options().GetExtension(FluxMsgRsp);
	std::string response="";
	if(0!= strResponse.length() && strResponse !="!")
	{
		response=strResponse;
	}
	return response;
}
//check file for reverse ajax
inline bool FluxCodeGenerator::isReverseAjaxEnable(const FileDescriptor & file)const
{
	bool notifyAnnotation=false;
	for (int i = 0; i < file.message_type_count(); ++i)
       
		{
             
			const Descriptor & message(*file.message_type(i));
			std::string strNotify = message.options().GetExtension(FluxMsgNotify);
			if(0 != strNotify.length() && strNotify !="!")
			{
				notifyAnnotation=true;
				break;
			}
		}
return notifyAnnotation;

}

//This is not thread safe - "Yet" - Simple mutex should do that if needed
inline std::string FluxCodeGenerator::GetUniqueIdentifierName() const 
{
	if('z' == uniqueIdentifierSuffix[1])
	{
		if('z' == uniqueIdentifierSuffix[0])
		{
			//Reset to prevent overflow
			uniqueIdentifierSuffix[0] = 'a';
			uniqueIdentifierSuffix[1] = 'a';
		}
		else
		{
			uniqueIdentifierSuffix[0]++;
		}
	}
	else
	{
		uniqueIdentifierSuffix[1]++;
	}
	return (uniqueIdentifierPrefix + uniqueIdentifierSuffix);
}

// Return's bare file name given a file descriptor *
inline std::string FluxCodeGenerator::GetFileNameFromFileDescriptor(const FileDescriptor* fileDescriptor) const 
{
	std::string protoFilename ( fileDescriptor->name());
	size_t slashposition=protoFilename.find_last_of ('/');
	size_t pos1 = protoFilename.find_first_of ('.');
	std::string sbstring = protoFilename.substr(slashposition+1,pos1);
	size_t pf = sbstring.find_first_of ('.');
	std::string file_name=sbstring.substr(0,pf); //file name to be created

	return file_name;
}

//Return .proto suffixed file name given a file descriptor
inline std::string FluxCodeGenerator::GetProtoFileNameFromFileDescriptor(const FileDescriptor& fileDescriptor) const 
{
	std::string retStrName (fileDescriptor.name());
        size_t pos = retStrName.find_last_of ('/');
	if(std::string::npos != pos)
        	retStrName = retStrName.substr(pos+1);
        return retStrName;
}

template <class DescriptorType>
inline std::string FluxCodeGenerator::PackageNameUptoFirstDot(const DescriptorType & descriptor) const 
{
	std::string tempName(descriptor.full_name());
	size_t pos = tempName.find_first_of('.');
	std::string name = tempName.substr(0,pos);
	return name;
}

template <class DescriptorType>
inline std::string FluxCodeGenerator::PackageName(const DescriptorType & descriptor) const 
{
	std::string tempName(descriptor.full_name());
	size_t pos = tempName.find_last_of('.');
	std::string name = tempName.substr(0,pos);
	return name;
}

std::string FluxCodeGenerator::GetMessageURI(const Descriptor & message)const
{
	std::string package = PackageName(message);
	std::string name =  ReplaceDotWithFullColon(package) + ":" + message.name();
	return name;
}

// Get's Package directory name from Message Descriptor
std::string FluxCodeGenerator::GetPackageDirectoryName(const Descriptor & message) const
{
	//find package name.
	std::string package=PackageName(message);
	std::string name = ReplaceDotWithSlash(package);
	return name;
}

// Get's Package directory name from Descriptor
std::string FluxCodeGenerator::GetPackageDirectoryName(const FileDescriptor* file) const
{
	//find package name.
	std::string package=file->package();
	size_t pos = package.find_last_of('.');
	std::string name = ReplaceDotWithSlash(package.substr(0,pos));
	return name;
}

inline std::string FluxCodeGenerator::GetComponentVariableName(std::string varName, std::string componentName)const
{
	return varName + UnderscoresToCapitalizedCamelCase(componentName);
}

inline std::string FluxCodeGenerator::GetComponentArtifactName(const Descriptor & message, std::string componentName)const
{
	return UnqualifiedClassOrEnumOrFieldName(message) + UnderscoresToCapitalizedCamelCase(componentName);
}

inline std::string FluxCodeGenerator::GetComponentPackageName(const Descriptor & message, std::string componentName)const
{
	return PackageName(message) + "." + componentName;
}

inline std::string FluxCodeGenerator::GetComponentDirectoryName(const Descriptor & message, std::string componentName)const
{
	return GetPackageDirectoryName(message) + "/" + componentName + "/";
}

inline std::string FluxCodeGenerator::GetJavaComponentFileName(const FileDescriptor & file, std::string componentName)const
{
	return GetFileNameFromFileDescriptor(&file) + UnderscoresToCapitalizedCamelCase(componentName) + ".java";
}

inline std::string FluxCodeGenerator::GetJavaComponentFileName(const Descriptor & message, std::string componentName)const
{
	return GetComponentArtifactName(message,componentName) + ".java";
}

inline std::string FluxCodeGenerator::GetJavaComponentFullPathFileName(const Descriptor & message, std::string componentName)const
{
	return GetComponentDirectoryName(message,componentName) + GetJavaComponentFileName(message,componentName);
}

template <class DescriptorType>
std::string FluxCodeGenerator::ClassName(const DescriptorType & descriptor) const 
{
   std::string name (descriptor.full_name());
   return name;
}

// Maps a Message name into a DB aligned lowercase unqualified name
template <class DescriptorType>
inline std::string FluxCodeGenerator::LowerCaseDescriptorName(const DescriptorType & descriptor) const 
{
    std::string retStrName (descriptor.full_name());
	google::protobuf::LowerString(&retStrName);
	size_t pos = retStrName.find_last_of ('.');
	retStrName = retStrName.substr(pos+1);
	return retStrName;
}


// Maps a Message name into a CPP Class unqualified name
template <class DescriptorType>
inline std::string FluxCodeGenerator::UnqualifiedClassOrEnumOrFieldName(const DescriptorType & descriptor) const 
{
    std::string name (descriptor.full_name());
	size_t pos = name.find_last_of ('.');
	name = name.substr(pos+1);
    return name;
}

// Maps a Message name into a fully qualified CPP Class name
template <class DescriptorType>
inline std::string FluxCodeGenerator::QualifiedCppClassOrEnumName(const DescriptorType & descriptor) const 
{
	std::string name (descriptor.full_name());
	std::string::iterator oit;
	for (oit = name.begin(); oit != name.end(); oit++)
	{
		size_t pos = name.find('.');
		if(std::string::npos == pos)
		{
			break;
		}
		std::string::iterator it = name.begin() + pos;
		for (;it != name.end(); it++)
		{		
			if(*it == '.')
			{
				name.replace(it,it+1,"::");
				break;
			}
		}
	}
	return name;
}

// Maps a Message fully qualified qualified name into a JAVA Class name
template <class DescriptorType>
inline std::string FluxCodeGenerator::QualifiedJavaClassOrEnumName(const DescriptorType & descriptor) const 
{
   std::string name (descriptor.full_name());
   return name;
}

inline std::string FluxCodeGenerator::QualifiedCppTypeNameForField(const FieldDescriptor & field) const 
{
	std::string strQualifiedCppTypeName;
	if(field.type() == FieldDescriptor::TYPE_MESSAGE)
	{
		//This field is a complex type
		strQualifiedCppTypeName = QualifiedCppClassOrEnumName(*field.message_type());
	}
	else if(field.type() == FieldDescriptor::TYPE_ENUM)
	{
		//This field is a enum type
		strQualifiedCppTypeName = QualifiedCppClassOrEnumName(*field.enum_type());
	}
	else
	{
		//All other simple types
		//: TODO: Handle int64 DateTime type here
		strQualifiedCppTypeName = CppDataType(field);
	}
	return strQualifiedCppTypeName;
}

inline std::string FluxCodeGenerator::QualifiedJavaTypeNameForField(const FieldDescriptor & field) const 
{
	std::string strQualifiedCppTypeName;
	if(field.type() == FieldDescriptor::TYPE_MESSAGE)
	{
		//This field is a complex type
		strQualifiedCppTypeName = QualifiedJavaClassOrEnumName(*field.message_type());
	}
	else if(field.type() == FieldDescriptor::TYPE_ENUM)
	{
		//This field is a enum type
		strQualifiedCppTypeName = QualifiedJavaClassOrEnumName(*field.enum_type());
	}
	else
	{
		//All other simple types
		//: TODO: Handle int64 DateTime type here
		strQualifiedCppTypeName = JavaDataType(field);
	}
	return strQualifiedCppTypeName;
}


inline std::string FluxCodeGenerator::VariableName(const FieldDescriptor & field) const 
{
	return UnderscoresToCamelCase(field);
}

std::string FluxCodeGenerator::ProtoCppVariableAccessorName(const FieldDescriptor & field) const 
{
	return (ToLowerCaseUnderscoreSeparated(VariableName(field)));
}

std::string FluxCodeGenerator::VariableGetterName(const FieldDescriptor & field) const 
{
	return (std::string("get") + UnderscoresToCapitalizedCamelCase(VariableName(field)));
}

std::string FluxCodeGenerator::VariableSetterName(const FieldDescriptor & field) const 
{
	return (std::string("set") + UnderscoresToCapitalizedCamelCase(VariableName(field)));
}

inline std::string FluxCodeGenerator::DefaultValueAsString(const FieldDescriptor & field, bool quote_string_type) const
{
	switch (field.type()) 
	{
		case FieldDescriptor::TYPE_INT32:
			return SimpleItoa(field.default_value_int32());
		case FieldDescriptor::TYPE_INT64:
			return SimpleItoa(field.default_value_int64());
		case FieldDescriptor::TYPE_UINT32:
			return SimpleItoa(field.default_value_uint32());
		case FieldDescriptor::TYPE_UINT64:
			return SimpleItoa(field.default_value_uint64());
		case FieldDescriptor::TYPE_FLOAT:
			return SimpleFtoa(field.default_value_float());
		case FieldDescriptor::TYPE_DOUBLE:
			return SimpleDtoa(field.default_value_double());
		case FieldDescriptor::TYPE_BOOL:
			return field.default_value_bool() ? "true" : "false";
		case FieldDescriptor::TYPE_STRING:
			if (quote_string_type)
				return "\"" + CEscape(field.default_value_string()) + "\"";
			//else to fall through (non-qupte std::string type handeled as bytes)
		case FieldDescriptor::TYPE_BYTES:
			return CEscape(field.default_value_string());
		case FieldDescriptor::TYPE_ENUM:
			return QualifiedCppClassOrEnumName(*field.enum_type()) + "::" + field.default_value_enum()->name();
		case FieldDescriptor::TYPE_MESSAGE:
			return "NA";
		default:
			return "DefaultValueAsString-UnSupportedFieldTypeRequest";
	}
	return "DefaultValueAsString-UnreachableCodeReached";
}

inline std::string FluxCodeGenerator::TestValueAsString(const FieldDescriptor & field, bool isJava, bool isJSP) const 
{
	static unsigned int testUInt32 = 0x7FFFFFFE;
	static unsigned long long testUInt64 = 0x7FFFFFFFFFFFFFFE;
	static float testFloat = 0.1;
	static double testDouble = 0.999999999999;
	static bool testBool = false;
	static std::string testString = "SampleString";
	static int testStringId = 10000;
	static std::string testBytes = "SampleBytes";
	static int testBytesId = 50000;

	//Read value options
	std::string strFieldValueMinimum = field.options().GetExtension(FluxFldValMin);
	std::string strFieldValueMaximum = field.options().GetExtension(FluxFldValMax);
	std::string strFieldValueList = field.options().GetExtension(FluxFldValList);
	std::vector<std::string> valueVector;
	std::string strMidVal;
	if(0 != strFieldValueList.length())
	{
		//The valid values come from a list, the the value be what is found in middle of the list
		SplitStringUsing(strFieldValueList,",",&valueVector);
		strMidVal = valueVector[(valueVector.size()/2)];
	}

  	switch (field.type()) 
	  	{
	    case FieldDescriptor::TYPE_INT32:
	    case FieldDescriptor::TYPE_UINT32:
			{
				unsigned int retVal = 0;
				testUInt32 -= 1;
				if(0 != strFieldValueMinimum.length())
				{
					if(0 != strFieldValueMaximum.length())
					{
						//We have well defined Min and Max, let the value be min+max / 2
						retVal = (strtou32(strFieldValueMinimum.c_str(),0,0) + strtou32 (strFieldValueMaximum.c_str(),0,0))/2;
					}
					else
					{
						//Only Min defined, let the value be Min + testDouble
						retVal = strtou32(strFieldValueMinimum.c_str(),0,0) + 1;
					}
				}
				else if(0 != strFieldValueMaximum.length())
				{
					//Only Maximum defined, let the value be Max - testDouble;
					retVal = strtou32 (strFieldValueMaximum.c_str(),0,0) - 1;
				}
				else if(0 != strFieldValueList.length())
				{
					//The valid values come from a list, the the value be what is found in middle of the list
					retVal = strtou32(strMidVal.c_str(),0,0);
				}
				else
				{
					//Well no annotation set, just send any value
				  	retVal = testUInt32;
				}
				//Final Return Value
				std::string retString = SimpleItoa(retVal);
				return retString;
	    	}

	    case FieldDescriptor::TYPE_INT64:
	    case FieldDescriptor::TYPE_UINT64:
			{
				unsigned long long retVal = 0;
				if(0 != strFieldValueMinimum.length())
				{
					if(0 != strFieldValueMaximum.length())
					{
						//We have well defined Min and Max, let the value be min+max / 2
						retVal = (strtou64(strFieldValueMinimum.c_str(),0,0) + strtou64 (strFieldValueMaximum.c_str(),0,0))/2;
					}
					else
					{
						//Only Min defined, let the value be Min + testDouble
						retVal = strtou64(strFieldValueMinimum.c_str(),0,0) + 1;
					}
				}
				else if(0 != strFieldValueMaximum.length())
				{
					//Only Maximum defined, let the value be Max - testDouble;
					retVal = strtou64 (strFieldValueMaximum.c_str(),0,0) - 1;
				}
				else if(0 != strFieldValueList.length())
				{
					//The valid values come from a list, the the value be what is found in middle of the list
					retVal = strtou64(strMidVal.c_str(),0,0);
				}
				else
				{
					//Well no annotation set, just send any value
				  	retVal = testUInt64 -= 1;
				}
				//Final Return Value
				std::string retString = SimpleItoa(retVal);
				if(!isJSP)
				{
					retString + "L";
				}
				return retString;
	    	}
	    case FieldDescriptor::TYPE_FLOAT:
			{
				double retVal = 0.0;
				if(0 != strFieldValueMinimum.length())
				{
					if(0 != strFieldValueMaximum.length())
					{
						//We have well defined Min and Max, let the value be min+max / 2
						retVal = (atof(strFieldValueMinimum.c_str()) + atof (strFieldValueMaximum.c_str()))/2;
					}
					else
					{
						//Only Min defined, let the value be Min + testDouble
						retVal = atof(strFieldValueMinimum.c_str()) + 0.99;
					}
				}
				else if(0 != strFieldValueMaximum.length())
				{
					//Only Maximum defined, let the value be Max - testDouble;
					retVal = atof (strFieldValueMaximum.c_str()) - 0.99;
				}
				else if(0 != strFieldValueList.length())
				{
					//The valid values come from a list, the the value be what is found in middle of the list
					retVal = atof(strMidVal.c_str());
				}
				else
				{
					//Well no annotation set, just send any value
				  	retVal = testFloat += 1;
				}
				//Final Return Value
				std::string retString = SimpleFtoa(static_cast<float>(retVal));
				//Force double if the retVal is a whole number
				if(retVal == (static_cast<int>(retVal)))
					 retString += ".0";
				return retString;
	    	}
	    case FieldDescriptor::TYPE_DOUBLE:
			{
				double retVal = 0.0;
				if(0 != strFieldValueMinimum.length())
				{
					if(0 != strFieldValueMaximum.length())
					{
						//We have well defined Min and Max, let the value be min+max / 2
						retVal = (atof(strFieldValueMinimum.c_str()) + atof (strFieldValueMaximum.c_str()))/2;
					}
					else
					{
						//Only Min defined, let the value be Min + testDouble
						retVal = atof(strFieldValueMinimum.c_str()) + 0.99;
					}
				}
				else if(0 != strFieldValueMaximum.length())
				{
					//Only Maximum defined, let the value be Max - testDouble;
					retVal = atof (strFieldValueMaximum.c_str()) - 0.99;
				}
				else if(0 != strFieldValueList.length())
				{
					//The valid values come from a list, the the value be what is found in middle of the list
					retVal = atof(strMidVal.c_str());
				}
				else
				{
					//Well no annotation set, just send any value
				  	retVal = testDouble += 1;
				}
				//Final Return Value
				std::string retString = SimpleDtoa(retVal);
				//Force double if the retVal is a whole number
				if(retVal == (static_cast<int>(retVal)))
					 retString += ".0";
				return retString;
	    	}
	    case FieldDescriptor::TYPE_BOOL:
		  testBool = testBool ? false : true;
	      return testBool ? "true" : "false";

	    case FieldDescriptor::TYPE_STRING:
			{
				std::string retString;
				if(0 != strFieldValueList.length())
				{
					//The valid values come from a list, the the value be what is found in middle of the list
					retString = strMidVal;
				}
				else
				{
					//Well no annotation set, just send any value
					retString = SimpleItoa(testStringId++) + testString;
				}
				return (std::string("\"") + retString + "\"");
	    	}
		  
	    case FieldDescriptor::TYPE_BYTES:
	      return SimpleItoa(testBytesId++) + testBytes;
		  
	    case FieldDescriptor::TYPE_ENUM:
			{
				const EnumDescriptor &enumDescp (*field.enum_type()) ;
				const EnumValueDescriptor &ev (*enumDescp.value(1));//Always return 2nd (starts from 0) value as enum test value
				if(isJava)
					return QualifiedJavaClassOrEnumName(*field.enum_type()) + "." + ev.name();
				else
					return QualifiedCppClassOrEnumName(*field.enum_type()) + "::" + ev.name();
		    }
	    case FieldDescriptor::TYPE_MESSAGE:
	      return "null";
		default:
			return "TestValueAsString-UnSupportedFieldTypeRequest";
	}
	return "TestValueAsString-UnreachableCodeReached";  
}

//This statement returns data type of the variable
inline std::string FluxCodeGenerator::ObjCDataType(const FieldDescriptor & field) const 
{
   switch (field.type()) 
    {
     case FieldDescriptor::TYPE_INT32:
       return "NSNumber";
     case FieldDescriptor::TYPE_INT64:
       return "NSNumber";
     case FieldDescriptor::TYPE_UINT32:
       return "NSNumber";
     case FieldDescriptor::TYPE_UINT64:
       return "NSNumber";
     case FieldDescriptor::TYPE_FLOAT:
       return "NSNumber";
     case FieldDescriptor::TYPE_DOUBLE:
       return "NSNumber";
     case FieldDescriptor::TYPE_BOOL:
       return "NSNumber";
     case FieldDescriptor::TYPE_STRING:
       return "NSString";
     case FieldDescriptor::TYPE_BYTES:
       return "NSMutableArray";
     case FieldDescriptor::TYPE_ENUM:
       return "enum";
     case FieldDescriptor::TYPE_MESSAGE:
       return "message";
	default:
	   return "JavaDataType-UnSupportedFieldTypeRequest";
   }
   return "JavaDataType-UnreachableCodeReached";
}

//This statement returns data type of the variable
inline std::string FluxCodeGenerator::JavaDataType(const FieldDescriptor & field) const 
{
   switch (field.type()) 
    {
     case FieldDescriptor::TYPE_INT32:
       return "Integer";
     case FieldDescriptor::TYPE_INT64:
       return "Long";
     case FieldDescriptor::TYPE_UINT32:
       return "Integer";
     case FieldDescriptor::TYPE_UINT64:
       return "Integer";
     case FieldDescriptor::TYPE_FLOAT:
       return "Float";
     case FieldDescriptor::TYPE_DOUBLE:
       return "Double";
     case FieldDescriptor::TYPE_BOOL:
       return "Boolean";
     case FieldDescriptor::TYPE_STRING:
       return "String";
     case FieldDescriptor::TYPE_BYTES:
       return "Byte";
     case FieldDescriptor::TYPE_ENUM:
       return "Enumeration";
     case FieldDescriptor::TYPE_MESSAGE:
       return "message";
	default:
	   return "JavaDataType-UnSupportedFieldTypeRequest";
   }
   return "JavaDataType-UnreachableCodeReached";
}

//This statement returns data type of the variable
inline std::string FluxCodeGenerator::XmlDataType(const FieldDescriptor & field) const 
{
   switch (field.type()) 
    {
     case FieldDescriptor::TYPE_INT32:
       return "int";
     case FieldDescriptor::TYPE_INT64:
       return "long";
     case FieldDescriptor::TYPE_UINT32:
       return "int";
     case FieldDescriptor::TYPE_UINT64:
       return "long";
     case FieldDescriptor::TYPE_FLOAT:
       return "float";
     case FieldDescriptor::TYPE_DOUBLE:
       return "double";
     case FieldDescriptor::TYPE_BOOL:
       return "boolean";
     case FieldDescriptor::TYPE_STRING:
       return "String";
     case FieldDescriptor::TYPE_BYTES:
       return "byte";
     case FieldDescriptor::TYPE_ENUM:
       return "Enumeration";
     case FieldDescriptor::TYPE_MESSAGE:
       return "String";
   default:
	   return "XmlDataType-UnSupportedFieldTypeRequest";
   }
   return "XmlDataType-UnreachableCodeReached";
}

inline std::string FluxCodeGenerator::CppDataType(const FieldDescriptor & field) const 
{
  	switch (field.cpp_type()) 
	{
	    case FieldDescriptor::CPPTYPE_INT32:
	      return "int32";
	    case FieldDescriptor::CPPTYPE_INT64:
	      return "int64";
	    case FieldDescriptor::CPPTYPE_UINT32:
	      return "uint32";
	    case FieldDescriptor::CPPTYPE_UINT64:
	      return "uint64";
	    case FieldDescriptor::CPPTYPE_FLOAT:
		  return "float";
	    case FieldDescriptor::CPPTYPE_DOUBLE:
		  return "double";
	    case FieldDescriptor::CPPTYPE_BOOL:
		  return "bool";
	    case FieldDescriptor::CPPTYPE_STRING:
	      return "std::string";
	    case FieldDescriptor::CPPTYPE_ENUM:
	      return "enum";
	    case FieldDescriptor::CPPTYPE_MESSAGE:
	      return "message";
	  default:
		  return "CppDataType-UnSupportedFieldTypeRequest";
	  }
  return "CppDataType-UnreachableCodeReached";
}

inline std::string FluxCodeGenerator::ProtoCppDataType(const FieldDescriptor & field) const 
{
  	switch (field.cpp_type()) 
  	{
	    case FieldDescriptor::CPPTYPE_INT32:
	      return "int32";
	    case FieldDescriptor::CPPTYPE_INT64:
	      return "int64";
	    case FieldDescriptor::CPPTYPE_UINT32:
	      return "uint32";
	    case FieldDescriptor::CPPTYPE_UINT64:
	      return "uint64";
	    case FieldDescriptor::CPPTYPE_FLOAT:
		  return "float";
	    case FieldDescriptor::CPPTYPE_DOUBLE:
		  return "double";
	    case FieldDescriptor::CPPTYPE_BOOL:
		  return "bool";
	    case FieldDescriptor::CPPTYPE_STRING:
	      return "string";
	    case FieldDescriptor::CPPTYPE_ENUM:
	      return "enum";
	    case FieldDescriptor::CPPTYPE_MESSAGE:
	      return "message";
	  default:
		  return "ProtoCppDataType-UnSupportedFieldTypeRequest";
	  }
  return "ProtoCppDataType-UnreachableCodeReached";
}

inline std::string FluxCodeGenerator::ProtoDataType(const FieldDescriptor & field) const
{
	switch (field.type())
	{
		case FieldDescriptor::TYPE_INT32:
			return "int32";
		case FieldDescriptor::TYPE_INT64:
			return "int64";
		case FieldDescriptor::TYPE_UINT32:
			return "uint32";
		case FieldDescriptor::TYPE_UINT64:
			return "uint64";
		case FieldDescriptor::TYPE_FLOAT:
			return "float";
		case FieldDescriptor::TYPE_DOUBLE:
			return "double";
		case FieldDescriptor::TYPE_BOOL:
			return "bool";
		case FieldDescriptor::TYPE_STRING:
			return "string";
		case FieldDescriptor::TYPE_BYTES:
			return "bytes";
		case FieldDescriptor::TYPE_ENUM:
			return "enum";
		case FieldDescriptor::TYPE_MESSAGE:
			return "message";
		case FieldDescriptor::TYPE_FIXED32:
			return "fixed32";
		case FieldDescriptor::TYPE_FIXED64:
			return "fixed64";
		case FieldDescriptor::TYPE_SFIXED32:
			return "sfixed32";
		case FieldDescriptor::TYPE_SFIXED64:
			return "sfixed64";
		case FieldDescriptor::TYPE_SINT32:
			return "sint32";
		case FieldDescriptor::TYPE_SINT64:
			return "sint64";
		default:
			return "ProtoDataType-UnSupportedFieldTypeRequest";
	}
	return "ProtoDataType-UnreachableCodeReached";
}

inline std::string FluxCodeGenerator::MySQLDataType(const FieldDescriptor & field, size_t size) const 
{
	std::string strSize = "255";
	if(0 != size)
		strSize = SimpleItoa(size);
  	switch (field.type()) 
	{
		case FieldDescriptor::TYPE_INT32:
			return "INT";
		case FieldDescriptor::TYPE_INT64:
			return "BIGINT";
		case FieldDescriptor::TYPE_UINT32:
			return "INT unsigned";
		case FieldDescriptor::TYPE_UINT64:
			return "BIGINT unsigned";
		case FieldDescriptor::TYPE_FLOAT:
			return "FLOAT";
		case FieldDescriptor::TYPE_DOUBLE:
			return "DOUBLE";
		case FieldDescriptor::TYPE_BOOL:
			return "BOOL";
		case FieldDescriptor::TYPE_STRING:
			return "varchar(255)";
		case FieldDescriptor::TYPE_BYTES:
			return (size?"varchar(" + strSize + ")":"varchar(255)");
		case FieldDescriptor::TYPE_ENUM:
			return "INT";
		default:
			return "MySQLDataType-UnSupportedFieldTypeRequest";	
	}
	return "MySQLDataType-UnreachableCodeReached";
}


inline void FluxCodeGenerator::PrintMessage(io::Printer &printer, const Descriptor & message) const 
{
	printer.Indent();
	printer.Print(
	"`name`\n",
		  "name", UnqualifiedClassOrEnumOrFieldName(message)
	);
	printer.Indent();
	printer.Outdent();
	printer.Outdent();
}

inline void FluxCodeGenerator::PrintMessages(io::Printer &printer, const FileDescriptor & file) const 
{
	for (int i = 0; i < file.message_type_count(); ++i) 
	{
		PrintMessage(printer, *file.message_type(i));
	}
}


inline bool FluxCodeGenerator::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	std::string output_filename = "../temp/" + file->name() + "_default.txt";
	// Generate main file.
	scoped_ptr<io::ZeroCopyOutputStream> output(
		output_directory->Open(output_filename)
	);

	io::Printer printer(output.get(), '`');
	PrintMessages  (printer, *file);
	return true;
}


#endif //FluxCodeGenerator_h
