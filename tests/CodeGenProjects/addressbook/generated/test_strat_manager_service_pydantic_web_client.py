
# project imports
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_beanie_model import OrderLimitsBaseModel
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient


def test_create_get_put_patch_delete_order_limits_client(launch_mongo_and_beanie_fastapi,
                                                         web_clients: StratManagerServiceWebClient, order_limit,
                                                         order_limit_received, order_limits_updated,
                                                         partial_updated_order_limits,
                                                         partial_updated_order_limits_complete,
                                                         delete_response, updated_order_limit):

    order_limits_obj = OrderLimitsBaseModel(**order_limit)
    # testing create_order_limits_client()
    assert web_clients.create_order_limits_client(order_limits_obj).dict() == order_limit_received, \
        f"create_order_limits_client() failed: details: order_limit: {order_limit}, order_limits_obj: " \
        f"{order_limits_obj}, order_limit_received: {order_limit_received}"

    # Creating obj of order_limit_received
    order_limits_obj = OrderLimitsBaseModel(**order_limit_received)

    # getting get_all_order_limits_client() as received_resp
    received_resp = web_clients.get_all_order_limits_client()
    # checking order_limit_obj available on received_resp or not.
    if order_limit_received in received_resp:
        assert True, f"get_all_order_limits_client() failed while testing create_order_limits_client(): details: " \
                     f"order_limit_received: {order_limit_received}, order_limits_obj: {order_limits_obj}" \
                     f" not in received_resp: {received_resp} "
    else:
        assert False, f"get_all_order_limits_client() failed create_order_limits_client(): details:" \
                      f" order_limit_received: {order_limit_received} order_limits_obj: {order_limits_obj}" \
                      f" not in received_resp: {received_resp} "

    # getting get_order_limits_client() as received_resp
    received_resp = web_clients.get_order_limits_client(10)
    # testing received_resp is in order_limit_obj or not
    assert received_resp == order_limit_received, f"get_order_limits_client() failed: details: order_limit_received:" \
                                                  f" {order_limit_received} order_limits_obj: {order_limits_obj} " \
                                                  f"is not equal to received_resp: {received_resp}"

    # Creating order_limits_obj of updated_order_limit to test put_order_limits_client()
    order_limits_obj = OrderLimitsBaseModel(**updated_order_limit)
    # testing put_order_limits_client()
    received_resp = web_clients.put_order_limits_client(order_limits_obj)
    assert received_resp.dict() == order_limits_obj.dict(), f"put_order_limits_client() failed: details: while " \
                                                            f"requesting put: updated_order_limit:" \
                                                            f" {updated_order_limit}, order_limits_obj: " \
                                                            f"{order_limits_obj}, received_resp: {received_resp}"

    # creating order_limits_obj for order_limit_received to test put_order_limits_client()
    order_limits_obj = OrderLimitsBaseModel(**updated_order_limit)

    # getting get_all_order_limits_client() as received_resp
    received_resp = web_clients.get_all_order_limits_client()
    # checking order_limit_obj available on received_resp or not.
    if order_limits_obj in received_resp:
        assert True, f"get_all_order_limits_client() failed while requesting put_order_limits_client(): " \
                     f"details: order_limit_received: {order_limit_received}, order_limits_obj: {order_limits_obj}" \
                     f" not in received_resp: {received_resp} "
    else:
        assert False, f"get_all_order_limits_client() failed while requesting put_order_limits_client(): details: " \
                      f"order_limit_received: {order_limit_received}, order_limits_obj: {order_limits_obj} " \
                      f"not in received_resp: {received_resp} "

    # creating order_limits_obj for partial_updated_order_limits to patch_order_limits_client()
    order_limits_obj = OrderLimitsBaseModel(**partial_updated_order_limits)
    received_resp = web_clients.patch_order_limits_client(order_limits_obj)
    # testing patch_order_limits_client()
    assert received_resp.dict() == partial_updated_order_limits_complete, f"patch_order_limits_client(): failed: " \
                                                                          f"details: partial_updated_order_limits: " \
                                                                          f"{partial_updated_order_limits}, " \
                                                                          f"order_limits_obj: {order_limits_obj}, " \
                                                                          f"received_resp: {received_resp}, " \
                                                                          f"partial_updated_order_limits_complete: " \
                                                                          f"{partial_updated_order_limits_complete}"
    # creating order_limit_obj of partial_updated_order_limits_complete to test patch_order_limits_client()
    order_limits_obj = OrderLimitsBaseModel(**partial_updated_order_limits_complete)

    # getting get_all_order_limits_client() as received_resp
    received_resp = web_clients.get_all_order_limits_client()
    # checking order_limit_obj available on received_resp or not.
    if order_limits_obj in received_resp:
        assert True, f"get_all_order_limits_client() failed while requesting patch_order_limits_client: details:" \
                     f" order_limit_received: {order_limit_received}, order_limits_obj: {order_limits_obj}" \
                     f" not in received_resp:  {received_resp} "
    else:
        assert False, f"get_all_order_limits_client() failed while requesting patch_order_limits_client(): details:" \
                      f" order_limit_received: {order_limit_received}, order_limits_obj: {order_limits_obj}" \
                      f" not in received_resp: {received_resp} "

    received_resp = web_clients.delete_order_limits_client(10)
    assert received_resp == delete_response, f"delete_order_limits_client() failed: details: received_resp: " \
                                             f"{received_resp}, delete_response: {delete_response}"

    # creating order_limit_obj of order_limit_received to test delete_order_limits_client()
    order_limits_obj = OrderLimitsBaseModel(**order_limit_received)

    # getting get_all_order_limits_client() as received_resp to test delete_order_limits_client()
    received_resp = web_clients.get_all_order_limits_client()
    # checking order_limit_obj available on received_resp or not.
    if order_limits_obj in received_resp:
        assert False, f"get_all_order_limits_client() failed while requesting delete_order_limits_client(): details:" \
                      f" order_limit_received: {order_limit_received}, order_limits_obj: {order_limits_obj}" \
                      f" not in received_resp: {received_resp} "
    else:
        assert True, f"get_all_order_limits_client() failed while requesting delete_order_limits_client: details: " \
                     f"order_limit_received: {order_limit_received}, order_limits_obj: {order_limits_obj} \
                     not in received_resp: {received_resp}"
