import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(layout="wide")
st.title("CityU HKTech300 Startups Scraper")
st.markdown("Scrapes all  pages for Company Name, CityU URL, Website, and Email.")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Step 1: Collect company names and URLs from the main page
@st.cache_data(show_spinner="Collecting company list...")
def collect_companies():
    company_list = []
    page = 0

    while True:
        url = f"https://www.cityu.edu.hk/hktech300/start-ups/all-start-ups?page={page}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            blocks = soup.find_all("li", class_="col-md-4 sm-12 mb-3")

            if not blocks:
                break # End of pagination

            for block in blocks:
                link_tag = block.find_all("a", href=True)[-1]
                name = link_tag.text.strip()
                full_url = link_tag['href']
                if not full_url.startswith("http"):
                    full_url = "https://www.cityu.edu.hk" + full_url

                company_list.append({
                    "Company Name": name,
                    "CityU URL": full_url,
                    "Page Number": page + 1,
                    "Company Website": "",
                    "Email": ""
                })

        except Exception as e:
            st.warning(f"Failed on page {page + 1}: {e}")
            break

        page += 1

    return company_list

# Step 2: Scrape email and website from company profile page
def scrape_details(company):
    try:
        res = requests.get(company["CityU URL"], headers=HEADERS, timeout=10)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")
        article = soup.find("article")
        if not article:
            company["Email"] = "Info Not Found"
            company["Company Website"] = "Info Not Found"
            return company

        for a_tag in article.find_all("a", href=True):
            href = a_tag['href']
            if href.startswith("mailto:") and not company["Email"]:
                company["Email"] = href.replace("mailto:", "")
            elif href.startswith("http") and "cityu.edu.hk" not in href and not company["Company Website"]:
                company["Company Website"] = href

        # Set "Info Not Found" if still empty
        if not company["Email"]:
            company["Email"] = "Info Not Found"
        if not company["Company Website"]:
            company["Company Website"] = "Info Not Found"

    except Exception:
        company["Email"] = "Info Not Found"
        company["Company Website"] = "Info Not Found"

    return company

# Step 3: button to trigger scraping
if st.button("Start Scraping Now"):
    companies = collect_companies()
    total = len(companies)
    results = []

    st.info(f"Found {total} companies. Scraping details now...")
    progress = st.progress(0)
    status = st.empty()

    # Use multithreading for faster scraping
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(scrape_details, c): c for c in companies}
        for idx, future in enumerate(as_completed(futures), 1):
            company = future.result()
            results.append(company)
            percent = idx / total
            progress.progress(percent)
            status.text(f"Scraping {idx}/{total} [{percent*100:.1f}%]")

    # Save results to Excel
    df = pd.DataFrame(results)
    df.to_excel("hktech300_full_details.xlsx", index=False)
    st.success("Scraping completed!")
    st.dataframe(df)

    with open("hktech300_full_details.xlsx", "rb") as f:
        st.download_button(
            label="Download Excel File",
            data=f,
            file_name="hktech300_full_details.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
