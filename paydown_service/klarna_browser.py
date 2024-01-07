import contextlib
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import re
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv
import imaplib
import email

load_dotenv(verbose=True, override=True)

import sys

sys.path.append('../')
from common.scraper import get_driver
from common.captcha_bypass import CaptchaBypass
from common.otp_bypass import TextBypass

class KlarnaBrowser(object):

    def __init__(self, phone_number, email_user, email_pass, driver=None):
        self.email_user_id = email_user
        self.email_pass_id = email_pass
        self.phone_number_field = phone_number
        self.driver = driver or get_driver()
        self.driver.implicitly_wait(10)

    def log_into_klarna(self):

        wait = WebDriverWait(self.driver, 10)

        self.driver.get('https://app.klarna.com/login')

        time.sleep(2)

        if self.driver.find_elements('xpath', '//*[@id="ModalLayout"]/div[3]/div/div[2]/button/div/div[1]'):
            self.driver.find_element('xpath', '//*[@id="ModalLayout"]/div[3]/div/div[2]/button/div/div[1]').click()

        self.driver.find_element('id', 'app-market-selector__option__22__label').click()
        # self.driver.find_element('xpath', '//*[contains(text(), "United Kingdom")]').click()
        # self.driver.find_element('xpath', '//*[@id="root"]/div/div/div[1]/div[1]/div[1]').click()  # close country of residence

        time.sleep(3)

        if self.driver.find_elements('xpath', '//*[@id="ModalLayout"]/div[3]/div/div[2]/button/div/div[1]'):
            element = wait.until(lambda driver: self.driver.find_element('xpath',
                                                                    '//*[@id="ModalLayout"]/div[3]/div/div[2]/button/div/div[1]'))  # cookies
            element.click()

        self.driver.find_element('xpath', '//*[@id="root"]/div/div/div[1]/div[2]/button[2]/div/div[1]').click()  # sign in

        ### New website

        self.driver.find_element('id', 'emailOrPhone').send_keys(self.phone_number_field)
        self.driver.find_element('id', 'onContinue').click()
        code = TextBypass().check_code('Klarna verification code', 'klarna')
        self.driver.find_element('id', 'otp_field').send_keys(code)

        time.sleep(5)

        # retries = 0
        # while 'Verify your email' in driver.page_source and retries < 5:
        if 'verify your email' in self.driver.page_source:

            # self.driver.find_element('xpath', '//*[@id="ModalLayout"]/div[2]/div/div[3]/div/div/button/div/div[1]').click()

            time.sleep(30)

            port = 993

            SMTP_SERVER = "imap.gmail.com"

            mail = imaplib.IMAP4_SSL(SMTP_SERVER)

            mail.login(self.email_user_id, self.email_pass_id)

            mail.select('klarna')

            status, mailbox = mail.search(None, 'ALL')

            item = mailbox[0].split()[-1]  # most recent

            status, body = mail.fetch(item, '(RFC822)')
            email_msg = body[0][1]

            email_message = email.message_from_bytes(email_msg)

            code = re.search('\d{6}', email_message['Subject']).group()
            # print(code)

            # self.driver.find_element('xpath', '//input[@aria-label="Verification code"]').send_keys(code)  # get from email
            self.driver.find_element('id', 'otp_field').send_keys(code)  # get from email

            # Delete email
            mail.store(item, "+FLAGS", "\\Deleted")
            mail.expunge()
            # close the mailbox
            mail.close()
            # logout from the account
            mail.logout()

            # time.sleep(10)

        # self.driver.find_element('xpath',
        #                                 '//*[@id="root"]/div/div/div/div[2]/div[2]/div/div[1]/div/div[1]/div[2]').click()
        # browser.driver.find_element('xpath', "//*[contains(text(),'Resend code')]").click()

        time.sleep(20)

        if self.driver.find_elements('xpath', '//*[contains(text(), "Next")]'):
            time.sleep(5)

            self.driver.find_element('xpath', '//*[contains(text(), "Next")]').click()
            self.driver.find_element('xpath', '//*[contains(text(), "Next")]').click()
            self.driver.find_element('xpath', '//*[contains(text(), "Done")]').click()

        return self.driver

    def secure_checkout_bypass(self):
        wait = WebDriverWait(self.driver, 10)
        with contextlib.suppress(Exception):
            element = wait.until(lambda driver: self.driver.find_element('id', 'interactiveCard-challenger-iframe'))
            self.driver.switch_to.frame(element)
        time.sleep(1)
        with contextlib.suppress(Exception):
            self.driver.switch_to.frame(self.driver.find_element('id', '3ds-iframe'))
        time.sleep(1)
        with contextlib.suppress(Exception):
            self.driver.switch_to.frame(self.driver.find_element('tag name', "iframe"))

    def get_purchasing_power(self):

        if 'klarna' in self.driver.current_url:
            self.driver.get('https://app.klarna.com/spending-limit/dynamic-dashboard')

        elif 'David' not in self.driver.page_source and self.driver.current_url != 'https://app.klarna.com/':
            wait = WebDriverWait(self.driver, 10)
            self.log_into_klarna()

        self.driver.get('https://app.klarna.com/spending-limit/dynamic-dashboard')
        time.sleep(5)
        purchasing_power = self.driver.find_element('xpath', '//span[starts-with(text(), "£")]').text

        return int(re.sub('\D', '', purchasing_power))

    def total_unpaid_orders(self):

        if 'klarna' in self.driver.current_url:
            self.driver.get('https://app.klarna.com/')

        elif 'David' not in self.driver.page_source and self.driver.current_url != 'https://app.klarna.com/':
            wait = WebDriverWait(self.driver, 10)
            self.log_into_klarna()

        self.driver.get('https://app.klarna.com/to-do/total-debt')
        time.sleep(5)
        total_unpaid_orders = self.driver.find_element('xpath', '//span[starts-with(text(), "£")]').text

        return float(int(re.sub('\D', '', total_unpaid_orders)) / 100)


    def paydown_klarna(self, card=None):

        self.driver.get('https://app.klarna.com/')
        time.sleep(2)

        wait = WebDriverWait(self.driver, 30)

        # Check if already signed in
        if 'David' not in self.driver.page_source and self.driver.current_url != 'https://app.klarna.com/':
            self.log_into_klarna()

        # wait.until(lambda driver: self.driver.find_element('xpath', "//*[contains(text(),'Payments')]")).click()

        # loop from here
        # driver.get('https://app.klarna.com/')

        # element = wait.until(lambda driver: self.driver.find_element('xpath', '//*[@id="toDo/TO_PAY"]/div[1]/div[1]'))

        # if 'Sit back and relax' in element.text:
        #     return 'No payments required'

        if self.driver.find_elements('xpath', "//button[@title='Dismiss']"):
            self.driver.find_element('xpath', "//button[@title='Dismiss']").click()

        # old card approach
        # while len(self.driver.find_elements('xpath', '//button[@data-pay-button="true"]')) > 0:
        #
        #     pay_button = self.driver.find_elements('xpath', '//button[@data-pay-button="true"]')[0]
        #
        #     wait.until(EC.element_to_be_clickable(pay_button)).click()
        #     # pay_button.click()

        self.driver.get('https://app.klarna.com/to-do/card-balance')
        self.driver.find_element('xpath', "//*[contains(text(),'Open')]").click()
        while len(self.driver.find_elements('xpath', "//*[contains(text(),'Payment options')]")) > 0:
            pay_button = self.driver.find_elements('xpath', "//*[contains(text(),'Payment options')]")[0]
            wait.until(EC.element_to_be_clickable(pay_button)).click()

            try:
                # element = wait.until(lambda driver: self.driver.find_element('xpath',
                #                                                     '//*[@id="klapp-dialog__container"]/div/span/div/div/div[2]/div[1]/div/div[1]/div'))  # Pay now or schedule payment
                element = wait.until(lambda driver: self.driver.find_element('class name', 'SettlementSelectorPayInteractiveCard-enabled'))
            except TimeoutException:
                self.driver.get('https://app.klarna.com/')
                pay_button = self.driver.find_elements('xpath', '//button[@data-pay-button="true"]')[0]
                wait.until(EC.element_to_be_clickable(pay_button)).click()
                # element = wait.until(lambda driver: self.driver.find_element('xpath',
                #                                         '//*[@id="klapp-dialog__container"]/div/span/div/div/div[2]/div[1]/div/div[1]/div'))  # Pay now or schedule payment
                element = wait.until(lambda driver: self.driver.find_element('class name', 'SettlementSelectorPayInteractiveCard-enabled'))

            element.click()
            time.sleep(2)

            #### Move to Uphold
            if card == 'Uphold':

                if '•••• <HIDDEN>' not in self.driver.page_source:
                    self.driver.find_element('xpath', "//*[contains(text(),'Change')]").click()
                    time.sleep(2)
                    self.driver.find_element('xpath', "//*[contains(text(),'•••• <HIDDEN>')]").click()

                time.sleep(1)
                self.driver.find_element('xpath',
                                    '//*[@id="klapp-dialog__footer-button-wrapper"]/div/div/button/div').click()  # Pay now
                time.sleep(5)

                if self.driver.find_elements('id', 'interactiveCard-challenger-iframe'):
                    code = TextBypass().check_code("Mastercard: Code: ", 'uphold')
                    self.driver.switch_to.frame(self.driver.find_element('id', 'interactiveCard-challenger-iframe'))
                    self.driver.switch_to.frame(self.driver.find_element('id', '3ds-iframe'))
                    self.driver.find_element('id', 'inputID').send_keys(code)
                    self.driver.find_element('id', 'sqInputID').send_keys('0896')
                    self.driver.find_element('id', 'sendOtpsq').click()
                    self.driver.switch_to.default_content()

            elif card == 'Plutus':
                if '•••• <HIDDEN>' not in self.driver.page_source:
                    self.driver.find_element('xpath', "//*[contains(text(),'Change')]").click()
                    time.sleep(2)
                    self.driver.find_element('xpath', "//*[contains(text(),'•••• <HIDDEN>')]").click()

                self.driver.find_element('xpath',
                                    '//*[@id="klapp-dialog__footer-button-wrapper"]/div/div/button/div').click()  # Pay now

                time.sleep(10)
                if not self.driver.find_elements('xpath', "//*[contains(text(),'Done')]"):

                    self.driver.switch_to.frame(self.driver.find_element('id', 'interactiveCard-challenger-iframe'))
                    self.driver.switch_to.frame(self.driver.find_element('id', '3ds-iframe'))
                    # browser.driver.switch_to.frame(browser.driver.find_element('xpath', "//*[starts-with(@id, 'cardinal-stepUpIframe-')]"))
                    code = TextBypass().check_code("is the One Time Password for purchase of", 'plutus')
                    self.driver.find_element('id', 'Credential_Value').send_keys(code)
                    self.driver.find_element('id', 'ValidateButton').click()

                    time.sleep(5)

                    if self.driver.find_element('id', 'CredentialValidateInput'):
                        self.driver.find_element('id', 'CredentialValidateInput').send_keys('spikey')
                        self.driver.find_element('id', 'ValidateButton').click()

                # wait.until(lambda driver: self.driver.find_element('xpath', "//*[contains(text(),'Done')]"))

                self.driver.switch_to.default_content()


            # Curve is default payment method
            else:

                if '•••• <HIDDEN>' not in self.driver.page_source:
                    self.driver.find_element('xpath', "//*[contains(text(),'Change')]").click()
                    time.sleep(2)
                    self.driver.find_element('xpath', "//*[contains(text(),'•••• <HIDDEN>')]").click()

                time.sleep(1)
                self.driver.find_element('xpath',
                                    '//*[@id="klapp-dialog__footer-button-wrapper"]/div/div/button/div').click()  # Pay now

                time.sleep(3)
                if self.driver.find_elements('id', 'payment-options-pi-full-purchase'):
                    self.driver.find_element('id', 'payment-options-pi-full-purchase').click()  # Pay full amount
                    self.driver.find_element('xpath',
                                        '//*[@id="klapp-dialog__footer-button-wrapper"]/div/div/button/div').click()  # Pay now

                # if scheduled
                if pay_button.get_attribute("aria-label") == 'Pay early':
                    element = wait.until(lambda driver: self.driver.find_element('xpath',
                                                                            '//*[@id="klapp-dialog__footer-button-wrapper"]/div/div/button/div/div[1]'))  # Pay now for schedule payment
                    element.click()
                    time.sleep(2)

                with contextlib.suppress(Exception):
                    element = wait.until(lambda driver: self.driver.find_element('id', 'interactiveCard-challenger-iframe'))
                    self.driver.switch_to.frame(element)
                time.sleep(1)
                with contextlib.suppress(Exception):
                    element = wait.until(lambda driver: self.driver.find_element('id', '3ds-iframe'))
                    self.driver.switch_to.frame(element)
                wait.until(
                    lambda driver: self.driver.find_element('xpath', "//*[contains(text(),'mobile: ********<HIDDEN>')]")).click()
                self.driver.find_element('id', 'submit-label').click()

                code = TextBypass().check_code('transaction at Klarna', 'curve')

                self.driver.find_element('id', 'dataEntry').send_keys(code)
                self.driver.find_element('id', 'submit-label').click()

            time.sleep(5)

            # TODO: ADD fix for if uphold fails
            if "Payment failed" in self.driver.find_element('xpath', '//*[@id="klapp-dialog__container"]').text:
                # retry from 'choose payment option'
                self.driver.find_element('xpath',
                                    "//*[@id=\"root\"]/div/div/div/div[2]/div/div[5]/div/button/div/div[1]").click()  # Choose payment option
                # self.driver.find_element('xpath', '//*[@id="root"]*[contains(text(),\'Choose payment option\')]').click()

                self.driver.find_element('xpath',
                                    '//*[@id="klapp-dialog__container"]/div/span/div/div/div[2]/div[1]/div/div[1]/div').click()

                wait.until(lambda driver: self.driver.find_element('xpath',
                                                              '//*[@id="klapp-dialog__footer-button-wrapper"]/div/div/button/div')).click()  # Pay today

                time.sleep(2)
                self.driver.switch_to.frame(self.driver.find_element('id', 'interactiveCard-challenger-iframe'))
                self.driver.switch_to.frame(self.driver.find_element('id', '3ds-iframe'))
                self.driver.switch_to.frame(self.driver.find_element('tag name', "iframe"))
                self.driver.find_element('xpath', "//*[contains(text(),'mobile: ********<HIDDEN>')]").click()
                self.driver.find_element('id', 'submit-label').click()

                # driver.find_element('xpath', '//*[@id="toDo/TO_PAY"]/div[1]/div[1]').click()

                code = TextBypass().check_code('transaction at Klarna', 'curve')

                self.driver.find_element('id', 'dataEntry').send_keys(code)
                self.driver.find_element('id', 'submit-label').click()

            element = wait.until(lambda driver: self.driver.find_element('xpath',
                                                                    '//*[@id="klapp-dialog__footer-button-wrapper"]/div/div/button/div/div[1]'))
            element.click()

            self.driver.switch_to.default_content()
            self.driver.refresh()
            # self.driver.implicitly_wait(10)

    def close(self):
        self.driver.close()
        self.driver.quit()

    def get_driver(self):
        return self.driver

