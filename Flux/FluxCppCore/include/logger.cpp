#include <iostream>
#include <yaml-cpp/yaml.h>

#include "logger.h"

quill::Logger* logger{nullptr};

void expand_file_template(const std::string& kr_log_file, std::string& r_log_file_out)
{
    std::string result{kr_log_file};

    bool need_data_at_end = true;

    auto pos = result.find("%P");
    if (pos != std::string::npos)
        result.replace(pos, 2, std::to_string(getpid()));

    pos = result.find("%D");
    if (pos != std::string::npos)
    {
        auto t = time(nullptr);
        auto tm = *std::localtime(&t);

        std::stringstream ss;
        ss << std::put_time(&tm, "%Y-%m-%d");

        result.replace(pos, 2, ss.str() );
        need_data_at_end = false;
    }

    pos = result.find("%T");
    if (pos != std::string::npos)
    {
        auto t = time(nullptr);
        auto tm = *std::localtime(&t);

        std::stringstream ss;
        ss << std::put_time(&tm, "%T-%m-%d");
        result.replace(pos, 2, ss.str());
        need_data_at_end = false;
    }

    if (need_data_at_end)
    {
        std::filesystem::path path(result);
        auto extn = path.extension();
        result = path.replace_extension().string() + std::format("_{:%Y%m%d}{}", std::chrono::system_clock::now(), extn.string());
    }
    r_log_file_out = result;
}

void create_file_handler(const std::string& kr_log_file_path, std::pair<std::shared_ptr<quill::Handler>, std::string>& r_file_hanler_out)
{
    quill::FileHandlerConfig cfg;
    cfg.set_open_mode('a');
    cfg.set_append_to_filename(quill::FilenameAppend::None);
    auto fir = quill::file_handler(kr_log_file_path, cfg);
    r_file_hanler_out = std::make_pair(fir, std::string{});
}

void get_log_file_handlers(const std::string& kr_log_file_template, std::vector<std::shared_ptr<quill::Handler>>& r_file_handlers_out, bool lineHeader = true )
{
    // std::vector<std::shared_ptr<quill::Handler>> FileHandlers;
    std::string logFile;
    expand_file_template(kr_log_file_template, logFile);
    std::pair<std::shared_ptr<quill::Handler>, std::string> fileFileHandler;
    create_file_handler(logFile, fileFileHandler);
    r_file_handlers_out.emplace_back(std::move(fileFileHandler.first));
    auto setPattern = [&r_file_handlers_out] (const std::string& kr_log_pattern, const std::string& kr_time_format = {})
    {
        for (auto& h : r_file_handlers_out)
        {
            if (kr_time_format.empty()) {h->set_pattern(kr_log_pattern);}
            else
            {
                h->set_pattern(kr_log_pattern, kr_time_format);
            }
        }
    };

    if (lineHeader)
    {
        auto logPtn = "%(time) %(log_level) %(thread_id) %(thread_name) %(file_name) %(line_number) - %(message)";
        setPattern(logPtn, "%Y-%m-%d %H-%M-%S.%Qus%z");
    }
}

quill::Logger* create_logger(const char* name, quill::LogLevel log_level, std::vector<std::shared_ptr<quill::Handler>>&& fh)
{
    quill::Logger* ql = quill::create_logger(name, std::move(fh));
    ql->set_log_level(log_level);
    return ql;
}

void get_log_file_path(std::string &r_log_file_path_out) {

    const char* config_file = getenv("CONFIG_FILE");
    if (!config_file) {
        throw std::runtime_error("export env variable {CONFIG_FILE}");
    }
    if (access(config_file, F_OK) != 0) {
        throw std::runtime_error(std::format("{} not accessable", config_file));
    }

    YAML::Node config = YAML::LoadFile(config_file);
    try {
        r_log_file_path_out = config["log_file_path"].as<std::string>();
    } catch (YAML::Exception& exception) {
        std::cerr << "-------------------------" << config["log_file_path"].size() << "\n";
        std::cerr << exception.msg << std::endl;
        throw std::runtime_error((exception.what()));
    }
}

#ifndef USE_LOGGING

void InitLogger(){}
quill::Logger* GetLogger() {return nullptr;}

#else

void InitLogger()
{

    std::string log_file_path;
    get_log_file_path(log_file_path);

    std::vector<std::shared_ptr<quill::Handler>> handlers;
    get_log_file_handlers(log_file_path + "/" + "market_data.logfile-%P--%D-%T.log", handlers);
    logger = create_logger("", quill::LogLevel::Debug, std::move(handlers));

    quill::Config cfg;
    cfg.backend_thread_sleep_duration = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::milliseconds{1});
    cfg.backend_thread_notification_handler = [](const std::string& message)
    {
        if (message.find("Quill INFO:") == std::string::npos)
        {
            std::cerr << message << '\n';
        }
    };
    cfg.default_queue_capacity = 2 * 1024 * 1024;
    quill::configure(cfg);

    quill::start();
}

quill::Logger* GetLogger()
{
    if (logger) return logger;
    InitLogger();
    return logger;

}

#endif
