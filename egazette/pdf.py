from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# Initialize Selenium WebDriver
driver = webdriver.Chrome()
driver.get("https://egazette.gov.in/(S(ywcght5qh3tuqqoieqyg5n1e))/ViewPDF.aspx")

try:
    # Wait for the iframe to load
    iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )
    
    # Get the iframe's src attribute (this may be the direct PDF URL)
    pdf_url = iframe.get_attribute("src")
    
    if not pdf_url or "about:blank" in pdf_url:
        raise ValueError("PDF URL not found in iframe src.")
    
    print("Found PDF URL:", pdf_url)
    
    # Download the PDF using requests
    response = requests.get(pdf_url, stream=True)
    if response.status_code == 200:
        with open("downloaded.pdf", "wb") as f:
            f.write(response.content)
        print("PDF downloaded successfully!")
    else:
        print("Failed to download PDF. Status code:", response.status_code)

except Exception as e:
    print("Error:", e)

finally:
    driver.quit()