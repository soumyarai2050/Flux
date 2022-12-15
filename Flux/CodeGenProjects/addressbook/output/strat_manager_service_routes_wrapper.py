import threading
from typing import Optional, TypeVar

StratManagerServiceRoutesWrapperDerivedType = TypeVar('StratManagerServiceRoutesWrapperDerivedType', bound='StratManagerServiceRoutesWrapper')


class StratManagerServiceRoutesWrapper:
    get_instance_mutex: threading.Lock = threading.Lock()
    strat_manager_service_routes_wrapper_instance: Optional['StratManagerServiceRoutesWrapper'] = None

    def __init__(self):
        pass

    @classmethod
    def get_instance(cls) -> 'StratManagerServiceRoutesWrapper':
        with cls.get_instance_mutex:
            if cls.strat_manager_service_routes_wrapper_instance is None:
                raise Exception("Error: get_instance invoked before any server creating instance via set_instance")
            else:
                return cls.strat_manager_service_routes_wrapper_instance

    @classmethod
    def set_instance(cls, instance: StratManagerServiceRoutesWrapperDerivedType) -> None:
        if not issubclass(instance, StratManagerServiceRoutesWrapper):
            raise Exception("StratManagerServiceRoutesWrapper.set_instance must be invoked with a type that is subclass"
                            " of StratManagerServiceRoutesWrapper - is-subclass test failed!")
        if instance == cls.strat_manager_service_routes_wrapper_instance:
            return  # multiple calls with same instance is not an error (though - should be avoided where possible)
        with cls.get_instance_mutex:
            if cls.strat_manager_service_routes_wrapper_instance is not None:
                raise Exception("Multiple StratManagerServiceRoutesWrapper.set_instance invocation detected with "
                                "different instance objects. multiple calls allowed with the exact same object only")
            cls.strat_manager_service_routes_wrapper_instance = StratManagerServiceRoutesWrapper()
            return cls.strat_manager_service_routes_wrapper_instance

    def read_all_order_limits_pre(self):
        pass

    def read_all_order_limits_post(self, obj):
        pass

    def read_all_ws_order_limits_pre(self):
        pass

    def read_all_ws_order_limits_post(self):
        pass

    def create_order_limits_pre(self):
        pass

    def create_order_limits_post(self, obj):
        pass

    def read_by_id_order_limits_pre(self):
        pass

    def read_by_id_order_limits_post(self, obj):
        pass

    def update_order_limits_pre(self):
        pass

    def update_order_limits_post(self, obj):
        pass

    def partial_update_order_limits_pre(self):
        pass

    def partial_update_order_limits_post(self, obj):
        pass

    def delete_order_limits_pre(self):
        pass

    def delete_order_limits_post(self, obj):
        pass

    def read_by_id_ws_order_limits_pre(self):
        pass

    def read_by_id_ws_order_limits_post(self):
        pass

    def read_all_portfolio_limits_pre(self):
        pass

    def read_all_portfolio_limits_post(self, obj):
        pass

    def read_all_ws_portfolio_limits_pre(self):
        pass

    def read_all_ws_portfolio_limits_post(self):
        pass

    def create_portfolio_limits_pre(self):
        pass

    def create_portfolio_limits_post(self, obj):
        pass

    def read_by_id_portfolio_limits_pre(self):
        pass

    def read_by_id_portfolio_limits_post(self, obj):
        pass

    def update_portfolio_limits_pre(self):
        pass

    def update_portfolio_limits_post(self, obj):
        pass

    def delete_portfolio_limits_pre(self):
        pass

    def delete_portfolio_limits_post(self, obj):
        pass

    def read_by_id_ws_portfolio_limits_pre(self):
        pass

    def read_by_id_ws_portfolio_limits_post(self):
        pass

    def read_all_portfolio_status_pre(self):
        pass

    def read_all_portfolio_status_post(self, obj):
        pass

    def read_all_ws_portfolio_status_pre(self):
        pass

    def read_all_ws_portfolio_status_post(self):
        pass

    def create_portfolio_status_pre(self):
        pass

    def create_portfolio_status_post(self, obj):
        pass

    def read_by_id_portfolio_status_pre(self):
        pass

    def read_by_id_portfolio_status_post(self, obj):
        pass

    def update_portfolio_status_pre(self):
        pass

    def update_portfolio_status_post(self, obj):
        pass

    def delete_portfolio_status_pre(self):
        pass

    def delete_portfolio_status_post(self, obj):
        pass

    def read_by_id_ws_portfolio_status_pre(self):
        pass

    def read_by_id_ws_portfolio_status_post(self):
        pass

    def read_all_pair_strat_pre(self):
        pass

    def read_all_pair_strat_post(self, obj):
        pass

    def read_all_ws_pair_strat_pre(self):
        pass

    def read_all_ws_pair_strat_post(self):
        pass

    def create_pair_strat_pre(self):
        pass

    def create_pair_strat_post(self, obj):
        pass

    def read_by_id_pair_strat_pre(self):
        pass

    def read_by_id_pair_strat_post(self, obj):
        pass

    def update_pair_strat_pre(self):
        pass

    def update_pair_strat_post(self, obj):
        pass

    def delete_pair_strat_pre(self):
        pass

    def delete_pair_strat_post(self, obj):
        pass

    def read_by_id_ws_pair_strat_pre(self):
        pass

    def read_by_id_ws_pair_strat_post(self):
        pass

    def read_all_strat_collection_pre(self):
        pass

    def read_all_strat_collection_post(self, obj):
        pass

    def read_all_ws_strat_collection_pre(self):
        pass

    def read_all_ws_strat_collection_post(self):
        pass

    def create_strat_collection_pre(self):
        pass

    def create_strat_collection_post(self, obj):
        pass

    def read_by_id_strat_collection_pre(self):
        pass

    def read_by_id_strat_collection_post(self, obj):
        pass

    def update_strat_collection_pre(self):
        pass

    def update_strat_collection_post(self, obj):
        pass

    def delete_strat_collection_pre(self):
        pass

    def delete_strat_collection_post(self, obj):
        pass

    def read_by_id_ws_strat_collection_pre(self):
        pass

    def read_by_id_ws_strat_collection_post(self):
        pass

    def read_all_ui_layout_pre(self):
        pass

    def read_all_ui_layout_post(self, obj):
        pass

    def read_all_ws_ui_layout_pre(self):
        pass

    def read_all_ws_ui_layout_post(self):
        pass

    def create_ui_layout_pre(self):
        pass

    def create_ui_layout_post(self, obj):
        pass

    def read_by_id_ui_layout_pre(self):
        pass

    def read_by_id_ui_layout_post(self, obj):
        pass

    def update_ui_layout_pre(self):
        pass

    def update_ui_layout_post(self, obj):
        pass

    def partial_update_ui_layout_pre(self):
        pass

    def partial_update_ui_layout_post(self, obj):
        pass

    def delete_ui_layout_pre(self):
        pass

    def delete_ui_layout_post(self, obj):
        pass

    def read_by_id_ws_ui_layout_pre(self):
        pass

    def read_by_id_ws_ui_layout_post(self):
        pass

    def index_of_profile_id_ui_layout_pre(self):
        pass

    def index_of_profile_id_ui_layout_post(self, obj):
        pass

