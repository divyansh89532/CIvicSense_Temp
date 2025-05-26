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



# Step 6: Select “Act” from dropdown
try:
    dropdown = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "ddlreftype"))
    )
    select = Select(dropdown)
    select.select_by_visible_text("Act")
    print("✅ Selected 'Act' from dropdown.")
    time.sleep(1)  # Wait for postback content load (important)
except Exception as e:
    print("❌ Failed to select dropdown option:", e)


# Step 7: Immediately click the Submit button (no wait)
submit_btn = driver.find_element(By.ID, "ImgSubmitDetails")
driver.execute_script("arguments[0].click();", submit_btn)
print("✅ Submit button clicked.")


# Step 8: Get total number of gazettes
try:
    result_span = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "lbl_Result"))
    )
    total_text = result_span.text
    print("🧾", total_text)

    # Extract the number using regex
    match = re.search(r'\d+', total_text)
    if match:
        total_gazettes = int(match.group())
        print("📊 Total Gazettes:", total_gazettes)
    else:
        print("⚠️ Could not extract number from text.")
except Exception as e:
    print("❌ Failed to extract gazette count:", e)


# Step 9: Extract rows from the correctly nested data table inside tbl_Gazette
all_extracted_rows = []
visited_pages = set()
pagination_limit = 2  # 👉 Set to None to scrape all pages, or set to a specific number like 3
download_folder = "downloads"
os.makedirs(download_folder, exist_ok=True)
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

            row_data = [col.text.strip() for col in cols[:-1]]  # Exclude the last <td> it contains the pdf size


            try:
                # Extract year from 3rd last <td>
                date_text = cols[-3].text.strip()  # e.g., "16-Apr-2025"
                year = date_text.split("-")[-1]

                # Extract document ID from 2nd last <td>
                doc_id_text = cols[-2].text.strip()  # e.g., "CG-DL-E-16042025-262469"
                document_id = doc_id_text.split("-")[-1]

                # Construct PDF URL
                pdf_url = f"https://egazette.gov.in/WriteReadData/{year}/{document_id}.pdf"
                print(f"📄 Downloading PDF: {pdf_url}")

                # Download and save the PDF
                response = requests.get(pdf_url, stream=True)
                if response.status_code == 200:
                    pdf_filename = f"{document_id}.pdf"
                    pdf_path = os.path.join(download_folder, pdf_filename)
                    with open(pdf_path, "wb") as f:
                        f.write(response.content)
                    print(f"✅ Saved to: {pdf_path}")
                else:
                    print(f"❌ Failed to download (status {response.status_code}) for {pdf_url}")
                
                row_data.extend([document_id,pdf_path])  # Optional: append these to row_data if you need later

            except Exception as e:
                print(f"⚠️ Failed to extract year and document ID for row {index + 1}: {e}")

            all_extracted_rows.append(row_data)

    # --------------------PAGINATION LOGIC----------------------------
        # # Identify pager row and current page
        pager_row = driver.find_element(By.CSS_SELECTOR, "tr.pager")
        current_page = None
        pager_tds = pager_row.find_elements(By.CSS_SELECTOR, "td > table > tbody > tr > td")
        for td in pager_tds:
            if not td.find_elements(By.TAG_NAME, "a"):
                current_page = td.text.strip()
                break

        # Avoid revisiting same page
        if current_page in visited_pages:
            print(f"⚠️ Already visited page {current_page}. Stopping loop.")
            break

        visited_pages.add(current_page)

        # Check if pagination limit is reached
        if pagination_limit and current_page_count >= pagination_limit:
            print(f"✅ Reached pagination limit: {pagination_limit} pages.")
            break

        # Click next page link
        clicked = False
        for td in pager_tds:
            try:
                a = td.find_element(By.TAG_NAME, "a")
                page_text = a.text.strip()
                if page_text in visited_pages:
                    continue

                driver.execute_script("arguments[0].click();", a)
                time.sleep(2)
                current_page_count += 1
                clicked = True
                break
            except:
                continue

        if not clicked:
            print("✅ No more pages to navigate.")
            break

    except Exception as e:
        print("❌ Exception occurred:", e)
        break

print(f"✅ Total records extracted: {len(all_extracted_rows)}")

# Step 10: saving the data to a CSV file

# Choose a filename
filename = "gazette_records.csv"

# Export to CSV
try:
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # Optional: Add a header row (modify as per actual columns)
        writer.writerow(["S. No.", "Ministry / Organization", "Department", "Office", "Subject"," Category","Part & Section", "Issue Date","Publish Date","Gazette ID","Document_id","pdf_path"])

        # Write all extracted rows
        writer.writerows(all_extracted_rows)

    print(f"✅ Data successfully exported to {filename}")
except Exception as e:
    print("❌ Failed to write CSV:", e)


# Hold for inspection
print("🔍 Holding browser open so you can inspect the main page...")
input("👀 Press Enter here to close the browser when done...")

driver.quit()
