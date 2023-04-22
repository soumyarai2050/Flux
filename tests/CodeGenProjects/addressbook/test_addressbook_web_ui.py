import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

short_delay: int = 2
delay: int = 5
long_delay: int = 20


@pytest.fixture(scope="session")
def driver():
    driver = webdriver.Chrome(r'"C:\Users\pc\Downloads\chromedriver_win32\chromedriver.exe"')
    yield driver


@pytest.fixture(scope="session")
def pair_strat():
    pair_strat = {
        "pair_strat_params": {
            "strat_leg1": {
                "sec": {
                    "sec_id": "CB_Sec_1"
                },
                "side": "BUY"
            },
            "strat_leg2": {
                "sec": {
                    "sec_id": "EQT_Sec_1"
                },
                "side": "SELL"
            },
            "common_premium": 3
        }
    }
    yield pair_strat


@pytest.fixture(scope="session")
def wait(driver):
    wait = WebDriverWait(driver, long_delay)
    yield wait


def load_web_project(driver, wait):
    driver.get("http://localhost:3020/")
    driver.maximize_window()
    # TODO: change the browser zoom to 75% (default zoom)
    # driver.execute_script("document.body.style.zoom='75%'")
    time.sleep(short_delay)
    driver.refresh()

    wait.until(EC.presence_of_element_located((By.ID, "portfolio_status")))
    portfolio_status_widget = driver.find_element(By.ID, "portfolio_status")
    driver.execute_script('arguments[0].scrollIntoView(true)', portfolio_status_widget)
    wait.until(EC.presence_of_element_located((By.NAME, "kill_switch")))
    kill_switch_btn = portfolio_status_widget.find_element(By.NAME, "kill_switch")
    assert kill_switch_btn.is_displayed()
    time.sleep(short_delay)


