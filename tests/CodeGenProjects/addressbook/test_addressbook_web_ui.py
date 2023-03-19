import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By


@pytest.fixture()
def driver():
    driver = webdriver.Chrome(r'C:\drivers of browser\chromedriver_win32\chromedriver.exe')
    yield driver


@pytest.fixture
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
        "common_premium_percentage": 3
    }
    yield pair_strat


def load_web_project(driver):
    driver.get("http://localhost:3020/")
    driver.maximize_window()
    time.sleep(5)


def test_first():
    load_web_project()
    assert driver.find_element(By.XPATH, '//*[@id="strat_collection"]/h6/div')
    assert driver.find_element(By.XPATH, '//*[@id="strat_collection"]/div/div/span/div/span')


def test_create_strat_strat(pair_strat):
    # use the pair_strat fixture to create pair strat and verify pair strat value after creation
    pass

