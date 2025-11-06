from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
import time
import pandas as pd
import datetime
import numpy as np
import logging

# Setup
today = datetime.date.today().isoformat()
logging.basicConfig(filename=f'./logs/log_{today}.txt', level=logging.DEBUG)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
wait = WebDriverWait(driver, 10)

# DAAD Base URL (Masters, English-taught, etc.)
PARENT_URL = "https://www2.daad.de/deutschland/studienangebote/international-programmes/en/result/?q=&degree%5B%5D=2&lang%5B%5D=2&sort=4&limit=10&display=list"

# Target university keywords (cleaned, DAAD-friendly)
TARGET_UNIS = [
    "TUB", "LMU", "Freie Universität Berlin", "Hamburg", "Dresden", "RWTH",
    "Freiburg", "Heidelberg", "KIT", "Humboldt", "TUM", "Tübingen",
    "Bonn", "FAU", "Göttingen", "Darmstadt", "Cologne", "Stuttgart"
]

PARAMS = ["course", "institution", "url", "admission req", "language req", "deadline"]
COLS = PARAMS.copy()
FINAL_DATA = []


def accept_cookies():
    try:
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.qa-cookie-consent-accept-all")))
        btn.click()
        print("Cookies accepted")
    except Exception:
        print("No cookie popup found.")


def fetch_all_links():
    """Scrape all program links across pagination."""
    all_urls = []
    driver.get(PARENT_URL)
    accept_cookies()

    while True:
        time.sleep(2)
        course_links = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "a.js-course-detail-link.list-inline-item.mr-0")))
        all_urls.extend([a.get_attribute("href") for a in course_links])

        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "a.js-result-pagination-next")
            if "disabled" in next_btn.get_attribute("class"):
                break
            next_btn.click()
        except Exception:
            break

    print(f"Total programs fetched: {len(all_urls)}")
    return list(set(all_urls))  # remove duplicates


def filter_links_by_universities(all_links):
    """Visit each link once, filter based on TARGET_UNIS."""
    filtered_links = []
    print("Filtering by university names...")
    for link in all_links:
        driver.get(link)
        try:
            institution = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "h3.c-detail-header__subtitle"))).text
            if any(keyword.lower() in institution.lower() for keyword in TARGET_UNIS):
                filtered_links.append((link, institution))
                print(f"Matched: {institution}")
        except Exception:
            continue
    print(f"Filtered {len(filtered_links)} matching universities.")
    return filtered_links


def text_combiner(targetIndex):
    try:
        elements = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, f"#registration > .container > .c-description-list > *:nth-child({targetIndex}) > *")))
        return "\n".join([el.text for el in elements])
    except Exception:
        return ""


def extract_data(filtered_links):
    for link, uni in filtered_links:
        print(f"Scraping data from: {link}")
        driver.get(link)
        row = []
        try:
            course = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "h2.c-detail-header__title > span:nth-child(1)"))).text
            admission_req = text_combiner("2")
            language_req = text_combiner("4")
            deadline = text_combiner("6")

            row = [course, uni, link, admission_req, language_req, deadline]
            FINAL_DATA.append(row)
        except Exception as e:
            print(f"Error at {link}: {e}")
            logging.critical(e, exc_info=True)
            continue


def export_csv():
    filename = f"Target_Unis_Masters_{today}"
    df = pd.DataFrame(np.array(FINAL_DATA), columns=COLS)
    df.to_csv(f"./{filename}.csv", encoding='utf-8-sig', index=False)
    print(f"Exported {len(df)} rows to {filename}.csv")


def main():
    print("# Starting focused scrape...")
    all_links = fetch_all_links()
    filtered_links = filter_links_by_universities(all_links)
    extract_data(filtered_links)
    export_csv()
    driver.quit()


if __name__ == "__main__":
    main()
