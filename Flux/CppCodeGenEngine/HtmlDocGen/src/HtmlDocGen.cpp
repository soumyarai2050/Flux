/**
 * Protocol Buffer Class Standard POCO Compatibility Generator Plugin
 * 
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>
#include <FluxFileUtil.h>

class HtmlDocGen: public FluxCodeGenerator 
{
	public:
		void PrintField	(io::Printer &printer, const FieldDescriptor &field, 
						 std::map<std::string, std::string> & fieldAttributeMap) const;
		void ComplexTablePrint    (const Descriptor & messageDescriptor, io::Printer & printer,std::map<std::string, std::string> & messageNameMap) const;
		
		void PrintMessage   (const Descriptor & messageDescriptor, io::Printer & printer) const;
		void PrintMessageExchangeTable	(const FileDescriptor & fileDescriptor, io::Printer & printer) const;
		void PrintMessages	(const FileDescriptor & fileDescriptor, io::Printer & printer) const;
		void PrintFiles (const FileDescriptor* file, io::Printer & printer) const;
		
		HtmlDocGen(){}
		bool Generate(const FileDescriptor* file, const std::string& parameter, OutputDirectory* output_directory, std::string* error) const;
};

void HtmlDocGen::PrintField	(io::Printer &printer, const FieldDescriptor &field, 
										 std::map<std::string, std::string> & fieldAttributeMap) const
{
	bool isComplex = false;
	if (FieldDescriptor::TYPE_MESSAGE == field.type()) 
	{
		isComplex = true;
	}

	if (field.is_repeated()) 
	{
		if(isComplex)
		{
			printer.Indent();
			printer.Print(fieldAttributeMap,"<tr><td width=300><p class=start  style=\"font-size:11;\">`field_name`</p></td>\n");
			printer.Print(fieldAttributeMap,"<td width=300><a href=#`unqualified_type`><p class=start  style=\"font-size:11;\"><b>`unqualified_type`<b></p></a></td>\n");
			printer.Print("<td width=300><p class=start  style=\"font-size:11;\">Field Specific Comment</p></td></tr>\n");
			printer.Outdent();
		}
		else
		{
			printer.Indent();
			printer.Print(fieldAttributeMap,"<tr><td width=300><p class=start  style=\"font-size:11;\">`field_name`</p></td>\n");
			printer.Print(fieldAttributeMap,"<td width=300><p class=start  style=\"font-size:11;\">`qualified_java_type`</p></td>\n");
			printer.Print("<td width=300><p class=start  style=\"font-size:11;\">Field Specific Comment</p></td></tr>\n");
			printer.Outdent();		
		}
	}
	else 
	{
		// Non repeated field
		if(isComplex)
		{
			
			printer.Indent();
			printer.Print(fieldAttributeMap,"<tr><td width=300><p class=start  style=\"font-size:11;\">`field_name`</p></td>\n");
			printer.Print(fieldAttributeMap,"<td width=300><a href=#`unqualified_type`><p class=start  style=\"font-size:11;\"><b>`unqualified_type`<b></p></a></td>\n");
			printer.Print("<td width=300><p class=start  style=\"font-size:11;\">Field Specific Comment</p></td></tr>\n");
			printer.Outdent();
		}
		else
		{
			//Within simple type we have 4 cases to handle 
			//Strings
			//Enums
			//Rest of It
			//DateTime (Protobuf representation is long)
			/* Default Values - Handeling Strings*/
			switch(field.type())
			{
				case FieldDescriptor::TYPE_STRING:
					{
						printer.Indent();
						printer.Print(fieldAttributeMap,"<tr><td width=300><p class=start  style=\"font-size:11;\">`field_name`</p></td>\n");
						printer.Print(fieldAttributeMap,"<td width=300><p class=start  style=\"font-size:11;\">`qualified_java_type`</p></td>\n");
						printer.Print("<td width=300><p class=start  style=\"font-size:11;\">Field Specific Comment</p></td></tr>\n");
						printer.Outdent();			
					}
					break;
				case FieldDescriptor::TYPE_ENUM:
					{
						printer.Indent();
			printer.Print(fieldAttributeMap,"<tr><td width=300><p class=start  style=\"font-size:11;\">`field_name`</p></td>\n");
			printer.Print(fieldAttributeMap,"<td width=300><a href=#`unqualified_type`><p class=start  style=\"font-size:11;\"><b>`unqualified_type`<b></p></a></td>\n");
			printer.Print("<td width=300><p class=start style=\"font-size:11;\">Field Specific Comment</p></td></tr>\n");
			printer.Outdent();
					}
					break;
				case FieldDescriptor::TYPE_INT64:
				{
					//Get Default
					//An int64 can or can not be a date time. If its a datetime field, it should have FluxFldValDateTime option set
					std::string strFluxFldTestVal=field.options().GetExtension(FluxFldValDateTime);
					if(0 != strFluxFldTestVal.length())
					{
						//This is a date time field, handle it like that - we should have imported time-support already
					}
					else
					{
						//This is a int64 simple type field handle here
						printer.Indent();
						printer.Print(fieldAttributeMap,"<tr><td width=300><p class=start  style=\"font-size:11;\">`field_name`</p></td>\n");
						printer.Print(fieldAttributeMap,"<td width=300><p class=start  style=\"font-size:11;\">`qualified_java_type`</p></td>\n");
						printer.Print("<td width=300><p class=start  style=\"font-size:11;\">Field Specific Comment</p></td></tr>\n");
						printer.Outdent();				
					}
					break;
				}
				default:
					//All other simple types falll in this case handle here
					{
						//This is any other simple type field, handle here
						printer.Indent();
						printer.Print(fieldAttributeMap,"<tr><td width=300><p class=start  style=\"font-size:11;\">`field_name`</p></td>\n");
						printer.Print(fieldAttributeMap,"<td width=300><p class=start  style=\"font-size:11;\">`qualified_java_type`</p></td>\n");
						printer.Print("<td width=300><p class=start  style=\"font-size:11;\">Field Specific Comment</p></td></tr>\n");
						printer.Outdent();	
					}
			}
		}
	}
}
void HtmlDocGen::ComplexTablePrint(const Descriptor &messageDescriptor, io::Printer & printer, std::map<std::string, std::string> & messageNameMap) const
{
	for (int i = 0; i < messageDescriptor.field_count(); ++i) 
	{
		std::map<std::string, std::string> fieldAttributeMap;
		const FieldDescriptor &field ( *messageDescriptor.field(i) );
		fieldAttributeMap["field_name"] = VariableName(field);
		if(field.type() == FieldDescriptor::TYPE_MESSAGE)
		{
			fieldAttributeMap["unqualified_type"] = (*field.message_type()).name();
			if(messageNameMap.find((*field.message_type()).name()) == messageNameMap.end())
			{	
				if (field.is_repeated()) 
				{
					//empty
				}
				else
				{	printer.Print("<br>");
					printer.Print(fieldAttributeMap,"<h><a id=`unqualified_type`><p class=normal style=\"font-size:11;\"><b>`unqualified_type`</b></p></a></h>\n");
					printer.Print("<p class=normal style=\"padding-left: 250px;\" style=\"font-size:11;\">Message Specific Comment</p>\n");
					printer.Print("<table width=900 style=\"border:1px solid; border-top-color:#FF920D; border-bottom-color:#FF920D;border-right-width:0;border-left-width:0;\">\n");
					printer.Print("<tr><td width=300><p class=start style=\"font-size:11;\"><b>Field Name</b></p></td>\n<td width=308><p class=start style=\"font-size:11;\"><b>Field Type</b></p></td>\n<td width=308><p class=start style=\"font-size:11;\"><b>Field Description</b></p></td></tr>\n");
					printer.Indent();
					PrintMessage(*field.message_type(),printer);
					printer.Print("</table>\n");
					ComplexTablePrint(*field.message_type(),printer,messageNameMap);
					printer.Outdent();
				}
				messageNameMap[(*field.message_type()).name()] = "TRUE";	
			}	
		}
	}
}	



