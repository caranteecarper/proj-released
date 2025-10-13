import os
import time
from urllib.parse import urljoin as url_join

from bs4 import BeautifulSoup

# Selenium / undetected-chromedriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import TimeoutException

# HTML generation (keep structure consistent with main project)
from dominate import document as HTMLDocument
from dominate import tags as HTMLTags


URL = os.environ.get('JPM_URL', 'https://www.jpmorgan.com/insights#all-insights')
URL_NAME = '摩根大通研究院（All Insights）'
MAX_ITEMS = int(os.environ.get('JPM_MAX_ITEMS', '30'))

# Output strictly inside this folder
OUT_DIR = os.path.join(os.path.dirname(__file__), 'generated_html')
OUT_INDEX = os.path.join(OUT_DIR, 'index.html')


def _extract_cards(html: str, base_url: str):
    soup = BeautifulSoup(html or '', 'html.parser')
    root = soup.select_one('#all-insights') or soup
    grid = root.select_one('.cmp-dynamic-grid-content') or root
    cards = grid.select('ul.grid > li.article-card, ul.grid > li.jpma-article-card, ul.grid > li.podcast-card')
    if not cards:
        cards = grid.select('ul.grid > li, ul li')

    seen = set()
    results = []
    for node in cards:
        # link
        a = node.select_one('p.dynamic-grid__cta-link a[href]') or node.select_one('a[href*="/insights/"]') or node.select_one('a[href]')
        if not a or not a.get('href'):
            continue
        href = url_join(base_url, a['href'])
        if href in seen:
            continue
        # title + date container
        td = node.select_one('.dynamic-grid__title-date')
        title_node = (td.select_one('.dynamic-grid__title') if td else None) or node.select_one('.dynamic-grid__title') or node.select_one('h3, h2') or a
        date_node = (td.select_one('.dynamic-grid__date') if td else None) or node.select_one('time[datetime]') or node.select_one('time')
        title = title_node.get_text(strip=True) if title_node is not None else ''
        date_text = ''
        if date_node is not None:
            date_text = (date_node.get_text(strip=True) or date_node.get('datetime', '')).strip()
        if not title:
            continue
        seen.add(href)
        results.append((href, title, date_text))
    return results


def _new_browser_uc():
    options = uc.ChromeOptions()
    # Options tuned for dynamic sites
    try:
        options.page_load_strategy = 'none'
    except Exception:
        pass
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-site-isolation-trials')
    options.add_argument('--test-type')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    # Keep headful by default for better compatibility
    return uc.Chrome(options=options)


def _new_browser_std():
    opts = ChromeOptions()
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--ignore-certificate-errors')
    opts.add_argument('--ignore-ssl-errors')
    opts.add_argument('--allow-running-insecure-content')
    opts.add_argument('--disable-web-security')
    opts.add_argument('--disable-site-isolation-trials')
    opts.add_argument('--test-type')
    opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    try:
        opts.page_load_strategy = 'none'
    except Exception:
        pass
    return webdriver.Chrome(options=opts)


def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    # Prefer UC, but fallback to standard driver if session errors
    try:
        driver = _new_browser_uc()
    except Exception:
        driver = _new_browser_std()
    try:
        driver.command_executor.set_timeout(45)
        try:
            driver.set_page_load_timeout(45)
        except Exception:
            pass
    except Exception:
        pass
    try:
        try:
            driver.get(URL)
        except TimeoutException:
            # Stop further loading and continue
            try:
                driver.execute_script('return 1;')
            except Exception:
                pass
        except Exception:
            # Fallback: recreate with std driver and retry once
            try:
                driver.quit()
            except Exception:
                pass
            driver = _new_browser_std()
            try:
                driver.set_page_load_timeout(45)
            except Exception:
                pass
            try:
                driver.get(URL)
            except TimeoutException:
                try:
                    driver.execute_script('return 1;')
                except Exception:
                    pass
        # Wait for the section to exist
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#all-insights')))

        # Scroll the insights section into view to trigger lazy loading
        try:
            sec = driver.find_element(By.CSS_SELECTOR, '#all-insights')
            driver.execute_script('arguments[0].scrollIntoView(true);', sec)
            # Nudge a bit further to trigger observers
            driver.execute_script('window.scrollBy(0, 200);')
        except Exception:
            pass

        # Wait for first cards to appear
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#all-insights .cmp-dynamic-grid-content ul.grid li')))
        except Exception:
            pass

        html = driver.page_source
        results = _extract_cards(html, URL)

        # Click load more until reach MAX_ITEMS
        def click_load_more_once() -> bool:
            sels = [
                '#all-insights .load-more-container .load-more-card.active button[aria-label="load more content"]',
                '#all-insights .load-more-container .load-more-card.active button',
                '#all-insights .load-more-container button',
            ]
            for sel in sels:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, sel)
                    driver.execute_script('arguments[0].scrollIntoView(true);', btn)
                    time.sleep(0.3)
                    driver.execute_script('arguments[0].click();', btn)
                    return True
                except Exception:
                    continue
            return False

        while len(results) < MAX_ITEMS:
            before = len(results)
            if not click_load_more_once():
                break
            # Wait for more cards to mount
            for _ in range(20):
                time.sleep(0.5)
                html = driver.page_source
                results = _extract_cards(html, URL)
                if len(results) > before:
                    break
            if len(results) <= before:
                break

        # Render HTML (minimal, but structure-compatible)
        doc = HTMLDocument(title='JPMorgan Insights (Debug)')
        with doc.head:
            HTMLTags.meta(charset='utf-8', name='viewport', content='width=device-width, initial-scale=1')
        with doc.body:
            with HTMLTags.div(cls='page-board'):
                # Use project logo if present (path from repo root). For debug we use a relative path that likely exists.
                HTMLTags.img(cls='site-logo', src='../Logos/handler12_JPMorgan.svg', alt='JPM Logo')
                with HTMLTags.a(href=URL):
                    HTMLTags.h2(URL_NAME)
                for (href, title, date_text) in results[:MAX_ITEMS]:
                    with HTMLTags.div(cls='page-board-item'):
                        with HTMLTags.a(href=href):
                            HTMLTags.h3(title)
                            HTMLTags.span(date_text or '')

        with open(OUT_INDEX, 'w', encoding='utf-8') as f:
            f.write(doc.render(pretty=True))
        print(f'Success: wrote {OUT_INDEX} with {min(len(results), MAX_ITEMS)} items')
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    run()
