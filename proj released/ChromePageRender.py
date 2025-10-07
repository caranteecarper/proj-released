from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

import undetected_chromedriver
from typing import Literal
from time import sleep

from urllib.parse import urlparse as url_parse


def is_valid_url(url):
    parsed = url_parse(url)
    return (parsed.scheme in ["http", "https"]) and (parsed.netloc != "")


class SafeChrome(webdriver.Chrome):
    def __del__(self):
        """Suppress __del__ cleanup to avoid invalid handle errors."""
        pass


class SafeChromeUndetected(undetected_chromedriver.Chrome):
    def __del__(self):
        """Suppress __del__ cleanup to avoid invalid handle errors."""
        pass


class ChromePageRender:
    def __init__(self, chrome_driver_filepath: str, options: Options, use_undetected_chromedriver: bool = False):
        self.__browser = SafeChrome(
            service=Service(chrome_driver_filepath),
            options=options
        ) if not use_undetected_chromedriver else SafeChromeUndetected(
            service=Service(chrome_driver_filepath),
            options=options
        )

    def goto_url(
            self,
            url: str
    ) -> None:
        if not isinstance(url, str):
            raise TypeError('Given url is not a string.')
        if not is_valid_url(url):
            raise ValueError('Given url is invalid, or it does not start with http or https.')
        self.__browser.get(url)
        return None

    def get_page_source(self) -> str:
        return self.__browser.page_source

    def wait_for_selectors(
            self,
            wait_type: Literal['appear', 'disappear'],
            selector_types_rules: list[tuple[Literal['css', 'xpath'], str]],
            waiting_timeout_in_seconds: float = 0.2,
            print_error_log_to_console: bool = False
    ) -> bool:  # is_timed_out: bool
        if waiting_timeout_in_seconds <= 0:
            raise TypeError('Waiting timeout in seconds <= 0.')
        try:
            patched_timeout_in_seconds = waiting_timeout_in_seconds / len(selector_types_rules)
            for (selector_type, selector_rule) in selector_types_rules:
                by = None
                if selector_type == 'css':
                    by = By.CSS_SELECTOR
                elif selector_type == 'xpath':
                    by = By.XPATH
                else:
                    raise TypeError(f"Selector type {selector_type} is not supported.")
                if wait_type == 'appear':
                    WebDriverWait(self.__browser, patched_timeout_in_seconds).until(
                        expected_conditions.presence_of_element_located((by, selector_rule))
                    )
                elif wait_type == 'disappear':
                    WebDriverWait(self.__browser, patched_timeout_in_seconds).until_not(
                        expected_conditions.presence_of_element_located((by, selector_rule))
                    )
                else:
                    raise TypeError(f"Wait type {wait_type} is not supported.")
            return False
        except TimeoutException:
            if print_error_log_to_console:
                print(f"ChromePageRender: wait_for_selectors: Timed out, "
                      f"failed to fulfill the \"{wait_type}\" selectors.")
            return True

    def goto_url_waiting_for_selectors(
            self,
            url: str,
            selector_types_rules: list[tuple[Literal['css', 'xpath'], str]],
            waiting_timeout_in_seconds: float = 0.2,
            print_error_log_to_console: bool = False
    ) -> bool:  # is_timed_out: bool
        self.goto_url(url=url)
        return self.wait_for_selectors(
            wait_type='appear',
            selector_types_rules=selector_types_rules,
            waiting_timeout_in_seconds=waiting_timeout_in_seconds,
            print_error_log_to_console=print_error_log_to_console
        )

    def click_on_html_element(
            self,
            click_element_selector_type: Literal['css', 'xpath'],
            click_element_selector_rule: str,
            use_javascript: bool,
            max_trials_for_unstable_page: int = 1,
            click_waiting_timeout_in_seconds: float = 0.2,
            print_error_log_to_console: bool = False
    ) -> bool:  # is_timed_out: bool
        if max_trials_for_unstable_page <= 0:
            raise TypeError('Waiting timeout in seconds <= 0.')
        if click_waiting_timeout_in_seconds <= 0:
            raise TypeError('Waiting timeout in seconds <= 0.')
        try:
            by = None
            if click_element_selector_type == 'css':
                by = By.CSS_SELECTOR
            elif click_element_selector_type == 'xpath':
                by = By.XPATH
            else:
                raise TypeError(f"Selector type {click_element_selector_type} is not supported.")
            html_element = WebDriverWait(self.__browser, click_waiting_timeout_in_seconds).until(
                expected_conditions.element_to_be_clickable((by, click_element_selector_rule))
            )
            # scroll element into view before click
            self.__browser.execute_script("arguments[0].scrollIntoView(true);", html_element)
            for attempt in range(max_trials_for_unstable_page):
                try:
                    if use_javascript:
                        self.__browser.execute_script('arguments[0].click();', html_element)
                    else:
                        html_element.click()
                    break
                except Exception as e:
                    if attempt == max_trials_for_unstable_page - 1:
                        raise e
                    sleep(0.5)
            return False
        except TimeoutException:
            if print_error_log_to_console:
                print(f"ChromePageRender: click_on_html_element: Timed out, failed to click on element.")
            return True

    # def take_screenshot(self, save_path: str):
    #     self.__browser.save_screenshot(save_path)

    def close(self) -> None:
        if self.__browser:
            self.__browser.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