void HtmlDocGen::PrintMessage(const Descriptor &messageDescriptor, io::Printer & printer) const
{
	//4.1 For each field in the Message:
	//    - Iterate over all fields we have in this message
	//    - In each iteration Find field's Name, its DataType and populate attribute map (create new attribute map in each iteration)
	//    - 

	//4.1
	//iterate over all fields we have and call PrintField to do the Job
	for (int i = 0; i < messageDescriptor.field_count(); ++i) 
	{
		std::map<std::string, std::string> fieldAttributeMap;
		const FieldDescriptor &field ( *messageDescriptor.field(i) );

		fieldAttributeMap["field_name"] = VariableName(field);
		//If field is of a complex type or enum type, we need unqualified_type name along with qualified_java_type name for the field 
		if(field.type() == FieldDescriptor::TYPE_MESSAGE)
		{
			//This field is a complex type, it has an un-qualified type name as well
			fieldAttributeMap["unqualified_type"] = (*field.message_type()).name();
		}
		else if(field.type() == FieldDescriptor::TYPE_ENUM)
		{
			//This field is a enum type, it has an un-qualified type name as well
			fieldAttributeMap["unqualified_type"] = (*field.enum_type()).name();
		}
		//Both simple and complex type have Qualified Type Name
		fieldAttributeMap["qualified_java_type"] = QualifiedJavaTypeNameForField(field);
		
		PrintField(printer, field, fieldAttributeMap);
	}
}




