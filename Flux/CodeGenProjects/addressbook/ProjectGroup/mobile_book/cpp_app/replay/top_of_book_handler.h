#pragma once

#include "mobile_book_service.pb.h"
#include "mongo_db_handler.h"
#include "mongo_db_codec.h"
#include "mobile_book_web_socket_server.h"
#include "utility_functions.h"


namespace mobile_book_handler {

    class TopOfBookHandler {

    public:
        explicit TopOfBookHandler(std::shared_ptr<FluxCppCore::MongoDBHandler> &mongo_db,
                                  MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> &r_websocket_server_,
                                  quill::Logger* p_logger = quill::get_logger()) :
                                  m_sp_mongo_db_(mongo_db), mr_websocket_server_(r_websocket_server_),
                                  m_top_of_book_db_codec_(mongo_db, p_logger), mp_logger_(p_logger) {

            update_top_of_book_cache_();
        }

        void insert_or_update_top_of_book(const mobile_book::TopOfBook &kr_top_of_book_obj) {
            int32_t db_id;
            std::string top_of_book_key;
            bool stat = m_top_of_book_db_codec_.insert_or_update(kr_top_of_book_obj, db_id);
            assert(stat);
            MobileBookKeyHandler::get_key_out(kr_top_of_book_obj, top_of_book_key);
            db_id = m_top_of_book_db_codec_.m_root_model_key_to_db_id[top_of_book_key];
            mobile_book::TopOfBook ws_top_of_book_obj;
            m_top_of_book_db_codec_.get_data_by_id_from_collection(ws_top_of_book_obj, db_id);
            mr_websocket_server_.NewClientCallBack(ws_top_of_book_obj, -1);
        }


    protected:
        std::shared_ptr<FluxCppCore::MongoDBHandler> m_sp_mongo_db_;
        MobileBookTopOfBookWebSocketServer<mobile_book::TopOfBook> &mr_websocket_server_;
        FluxCppCore::MongoDBCodec<mobile_book::TopOfBook, mobile_book::TopOfBookList> m_top_of_book_db_codec_;
        quill::Logger *mp_logger_;

        void update_top_of_book_cache_() {
            mobile_book::TopOfBookList top_of_book_documents;
            std::vector<std::string> keys;
            m_top_of_book_db_codec_.get_all_data_from_collection(top_of_book_documents);
            MobileBookKeyHandler::get_key_list(top_of_book_documents, keys);
            for (int i = 0; i < top_of_book_documents.top_of_book_size(); ++i) {
                m_top_of_book_db_codec_.m_root_model_key_to_db_id[keys.at(i)] =
                        top_of_book_documents.top_of_book(i).id();
            }
        }
    };
}