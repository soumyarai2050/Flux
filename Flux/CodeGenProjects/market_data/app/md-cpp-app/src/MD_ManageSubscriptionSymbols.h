# pragma once
#include <string>
#include "iostream"

#include "Poco/Net/HTTPClientSession.h"
#include "Poco/Net/HTTPRequest.h"
#include "Poco/Net/HTTPResponse.h"
#include "Poco/StreamCopier.h"

class MD_ManageSubscriptionSymbols {
public:
    static std::string get(const std::string& host, int port, const std::string& path) {
        try {
            Poco::Net::HTTPClientSession session(host, port);

            Poco::Net::HTTPRequest request(Poco::Net::HTTPRequest::HTTP_GET, path);

            session.sendRequest(request);
            Poco::Net::HTTPResponse response;
            std::istream& responseStream = session.receiveResponse(response);

            std::string responseBody;
            Poco::StreamCopier::copyToString(responseStream, responseBody);
            return responseBody;

        } catch (std::exception& e) {
            std::cerr << "Error: " << e.what() << std::endl;
            return "";
        }
    }
};

