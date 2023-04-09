import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec


@pytest.fixture()
def driver():
    driver = webdriver.Chrome(r'C:\drivers of browser\chromedriver_win32\chromedriver.exe')
    yield driver


@pytest.fixture()
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
                }
            }
        },
        "common_premium": 3
    }
    yield pair_strat


def load_web_project(driver):
    driver.get("http://localhost:3020/")
    driver.maximize_window()
    WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.NAME, "kill_switch")))
    portfolio_status_widget = driver.find_element(By.ID, "portfolio_status")
    portfolio_status_widget.find_element(By.NAME, "kill_switch")
    driver.execute_script('arguments[0].scrollIntoView(true)',  portfolio_status_widget)
    assert portfolio_status_widget.is_displayed()


def test_create_strat_strat(driver, pair_strat):
    load_web_project(driver)
    create_widget = driver.find_element(By.NAME, 'Create')
    driver.execute_script('arguments[0].scrollIntoView(true)', create_widget)
    # create button
    driver.find_element(By.NAME, 'Create').click()
    time.sleep(2)
    # sec id

    # for selecting sec id
    # MuiAutocomplete-listbox find element with this class global search on the body - use driver.find
    # inside this element, select the li tag with the matching text and click
    dropdwn = driver.find_element(By.XPATH, '//body//div//ul//ul//ul[1]//ul[1]//div[1]//div[1]//div[2]//div[1]//div[1]//input[1]')
    dd = Select(dropdwn)
    dd.select_by_value()

    # side
    driver.find_element(By.XPATH, "//div[normalize-space()='SIDE_UNSPECIFIED']").click()
    time.sleep(2)
    driver.find_element(By.XPATH, "//li[normalize-space()='BUY']").click()
    time.sleep(2)
    # sec id 2nd


    # common premium
    driver.find_element(By.NAME, "common_premium").send_keys('3')
    time.sleep(2)
    # save
    driver.find_element(By.NAME, "Save").click()
    time.sleep(2)
    # confirm
    driver.find_element(By.XPATH, "//button[normalize-space()='Confirm']").click()
    time.sleep(2)

    # verifying the value
    activate_widget = driver.find_element(By.XPATH, "//tbody//button[@value='Activate'][normalize-space()='Activate']")
    assert activate_widget.is_displayed()
    time.sleep(2)

    # use the pair_strat fixture to create pair strat and verify pair strat value after creation

