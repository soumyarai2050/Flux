/**
 * Protocol Buffer Class Name Generator Plugin for protoc
 * By Dev-0
 *
 */

#include <FluxUtil.h>
#include <FluxCodeGenerator.h>
#include <flux_options.pb.h>

class ModelClassNameTextGen: public FluxCodeGenerator 
{
	public:
		ModelClassNameTextGen(){}
};

int main(int argc, char* argv[]) 
{
	if(getenv("DEBUG_ENABLE"))
		sleep(30);
	ModelClassNameTextGen generator;
	return PluginMain(argc, argv, &generator);
}
