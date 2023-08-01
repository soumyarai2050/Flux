#include "FluxUtil.h"

#ifndef FluxORMUtil_h
#define FluxORMUtil_h 1

#include <google/protobuf/wire_format.h>
#include <google/protobuf/wire_format_lite.h>
#include <google/protobuf/wire_format_lite_inl.h>


#include <google/protobuf/compiler/plugin.h>
#include <google/protobuf/compiler/code_generator.h>

#include <google/protobuf/io/printer.h>
#include <google/protobuf/io/zero_copy_stream.h>

#include "flux_options.pb.h"
#include "FluxMessageUtil.h"

#define FLUX_ORM_CREATE_UPDATE_OR_DELETE "saveOrUpdate"
#define FLUX_ORM_READ "read"

//FluxMsgOrmCreateUpdateOrDeleteClasses helpers
class OrmCreateUpdateOrDeleteClass
{
	public:
		OrmCreateUpdateOrDeleteClass(std::string& strPersistenceClassPair )
		{
			//Common temporary resource
			std::vector<std::string> tempRes;
			
			//Now Populate respTypeName and respVarName from strRespPair			
			SplitStringUsing(strPersistenceClassPair, ",", &tempRes);
			persistenceClassTypeName = tempRes[0];
			persistenceClassVarName = (tempRes.size()>1)?tempRes[1]:"";
			
			//Finally var name if that is empty
			if(0 == persistenceClassVarName.length())
			{
				persistenceClassVarName = UnderscoresToCamelCase(persistenceClassTypeName);
			}
			//Done, all populated - code can use these types as if it all was well defined.
		}
		
		std::string getPersistenceClassTypeName()const{return persistenceClassTypeName;}
		std::string getPersistenceClassVarName()const{return persistenceClassVarName;}
		std::string getCapitalizedCamelCasePersistenceClassVarName()const{return UnderscoresToCapitalizedCamelCase(persistenceClassVarName);}
	private:
		std::string	persistenceClassTypeName;
		std::string	persistenceClassVarName;
};

class OrmCreateUpdateOrDeleteClasses
{
	public:
		OrmCreateUpdateOrDeleteClasses(const Descriptor & message):isOptionSet(false)
		{
			//Get FluxMsgOrmReadRespClasses option value
			std::string ormCreateUpdateOrDeleteClasses = message.options().GetExtension(FluxMsgOrmCreateUpdateOrDeleteClasses);
			if(0 != ormCreateUpdateOrDeleteClasses.length())
			{
				//Strip all spaces out
				ormCreateUpdateOrDeleteClasses.erase(std::remove_if(ormCreateUpdateOrDeleteClasses.begin(),ormCreateUpdateOrDeleteClasses.end(), 
												::isspace), ormCreateUpdateOrDeleteClasses.end());
				//Now take action
				std::vector<std::string> tempRes;
				SplitStringUsing(ormCreateUpdateOrDeleteClasses, ":", &tempRes);
				for(unsigned int i = 0; i < tempRes.size(); i++)
				{
					OrmCreateUpdateOrDeleteClass *ptrOrmCreateUpdateOrDeleteClass = new OrmCreateUpdateOrDeleteClass(tempRes[i]);
					ormCreateUpdateOrDeleteClassPtrVector.push_back(ptrOrmCreateUpdateOrDeleteClass);
				}
				isOptionSet = true;
			}
		}
		size_t size() const
		{
			return ormCreateUpdateOrDeleteClassPtrVector.size();
		}
		OrmCreateUpdateOrDeleteClass& operator[] (const unsigned int index)
		{
			if(index >= size())
				throw "Invalid Size Passed";
			//else just return required value
			return (*(ormCreateUpdateOrDeleteClassPtrVector[index]));
		}
		bool IsOptionSet()const{return isOptionSet;}
		static bool StyleAdjustedOrmCreateUpdateOrDeleteClassesOption(std::string& reqResp)
		{
			std::string ormCreateUpdateOrDeleteClasses = reqResp;
			if(0 != ormCreateUpdateOrDeleteClasses.length())
			{
				//Strip all spaces out
				ormCreateUpdateOrDeleteClasses.erase(std::remove_if(ormCreateUpdateOrDeleteClasses.begin(),ormCreateUpdateOrDeleteClasses.end(), 
												::isspace), ormCreateUpdateOrDeleteClasses.end());
				//Now take action
				std::vector<std::string> tempRes;
				SplitStringUsing(ormCreateUpdateOrDeleteClasses, ":", &tempRes);
				for(unsigned int i = 0; i < tempRes.size(); i++)
				{
					OrmCreateUpdateOrDeleteClass *ptrOrmCreateUpdateOrDeleteClass = new OrmCreateUpdateOrDeleteClass(tempRes[i]);
					//Now update the reqResp string
					if(0 == i)
						reqResp = ptrOrmCreateUpdateOrDeleteClass->getPersistenceClassTypeName(); 
					else
						reqResp += (std::string(":") + ptrOrmCreateUpdateOrDeleteClass->getPersistenceClassTypeName());

					if(ptrOrmCreateUpdateOrDeleteClass->getPersistenceClassVarName() != "")
						reqResp += (std::string(",") + ToLowerCaseUnderscoreSeparated(ptrOrmCreateUpdateOrDeleteClass->getPersistenceClassVarName()));
				}
			}
			return true;
		}
	private:
		std::vector<OrmCreateUpdateOrDeleteClass*> ormCreateUpdateOrDeleteClassPtrVector;
		bool isOptionSet;
};