if __name__ == '__main__':

    PHONE_NUM = os.getenv('PHONE_NUM')
    email_user = os.getenv('ALT_EMAIL')
    email_pass = os.getenv('ALT_PASS')

    PHONE_NUM=""
    email_user=""
    email_pass=""

    plutus_site = KlarnaBrowser(PHONE_NUM, email_user, email_pass)
    plutus_site.log_into_klarna()
    wait = WebDriverWait(plutus_site.driver, 10)
    plutus_site.paydown_klarna(card='Uphold')

    # new paydown
    plutus_site.driver.get('https://app.klarna.com/to-do/card-balance')
    plutus_site.driver.find_element('xpath', "//*[contains(text(),'Open')]").click()
    for button in plutus_site.driver.find_elements('xpath', "//*[contains(text(),'Payment options')]"):
        button.click()

        try:
            # element = wait.until(lambda driver: self.driver.find_element('xpath',
            #                                                     '//*[@id="klapp-dialog__container"]/div/span/div/div/div[2]/div[1]/div/div[1]/div'))  # Pay now or schedule payment
            element = wait.until(
                lambda driver: plutus_site.driver.find_element('class name', 'SettlementSelectorPayInteractiveCard-enabled'))
        except TimeoutException:
            plutus_site.driver.get('https://app.klarna.com/')
            pay_button = plutus_site.driver.find_elements('xpath', '//button[@data-pay-button="true"]')[0]
            wait.until(EC.element_to_be_clickable(pay_button)).click()
            # element = wait.until(lambda driver: self.driver.find_element('xpath',
            #                                         '//*[@id="klapp-dialog__container"]/div/span/div/div/div[2]/div[1]/div/div[1]/div'))  # Pay now or schedule payment
            element = wait.until(
                lambda driver: plutus_site.driver.find_element('class name', 'SettlementSelectorPayInteractiveCard-enabled'))

        element.click()
        plutus_site.driver.find_element('xpath',
                                 '//*[@id="klapp-dialog__footer-button-wrapper"]/div/div/button/div').click()  # Pay now/today


    # plutus_site.driver.get('https://app.klarna.com/')
    # plutus_site.driver.find_element('id', 'emailOrPhone').send_keys(PHONE_NUM)
    # plutus_site.driver.find_element('id', 'onContinue').click()
    # code = TextBypass().check_code('Klarna verification code', 'klarna')
    # plutus_site.driver.find_element('id', 'otp_field').send_keys(code)

    # plutus_site.get_purchasing_power()
    # plutus_site.total_unpaid_orders()

    plutus_site.driver.switch_to.frame(plutus_site.driver.find_element('id', 'interactiveCard-challenger-iframe'))
    plutus_site.driver.switch_to.frame(plutus_site.driver.find_element('id', '3ds-iframe'))
    plutus_site.driver.switch_to.frame(plutus_site.driver.find_element('tag name', "iframe"))
    plutus_site.driver.switch_to.frame(plutus_site.driver.find_element('id', 'cardinal-stepUpIframe-1685457091164'))
    plutus_site.driver.find_element('xpath', "//*[contains(text(),'mobile: ********<HIDDEN>')]").click()
    plutus_site.driver.find_element('xpath', '//*[@id="mainForm"]/div/div[4]/div/label[2]/span').click()
    plutus_site.driver.switch_to.default_content()

    plutus_site.driver.find_element('class name', 'SettlementSelectorPayInteractiveCard-enabled').click()


    plutus_site.paydown_klarna()
    plutus_site.close()