def test_create_strat_strat(driver, pair_strat, wait):
    load_web_project(driver, wait)
    # create button
    strat_collection_widget = driver.find_element(By.ID, 'strat_collection')
    driver.execute_script('arguments[0].scrollIntoView(true)', strat_collection_widget)
    create_strat_btn = strat_collection_widget.find_element(By.NAME, 'Create')
    create_strat_btn.click()
    time.sleep(short_delay)

    # sec id
    pair_strat_params_widget = driver.find_element(By.ID, "pair_strat_params")

    # selecting strat leg1 sec id
    strat_leg1_sec_id = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params."
                                                                        "strat_leg1.sec.sec_id']")

    selected_value_strat_leg1_sec_id = pair_strat["pair_strat_params"]["strat_leg1"]["sec"]["sec_id"]
    input_field_leg1_sec_id = strat_leg1_sec_id.find_element(By.TAG_NAME, "input")
    input_field_leg1_sec_id.send_keys(selected_value_strat_leg1_sec_id)
    time.sleep(short_delay)
    input_field_leg1_sec_id.send_keys(Keys.ARROW_DOWN)
    input_field_leg1_sec_id.send_keys(Keys.ENTER)

    # selecting side value
    # strat_leg1_side = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params.strat"
    #                                                                   "_leg1.side']")
    # strat_leg1_side_drpdwn = strat_leg1_side.find_element(By.XPATH, "//div[normalize-space()='SIDE_UNSPECIFIED']")
    # strat_leg1_side_drpdwn.click()
    # selected_option_strat_leg1_side_drpdwn = strat_leg1_side_drpdwn.find_element(By.XPATH, "//li[normalize-space"
    #                                                                                        "()='BUY']")
    # selected_option_strat_leg1_side_drpdwn.click()
    # time.sleep(short_delay)

    # strat_leg1_side = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params.strat"
    #                                                                  "_leg1.side']")
    # strat_leg1_side_drpdwn = strat_leg1_side.find_element(By.XPATH, "//div[normalize-space()='SIDE_UNSPECIFIED']")
    # select = Select(strat_leg1_side_drpdwn)
    # select.select_by_value("BUY")


    # strat_leg1_side = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params.strat"
    #                                                                   "_leg1.side']")
    # strat_leg1_side_drpdwn = strat_leg1_side.find_element(By.XPATH, "//div[normalize-space()='SIDE_UNSPECIFIED']")
    # strat_leg1_side_drpdwn_2 = strat_leg1_side_drpdwn.find_element(By.XPATH, "//ul[@role='listbox']")
    # time.sleep(short_delay)
    # strat_leg1_side_drpdwn_2.send_keys(Keys.ARROW_DOWN)
    # time.sleep(short_delay)
    # strat_leg1_side_drpdwn_2.send_keys(Keys.ENTER)

    strat_leg1_side = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params.strat"
                                                                      "_leg1.side']")
    strat_leg1_side_drpdwn = strat_leg1_side.find_element(By.XPATH, "//div[normalize-space()='SIDE_UNSPECIFIED']")
    strat_leg1_side_drpdwn.click()
    strat_leg1_side_list = driver.find_element(By.XPATH, "//ul[@role='listbox']")
    strat_leg1_side.send_keys(Keys.ARROW_DOWN)
    strat_leg1_side_list.send_keys(Keys.ENTER)


    # selecting strat leg2 sec id
    strat_leg2_sec_id = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params."
                                                                        "strat_leg2.""sec.sec_id']")
    selected_value_strat_leg2_sec_id = pair_strat["pair_strat_params"]["strat_leg2"]["sec"]["sec_id"]
    input_field_leg2_sec_id = strat_leg2_sec_id.find_element(By.TAG_NAME, "input")
    input_field_leg2_sec_id.send_keys(selected_value_strat_leg2_sec_id)
    time.sleep(short_delay)
    input_field_leg2_sec_id.send_keys(Keys.ARROW_DOWN)
    input_field_leg2_sec_id.send_keys(Keys.ENTER)

    # passing common premium value
    selected_value_common_prem = pair_strat["pair_strat_params"]["common_premium"]
    common_prem = pair_strat_params_widget.find_element(By.NAME, "common_premium")
    common_prem.send_keys(selected_value_common_prem)
    time.sleep(short_delay)

    # save btn
    save_btn = strat_collection_widget.find_element(By.NAME, "Save")
    save_btn.click()
    time.sleep(short_delay)
    # confirm btn
    confirm_btn_widget = driver.find_element(By.XPATH, "//div[@role='dialog']")
    confirm_btn = confirm_btn_widget.find_element(By.XPATH, "//button[normalize-space()='Confirm']")
    confirm_btn.click()

    # storing the values in variables of created pair strat
    # stratleg1_sec
    value_stratleg1_sec = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params."
                                                                          "strat_leg1.sec.sec_id']")
    value_of_created_stratleg1_sec = value_stratleg1_sec.find_element(By.TAG_NAME, "input").get_attribute('value')

    # strat_leg1_side
    value_strat_leg1_side = pair_strat_params_widget.find_element(By.XPATH,
                                                                  "//div[@data-xpath='pair_strat_params.strat_leg1.side']")
    value_of_created_strat_side = value_strat_leg1_side.find_element(By.TAG_NAME, "input").get_attribute('value')

    # stratleg2_sec
    value_stratleg2_sec = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_params."
                                                                          "strat_leg2.""sec.sec_id']")
    value_of_created_stratleg2_sec_id = value_stratleg2_sec.find_element(By.TAG_NAME, "input").get_attribute(
        'value')

    # leg2_side
    value_of_strat_leg2_side = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_"
                                                                               "params.strat_leg2.side']")
    value_of_created_strat_leg2_side = value_of_strat_leg2_side.find_element(By.TAG_NAME, 'input').get_attribute(
        'value')

    # common premium
    value_of_strat_common_prem = pair_strat_params_widget.find_element(By.XPATH, "//div[@data-xpath='pair_strat_"
                                                                                 "params.common_premium']")
    value_of_created_strat_common_prem = value_of_strat_common_prem.find_element(By.NAME, 'common_premium') \
        .get_attribute('value')
    value_of_created_strat_common_prem = str(value_of_created_strat_common_prem)

    # verifying the values of pair_strat
    assert value_of_created_stratleg1_sec == pair_strat["pair_strat_params"]["strat_leg1"]["sec"]["sec_id"]
    assert value_of_created_strat_side == pair_strat["pair_strat_params"]["strat_leg1"]["side"]
    assert value_of_created_stratleg2_sec_id == pair_strat["pair_strat_params"]["strat_leg2"]["sec"]["sec_id"]
    assert value_of_created_strat_leg2_side == pair_strat['pair_strat_params']['strat_leg2']['side']
    assert value_of_created_strat_common_prem == str(pair_strat["pair_strat_params"]["common_premium"])
    driver.quit()