//FluxMsgOrmReadRespClasses Helpers
class OrmReadRespClass
{
	public:
		OrmReadRespClass(std::string& strRespPair )
		{
			//Common temporary resource
			std::vector<std::string> tempRes;
			//Populate respTypeName and respVarName from strRespPair			
			SplitStringUsing(strRespPair, ",", &tempRes);
			respTypeName = tempRes[0];
			respVarName = (tempRes.size()>1)?tempRes[1]:"";

			//Finally fill all those that are empty
			if(0 == respVarName.length())
			{
				respVarName = UnderscoresToCamelCase(respTypeName);
			}
			//Done, all populated - code can use these types as if it all was well defined.
		}
		
		std::string getRespTypeName()const{return respTypeName;}
		std::string getRespVarName()const{return respVarName;}
		std::string getCapitalizedCamelCaseRespVarName()const{return UnderscoresToCapitalizedCamelCase(respVarName);}
	private:
		std::string	respTypeName;
		std::string	respVarName;
};

class OrmReadRespClasses
{
	public:
		OrmReadRespClasses(const Descriptor & message):isOptionSet(false), isRepeatType(false)
		{
			//Get FluxMsgRsp value for nested type repeat check
			std::string strFluxMsgRsp = message.options().GetExtension(FluxMsgRsp);
			//Get FluxMsgOrmReadRespClasses option value
			std::string strFluxMsgOrmReadRespClasses = message.options().GetExtension(FluxMsgOrmReadRespClasses);
			if(0 != strFluxMsgOrmReadRespClasses.length())
			{
				//Strip all spaces out
				strFluxMsgOrmReadRespClasses.erase(std::remove_if(strFluxMsgOrmReadRespClasses.begin(),strFluxMsgOrmReadRespClasses.end(), 
												::isspace), strFluxMsgOrmReadRespClasses.end());
				//Now take action
				std::vector<std::string> tempRes;
				SplitStringUsing(strFluxMsgOrmReadRespClasses, ":", &tempRes);
				for(unsigned int i = 0; i < tempRes.size(); i++)
				{
					OrmReadRespClass *ptrOrmReadRespClass = new OrmReadRespClass(tempRes[i]);
					ormRespAndQueryPtrVector.push_back(ptrOrmReadRespClass);					
					//If first iteration update isRepeatType status with newly inserted OrmCreateUpdateOrDeleteClass is a repeat type status
					bool ormReadRespClassVarRepeatType = IsNestedFieldRepeated(strFluxMsgRsp, ptrOrmReadRespClass->getRespTypeName(), ptrOrmReadRespClass->getRespVarName(), *(message.file()));
					if(0 == i)
					{
						isRepeatType = ormReadRespClassVarRepeatType;
					}
					else if(ormReadRespClassVarRepeatType != isRepeatType )
					{
						//If the newly inserted OrmCreateUpdateOrDeleteClass's repeat type is NOT same as isRepeatType then throw exception
						throw "Newly inserted OrmCreateUpdateOrDeleteClass's repeat type is NOT same as previously inserted OrmCreateUpdateOrDeleteClass's repeat type - Mixed Type NOT Supported";
					}
				}
				isOptionSet = true;
			}
		}
		
		size_t size()const
		{
			return ormRespAndQueryPtrVector.size();
		}
		OrmReadRespClass& operator[] (const unsigned int index)
		{
			if(index >= size())
				throw "Invalid Size Passed";
			//else just return required value
			return (*(ormRespAndQueryPtrVector[index]));
		}
		bool IsOptionSet()const{return isOptionSet;}
		bool IsRepeatType(){return isRepeatType;}
		static bool StyleAdjustedOrmReadRespClassesOption(std::string& reqResp)
		{
			//Get FluxMsgOrmReadRespClasses option value
			std::string strFluxMsgOrmReadRespClasses = reqResp;
			if(0 != strFluxMsgOrmReadRespClasses.length())
			{
				//Strip all spaces out
				strFluxMsgOrmReadRespClasses.erase(std::remove_if(strFluxMsgOrmReadRespClasses.begin(),strFluxMsgOrmReadRespClasses.end(), 
												::isspace), strFluxMsgOrmReadRespClasses.end());
				//Now take action
				std::vector<std::string> tempRes;
				SplitStringUsing(strFluxMsgOrmReadRespClasses, ":", &tempRes);
				for(unsigned int i = 0; i < tempRes.size(); i++)
				{
					OrmReadRespClass *ptrOrmReadRespClass = new OrmReadRespClass(tempRes[i]);
					//Now update the reqResp string
					if(0 == i)
						reqResp = ptrOrmReadRespClass->getRespTypeName(); 
					else
						reqResp += (std::string(":") + ptrOrmReadRespClass->getRespTypeName());
			
					if(ptrOrmReadRespClass->getRespVarName() != "")
						reqResp += (std::string(",") + ToLowerCaseUnderscoreSeparated(ptrOrmReadRespClass->getRespVarName()));
				}
			}
			return true;
		}
	private:
		std::vector<OrmReadRespClass*> ormRespAndQueryPtrVector;
		bool isOptionSet;
		bool isRepeatType;
};


#endif //FluxORMUtil_h
