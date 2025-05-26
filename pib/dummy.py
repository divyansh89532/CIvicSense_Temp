from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from datetime import datetime
from xhtml2pdf import pisa
import os
import json
import time

# Setup Chrome browser
options = Options()
options.headless = False  # Set True for headless mode
driver = webdriver.Chrome(options=options)

# Directories
BASE_DIR = os.getcwd()
PDF_DIR = os.path.join(BASE_DIR, "speeches_pdf")
HTML_PDF_DIR = os.path.join(PDF_DIR, "html_to_pdf")
os.makedirs(HTML_PDF_DIR, exist_ok=True)
output_json_path = os.path.join(BASE_DIR, "extracted_results.json")

results_metadata = []

def html_to_pdf(title: str, html_snippet: str, output_path: str):
    """Convert HTML content to a PDF file using xhtml2pdf."""
    full_html = f"""
    <html>
      <head><meta charset="utf-8"></head>
      <body>
        <h1 class='center'>{title}</h1>
        {html_snippet}
      </body>
    </html>
    """
    with open(output_path, "wb") as f:
        pisa_status = pisa.CreatePDF(full_html, dest=f)
    if pisa_status.err:
        raise RuntimeError("❌ xhtml2pdf conversion error")
    return output_path


def extract_item_content_and_save():
    """Extract content from iframe, convert to PDF, and return metadata."""
    wait = WebDriverWait(driver, 15)
    
    # Switch to iframe
    iframe = wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_iframepressrealese")))
    driver.switch_to.frame(iframe)
    
    # Get form data
    form = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form#form1")))
    title = form.find_element(By.ID, "ltrTitlee").get_attribute("value") or "untitled"
    html_body = form.find_element(By.ID, "ltrDescriptionn").get_attribute("value") or "<p>(no content)</p>"
    
    # Create safe filename
    safe_title = "".join(c if c.isalnum() else "_" for c in title)[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_name = f"{timestamp}_{safe_title}.pdf"
    pdf_path = os.path.join(HTML_PDF_DIR, pdf_name)
    
    # Save PDF
    html_to_pdf(title, html_body, pdf_path)
    print(f"✅ Saved PDF: {pdf_path}")
    
    # Return to main page
    driver.switch_to.default_content()
    return title, pdf_path


def extract_items_data(section_name):
    """Extract items (speeches or press releases) and save them to PDF."""
    wait = WebDriverWait(driver, 10)
    try:
        time.sleep(2)
        list_items = driver.find_elements(By.CSS_SELECTOR, "div.content-area ul.num > li")
        print(f"🔎 Found {len(list_items)} items on {section_name} page.")
        
        for li in list_items:
            try:
                a_tag = li.find_element(By.TAG_NAME, "a")
                span_tag = li.find_element(By.TAG_NAME, "span")
                
                title = a_tag.text.strip()
                date_info = span_tag.text.strip()
                print(f"\n📄 Title: {title}")
                print(f"📅 Date: {date_info}")
                
                main_window = driver.current_window_handle
                
                # Open in new tab
                a_tag.send_keys(Keys.CONTROL + Keys.RETURN)
                time.sleep(1)
                
                # Switch to new tab
                driver.switch_to.window([w for w in driver.window_handles if w != main_window][0])
                
                # Extract & Save
                title, pdf_path = extract_item_content_and_save()
                print(f"✅ [{section_name}] {title} | {date_info} | {pdf_path}")
                
                # storing the metadata
                results_metadata.append({
                    "section":section_name,
                    "title":title,
                    "date": date_info,
                    "pdf_path": pdf_path
                })

                # Close tab and switch back
                driver.close()
                driver.switch_to.window(main_window)
                print("-" * 40)
            
            except Exception as inner_e:
                print(f"⚠️ Error processing item: {str(inner_e)}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(main_window)
    
    except Exception as e:
        print(f"❌ Error extracting data on {section_name} page: {str(e)}")


def process_section(title_attr, section_name):
    """Navigate to section and extract content month-wise."""
    wait = WebDriverWait(driver, 10)
    
    # refreshing and going to the main page before navigating to a new section section
    driver.get("https://pib.gov.in/")
    time.sleep(2)   

    # Use refined XPath to ensure correct button is clicked
    section_xpath = f"//div[@class='pm-section text-center']//a[@title='{title_attr}']"
    section_link = wait.until(EC.element_to_be_clickable((By.XPATH, section_xpath)))
    section_link.click()
    print(f"\n✅ Navigated to {section_name} section.")

    time.sleep(2)

    # Select Year & Month
    now = datetime.now()
    current_month_index = now.month
    current_year = str(now.year)

    year_select = Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlYear"))
    year_select.select_by_visible_text(current_year)
    print(f"📅 Selected Year: {current_year}")
    time.sleep(3)

    for month_index in range(1, current_month_index + 1):
        month_select = Select(driver.find_element(By.ID, "ContentPlaceHolder1_ddlMonth"))
        month_name = datetime(1900, month_index, 1).strftime('%B')
        month_select.select_by_visible_text(month_name)
        print(f"\n🔄 Processing Month: {month_name} ({section_name})")
        time.sleep(3)
        
        extract_items_data(section_name)


# === MAIN EXECUTION ===
try:
    driver.get("https://pib.gov.in/")
    
    # Process Speeches
    process_section("Speeches", "Speeches")

    # Process Press Releases
    process_section("Press Releases", "Press Releases")

except Exception as e:
    print(f"❌ Main execution error: {str(e)}")

finally:
    with open(output_json_path, "w", encoding="utf-8") as json_file:
        json.dump(results_metadata, json_file, ensure_ascii=False, indent=2)
    print(f"✅ Results saved to {output_json_path}")

    
    ##############################################################################
    # Final cleanup        
    print("🏁 Script completed.")
    driver.quit()
