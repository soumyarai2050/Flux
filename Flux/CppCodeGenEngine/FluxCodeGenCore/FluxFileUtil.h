/**
 * CodeGenerator File Utility Functions
 * By Dev-0
 *
 */
#ifndef FluxFileUtil_h
#define FluxFileUtil_h 1

#include <fstream>

inline bool FileExists(const char* ptrFileName)
{
	bool retStatus = false;
	std::ifstream infile;
	
	infile.open (ptrFileName, ifstream::in);
	
	if (infile.good()) 
	{
		retStatus = true;
	}
	infile.close();
	return retStatus;
}


#endif //FluxFileUtil_h
