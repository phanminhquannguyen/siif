import requests
import json

BASE_API = "https://asx.api.markitdigital.com/asx-research/1.0/markets/announcements"
ENTITY_ID1 = "204115474"  # CSL Limited entityXid
PAGE_SIZE = 25
SUMMARY_DATE = "2025-08-14"
HEADERS = {"User-Agent": "Mozilla/5.0"}
VERSION_UID= "4a466cc3f899e00730cfbfcd5ab8940c41f474b6"


TARGET_COMPANY = input("Enter your ASX listed company ticker in CAPS: ")
TARGET_YEAR = int(input("What year's annual report would you like: "))


def fetch_announcements(page=1):
    url = (
        f"{BASE_API}"
        f"?entityXids={ENTITY_ID}"
        f"&page={page}"
        f"&itemsPerPage={PAGE_SIZE}"
        f"&summaryCountsDate={SUMMARY_DATE}"
    )
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def download_pdf(doc_key, version_uid, filename):
    pdf_url = f"https://cdn-api.markitdigital.com/apiman-gateway/ASX/asx-research/1.0/file/{doc_key}&v={version_uid}"
    r = requests.get(pdf_url, headers=HEADERS)
    r.raise_for_status()
    with open(filename, "wb") as f:
        f.write(r.content)


with open("test_scraper/asx_entities.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Make the dictionary: {ASX code -> entityXid}
entity_map = {item["asxCode"]: item["entityXid"] for item in data["data"]}

ENTITY_ID = entity_map[TARGET_COMPANY]
print(entity_map[TARGET_COMPANY])



# Loop through pages
page = 1
found = False

while not found:
    data = fetch_announcements(page)
    items = data.get("data", {}).get("items", [])  
    if not items:
        break
    for row in items:
        if "Full Year Accounts" in row.get("announcementTypes", []):
            report_year = int(row["date"][:4])
            print(f"report year: {report_year}")
            if report_year == TARGET_YEAR:
                doc_key = row["documentKey"]
                filename = f"{row['symbol']}_{row['date'][:10]}.pdf"
                download_pdf(doc_key, VERSION_UID, filename)
                print(f"Downloaded {filename}")
                found = True
                break
    page += 1