void HtmlDocGen::PrintMessages	(const FileDescriptor & fileDescriptor, io::Printer & printer) const
{
 			
	std::map<std::string, std::string> messageNameMap;
	for (int i = 0; i < fileDescriptor.message_type_count(); ++i) 
	{
		const Descriptor &messageDescriptor(*fileDescriptor.message_type(i));
		if(messageNameMap.find(messageDescriptor.name()) == messageNameMap.end())
		{
			printer.Print("<br>");
			printer.Print("<a id=`unqualified_name`><b><p class=normal style=\"font-size:11;\"><b>`unqualified_name`</b></p></a>\n","unqualified_name",messageDescriptor.name());
			printer.Print("<p class=normal style=\"padding-left: 200px;\" style=\"font-size:11;\">Message Specific Comment</p>\n");
			printer.Print("<table width=900 style=\"border:1px solid; border-top-color:#FF920D; border-bottom-color:#FF920D;border-right-width:0;border-left-width:0;\">\n");
			printer.Print("<tr><td width=300><p class=start style=\"font-size:11;\"><b>Field Name</b></p></td>\n<td width=308><p class=start style=\"font-size:11;\"><b>Field Type</b></p></td>\n<td width=308><p class=start style=\"font-size:11;\"><b>Field Description</b></p></td></tr>\n");
			printer.Indent();
			PrintMessage(messageDescriptor,printer);
			printer.Print("</table>\n");
			printer.Outdent();
			messageNameMap[messageDescriptor.name()] = "TRUE";
		}	
	}
	for (int i = 0; i < fileDescriptor.message_type_count(); ++i) 
	{
		const Descriptor &messageDescriptor(*fileDescriptor.message_type(i));
		ComplexTablePrint(messageDescriptor,printer,messageNameMap);
	}		
}



