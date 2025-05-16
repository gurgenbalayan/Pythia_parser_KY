import re
from typing import List, Optional, Dict

from selenium.webdriver import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from utils.logger import setup_logger
import os
from bs4 import BeautifulSoup
from selenium import webdriver


SELENIUM_REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL")
STATE = os.getenv("STATE")
logger = setup_logger("scraper")
async def fetch_company_details(url: str) -> dict:
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument(f'--lang=en-US')
        options.add_argument("--start-maximized")
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
        options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
        options.add_argument("--disable-features=DnsOverHttps")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-first-run")
        options.add_argument("--no-sandbox")
        options.add_argument("--test-type")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.set_capability("goog:loggingPrefs", {
            "performance": "ALL",
            "browser": "ALL"
        })
        driver = webdriver.Remote(
            command_executor=SELENIUM_REMOTE_URL,
            options=options
        )
        driver.set_page_load_timeout(30)
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        elements = driver.find_elements(By.ID, "MainContent_BtnImages")
        button_images = elements[0] if elements else None
        elements = driver.find_elements(By.ID, "MainContent_BtnCurrent")
        button_current = elements[0] if elements else None
        elements = driver.find_elements(By.ID, "MainContent_BtnInitial")
        button_initial = elements[0] if elements else None
        if button_images:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_images)
            wait.until(EC.visibility_of_element_located((By.ID, "MainContent_BtnImages")))
            wait.until(EC.element_to_be_clickable((By.ID, "MainContent_BtnImages")))
            driver.execute_script("arguments[0].click();", button_images)
            # button_images.click()
            wait.until(EC.visibility_of_element_located((By.ID, "MainContent_pImages")))
        if button_current:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_current)
            wait.until(EC.visibility_of_element_located((By.ID, "MainContent_BtnCurrent")))
            wait.until(EC.element_to_be_clickable((By.ID, "MainContent_BtnCurrent")))
            driver.execute_script("arguments[0].click();", button_current)
            # button_current.click()
            wait.until(EC.visibility_of_element_located((By.ID, "MainContent_pcurrent")))
        if button_initial:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_initial)
            wait.until(EC.visibility_of_element_located((By.ID, "MainContent_BtnInitial")))
            wait.until(EC.element_to_be_clickable((By.ID, "MainContent_BtnInitial")))
            driver.execute_script("arguments[0].click();", button_initial)
            # button_initial.click()
            wait.until(EC.visibility_of_element_located((By.ID, "MainContent_pInitial")))
        wait.until(EC.visibility_of_element_located(
            (By.ID, "MainContent_pInfo")))
        html = driver.page_source
        return await parse_html_details(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{url}': {e}")
        return {}
    finally:
        if driver:
            driver.quit()

async def fetch_company_data(query: str) -> list[dict]:
    driver = None
    url = "https://sosbes.sos.ky.gov/BusSearchNProfile/search.aspx"
    try:

        options = webdriver.ChromeOptions()
        options.add_argument(f'--lang=en-US')
        options.add_argument("--start-maximized")
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
        options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
        options.add_argument("--disable-features=DnsOverHttps")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-first-run")
        options.add_argument("--no-sandbox")
        options.add_argument("--test-type")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.set_capability("goog:loggingPrefs", {
            "performance": "ALL",
            "browser": "ALL"
        })
        driver = webdriver.Remote(
            command_executor=SELENIUM_REMOTE_URL,
            options=options
        )
        driver.set_page_load_timeout(30)
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        first_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent_txtSearch"))
        )
        first_input.send_keys(query)
        first_input.send_keys(Keys.RETURN)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        current_url = driver.current_url
        if "Profile.aspx" in current_url:
            wait.until(EC.visibility_of_element_located((By.ID, "MainContent_pInfo")))
            html = driver.page_source
            return await parse_html_details_small(html, current_url)
        else:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,
                                                    "#MainContent_PSearchResults")))
            html = driver.page_source
            return await parse_html_search(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{query}': {e}")
        return []
    finally:
        if driver:
            driver.quit()

async def parse_html_search(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    no_results_div = soup.find("div", id="MainContent_pNOSearchresults")
    if no_results_div and "No matching organizations" in no_results_div.get_text():
        return results

    table = soup.find("table", id="MainContent_gvSearchResults")
    if not table:
        return results

    rows = table.find_all("tr")[1:]

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        name_cell = cells[0]
        name_link = name_cell.find("a")
        name = name_link.get_text(strip=True) if name_link else name_cell.get_text(strip=True)
        link = name_link["href"] if name_link and name_link.has_attr("href") else None

        company_id = cells[1].get_text(strip=True)
        status = cells[2].get_text(strip=True)

        results.append({
            "state": STATE,
            "name": name,
            "status": status,
            "id": company_id,
            "url": "https://sosbes.sos.ky.gov/BusSearchNProfile/" + link
        })

    return results

async def parse_html_details_small(html: str, current_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    result["state"] = STATE
    result["name"] = soup.find("span", id="MainContent_lblName").text.strip()
    result["link"] = current_url
    for row in soup.select(".company-info-container .grid-row"):
        label_elem = row.select_one(".grid-label")
        value_elem = row.select_one(".grid-value")
        if label_elem and value_elem:
            label = label_elem.get_text(strip=True)
            value = value_elem.get_text(" ", strip=True).replace("\xa0", " ")
            if label == "Organization Number":
                result["id"] = value
            if label == "Status":
                result["status"] = value
    return result
async def parse_html_details(html: str) -> dict:
    def exists_multiple(lst, **kwargs):
        return any(all(d.get(k) == v for k, v in kwargs.items()) for d in lst)
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    result["state"] = STATE
    result["name"] = soup.find("span", id="MainContent_lblName").text.strip()
    for row in soup.select(".company-info-container .grid-row"):
        label_elem = row.select_one(".grid-label")
        value_elem = row.select_one(".grid-value")
        if label_elem and value_elem:
            label = label_elem.get_text(strip=True)
            value = value_elem.get_text(" ", strip=True).replace("\xa0", " ")
            if label == "Organization Number":
                result["registration_number"] = value
            if label == "Company Type":
                result["entity_type"] = value
            if label == "Status":
                result["status"] = value
            if label == "Company Name":
                result["entity_type"] = value
            if label == "Organization Date":
                result["date_registered"] = value
            if label == "Principal Office":
                result["prinicipal_address"] = value
            if label == "Registered Agent":
                parts = list(value_elem.stripped_strings)
                result["agent_name"] = parts[0]
                result["agent_address"] = ' '.join(parts[1:])

    officers = []
    for row in soup.select("#MainContent_pcurrent .panel-row")[1:]:
        cells = row.select(".panel-cell")
        if len(cells) == 2:
            title = cells[0].get_text(strip=True)
            officer = cells[1].get_text(strip=True)
            if officer and officer != "" and not exists_multiple(officers, title=title, officer=officer):
                officers.append({"title": title, "name": officer})
    for row in soup.select("#MainContent_pInitial .panel-row")[1:]:
        cells = row.select(".panel-cell")
        if len(cells) == 2:
            title = cells[0].get_text(strip=True)
            officer = cells[1].get_text(strip=True)
            if officer and officer != "" and not exists_multiple(officers, title=title, officer=officer):
                officers.append({"title": title, "officer": officer})
    result["officers"] = officers

    documents = []
    for row in soup.select("#MainContent_pImages .panel-row")[1:]:
        cells = row.select(".panel-cell")
        if len(cells) >= 2:
            title_tag = cells[0].find("a")
            title = title_tag.get_text(strip=True) if title_tag else None
            url = title_tag["href"] if title_tag and "href" in title_tag.attrs else None
            date = cells[1].get_text(strip=True)
            documents.append({"name": title, "url": url, "date": date})
    result["documents"] = documents

    return result