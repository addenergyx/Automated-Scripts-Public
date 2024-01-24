from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def get_driver(headless=True):

    options = Options()
    options.binary_location = '/opt/headless-chromium'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')
    options.add_argument('--disable-dev-shm-usage')

    return webdriver.Chrome('/opt/chromedriver', chrome_options=options)

def get_dev_driver(headless=False, options=None):

    # Importing in here because do not want to have to create a ChromeDriverManager lambda layer in PROD
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service()
    options = webdriver.ChromeOptions()

    if headless:
        options.add_argument("--headless")

    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')
    options.add_argument('--disable-dev-shm-usage')

    return webdriver.Chrome(service=service, options=options)
