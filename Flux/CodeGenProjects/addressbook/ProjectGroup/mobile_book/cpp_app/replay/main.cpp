
#include "cpp_app_shared_resource.h"
#include "mobile_book_web_n_ws_server.h"

int main(int argc, char *argv[]) {
	signal(SIGINT, signal_handler);
	signal(SIGKILL, signal_handler);
	signal(SIGTERM, signal_handler);

	if (argc != 2) {
		std::cerr << "Usage: " << argv[0] << " config_file" << std::endl;
		return 1; // Return an error code
	}
	std::string config_file = argv[1];
	Config config(config_file); // Use std::string directly
	MobileBookPublisher mobile_book_publisher(config);
	mobile_book_consumer = std::make_unique<MobileBookConsumer>(config, mobile_book_publisher);

	mobile_book_consumer->init_shm();
	mobile_book_consumer->go();

	while (keepRunning.load()) {
		std::this_thread::sleep_for(std::chrono::milliseconds(100));
	}
	// combined_server.cleanup();
	mobile_book_consumer->cleanup();
	return 0; // Return success code
}