import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import csv
import os 
import urllib.request
import requests
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Setup Chrome browser
options = Options()
options.headless = False  # So you can see the browser window
driver = webdriver.Chrome(options=options)


# Step 1: Open the homepage
driver.get("https://egazette.gov.in/")

# Step 2: Dismiss the first popup (OK button)
try:
    ok_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "ImgMessage_OK"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", ok_button)
    time.sleep(1)
    driver.execute_script("arguments[0].click();", ok_button)
    print("✅ First popup dismissed.")
except Exception as e:
    print("❌ Could not dismiss the first popup:", e)

# Step 3: Dismiss the second popup (Cross image)
try:
    cross_img = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'images/Cross.png')]"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", cross_img)
    time.sleep(1)
    driver.execute_script("arguments[0].click();", cross_img)
    print("✅ Second popup (cross) dismissed.")
except Exception as e:
    print("❌ Could not dismiss the second popup:", e)


# Step 4: Click on "Search" button (id='sgzt')
try:
    search_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "sgzt"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", search_btn)
    time.sleep(1)
    driver.execute_script("arguments[0].click();", search_btn)
    print("✅ Navigated to Search page.")
except Exception as e:
    print("❌ Failed to click Search button:", e)


# Step 5: Click “Search by Bill / Assent / Act” button
try:
    bill_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "btnBill"))
    )
    driver.execute_script("arguments[0].click();", bill_btn)
    print("✅ Navigated to Bill / Assent / Act search form.")
except Exception as e:
    print("❌ Failed to click Bill/Assent/Act button:", e)



# ADD THIS BLOCK at the top of Step 6
ref_types = ["Act", "Bill", "Assent"]
all_extracted_rows = []
download_folder = "downloads"
pagination_limit = 2  # 👉 Set to None to scrape all pages, or set to a specific number like 3
os.makedirs(download_folder, exist_ok=True)

for ref_type in ref_types:
    print(f"\n🔄 Processing type: {ref_type}")

    # Step 6: Select from dropdown
    try:
        dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ddlreftype"))
        )
        select = Select(dropdown)
        select.select_by_visible_text(ref_type)
        print(f"✅ Selected '{ref_type}' from dropdown.")
        time.sleep(1)  # Wait for postback
    except Exception as e:
        print(f"❌ Failed to select '{ref_type}':", e)
        continue

    # Step 7: Click Submit
    try:
        submit_btn = driver.find_element(By.ID, "ImgSubmitDetails")
        driver.execute_script("arguments[0].click();", submit_btn)
        print("✅ Submit button clicked.")
    except Exception as e:
        print("❌ Failed to click Submit:", e)
        continue

    # Step 8–9: Scrape pages
    visited_pages = set()
    current_page_count = 1
    while True:
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "tbl_Gazette")))

            outer_table = driver.find_element(By.ID, "tbl_Gazette")
            outer_rows = outer_table.find_elements(By.TAG_NAME, "tr")
            nested_tr = outer_rows[1]
            nested_td = nested_tr.find_element(By.TAG_NAME, "td")
            nested_div = nested_td.find_element(By.TAG_NAME, "div")
            data_table = nested_div.find_element(By.TAG_NAME, "table")

            data_rows = data_table.find_elements(By.TAG_NAME, "tr")[1:16]

            for index, row in enumerate(data_rows):
                cols = row.find_elements(By.TAG_NAME, "td")
                row_data = [col.text.strip() for col in cols[:-1]]

                try:
                    date_text = cols[-3].text.strip()
                    year = date_text.split("-")[-1]
                    doc_id_text = cols[-2].text.strip()
                    document_id = doc_id_text.split("-")[-1]
                    pdf_url = f"https://egazette.gov.in/WriteReadData/{year}/{document_id}.pdf"

                    response = requests.get(pdf_url, stream=True)
                    if response.status_code == 200:
                        pdf_filename = f"{ref_type}_{document_id}.pdf"
                        pdf_path = os.path.join(download_folder, pdf_filename)
                        with open(pdf_path, "wb") as f:
                            f.write(response.content)
                        print(f"✅ Saved: {pdf_path}")
                    else:
                        print(f"❌ PDF download failed ({response.status_code}): {pdf_url}")

                    row_data.extend([document_id, pdf_path, ref_type])
                    all_extracted_rows.append(row_data)
                except Exception as e:
                    print(f"⚠️ Row {index+1} failed: {e}")

            # Pagination logic
            pager_row = driver.find_element(By.CSS_SELECTOR, "tr.pager")
            pager_tds = pager_row.find_elements(By.CSS_SELECTOR, "td > table > tbody > tr > td")

            current_page = None
            for td in pager_tds:
                if not td.find_elements(By.TAG_NAME, "a"):
                    current_page = td.text.strip()
                    break

            if current_page in visited_pages:
                break

            visited_pages.add(current_page)

            if pagination_limit and current_page_count >= pagination_limit:
                break

            clicked = False
            for td in pager_tds:
                try:
                    a = td.find_element(By.TAG_NAME, "a")
                    if a.text.strip() in visited_pages:
                        continue
                    driver.execute_script("arguments[0].click();", a)
                    time.sleep(2)
                    current_page_count += 1
                    clicked = True
                    break
                except:
                    continue

            if not clicked:
                break
        except Exception as e:
            print("❌ Error during scraping:", e)
            break

# Step 10: Write CSV
filename = "gazette_records.csv"
try:
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            "S. No.", "Ministry / Organization", "Department", "Office", "Subject",
            "Category", "Part & Section", "Issue Date", "Publish Date", 
            "Gazette ID", "Document_id", "pdf_path", "ref_type"
        ])
        writer.writerows(all_extracted_rows)
    print(f"\n✅ All data exported to {filename}")
except Exception as e:
    print("❌ Failed to write CSV:", e)
