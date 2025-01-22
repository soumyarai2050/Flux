#pragma once

#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <regex>

struct Route {
    std::string path;
    std::regex path_pattern;
    std::vector<boost::beast::http::verb> methods;
    std::function<void(boost::beast::http::request<boost::beast::http::string_body>&, boost::beast::http::response<boost::beast::http::string_body>&, const std::smatch& match)> handler;
};