void HtmlDocGen::PrintMessageExchangeTable (const FileDescriptor & fileDescriptor, io::Printer & printer) const
{
 			
	for (int i = 0; i < fileDescriptor.message_type_count(); ++i) 
	{
		const Descriptor &messageDescriptor(*fileDescriptor.message_type(i));
		std::string strResponse= messageDescriptor.options().GetExtension(FluxMsgRsp);
		if(0!=strResponse.length())
 		{
			printer.Indent();
			printer.Print("<tr><td bgcolor=#FFFFFF width=300><a href=#`unqualified_name`><p class=normal style=\"font-size:11;\"><b>`unqualified_name`</b></a></td>\n","unqualified_name",messageDescriptor.name());
			printer.Print("<td width=300><p class=normal style=\"font-size:11;\">Synchronous Response</p></td>\n");
			printer.Print("<td width=300><a href =#`syn_responce`><p class=normal style=\"font-size:11;\"><b>`syn_responce`</b></p></td></tr>\n","syn_responce",strResponse);
			printer.Indent();
			printer.Outdent();
			printer.Outdent();
		
		}
	}
}

void HtmlDocGen::PrintFiles (const FileDescriptor* file, io::Printer & printer) const
{
	
			std::string strFileName=GetFileNameFromFileDescriptor(file);
			printer.Print("<!DOCTYPE html>\n<html>\n<body>\n");
			printer.Print("<style>\na:link {color:#blue;}\n a:hover {color:#8C6173;}\n a:visited{color:#75052E;}\n");
			printer.Print("table, tr, td, th {margin:0;border:0;padding:0;}\ntr:nth-child(odd) {background: rgb(249,221,189);\nbackground: -moz-linear-gradient(-45deg,  rgba(249,221,189,1) 0%, rgba(252,231,206,1) 35%, rgba(253,238,221,1) 97%);}\ntable { border-collapse: collapse; }\n");
			printer.Print("background: -webkit-gradient(linear, left top, right bottom, color-stop(0%,rgba(249,221,189,1)), color-stop(35%,rgba(252,231,206,1)), color-stop(97%,rgba(253,238,221,1)));\nbackground: -webkit-linear-gradient(-45deg,  rgba(249,221,189,1) 0%,rgba(252,231,206,1) 35%,rgba(253,238,221,1) 97%);");
			printer.Print("\nfilter: progid:DXImageTransform.Microsoft.gradient( startColorstr='#f9ddbd', endColorstr='#fdeedd',GradientType=1 );}\ntable { border-collapse: collapse; }\n");
			printer.Print("body{background-color:#FFFFFF;}\np.normal {font-family: Cambria Font;font-weight:normal;\ndisplay: inline;}\np.start {\nfont-family:Calibri Font;\nfont-weight:normal;\ndisplay: inline;");
			printer.Print("text-align: justify;\ndisplay: inline;\n}\nh1.start {\nfont-family: Calibri;\nfont-size: 21px;\nline-height: 28px;\nmargin: 0;\ndisplay: inline-block;\n}\n</style>");
			printer.Print("<h1 class=start style=\"font-size:18;\"><b>`GetFileName`</b></h1><p class=start \"font-size:16;\"><b>: File Specific Comment</b></p><br>\n","GetFileName",strFileName);
			printer.Print("<p class=normal style=\"font-size:14;\"><b>Message Exchange</b>\n");
			printer.Print("<table style=\"border:4px solid;border-left-width:0;border-right-width:1px;border-right-color:#FF920D;border-top-color:#FF920D; border-bottom-width:0;\" width=900>");
			PrintMessageExchangeTable(*file, printer);
			printer.Print("</table>\n");
			PrintMessages(*file, printer);
			printer.Print("</body>\n</html>\n");
			


}
bool HtmlDocGen::Generate(const FileDescriptor* file,
				const std::string& parameter,
				OutputDirectory* output_directory,
				std::string* error) const 
{
	
	//Step 0.
	std::string strOutputFileName = GetFileNameFromFileDescriptor(file) + ".html";
	//Step 1.
	scoped_ptr<io::ZeroCopyOutputStream> outputFileHandle(output_directory->Open(strOutputFileName));
	//Step 2.	
	io::Printer printer(outputFileHandle.get(), '`');
	//Step 3.
	PrintFiles(file, printer);
	return true;
}

int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	HtmlDocGen generator;
	return PluginMain(argc, argv, &generator);
}
