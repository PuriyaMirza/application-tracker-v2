import json
import re
import os
import smtplib
from email.message import EmailMessage
from playwright.sync_api import sync_playwright
from datetime import datetime

# Load email credentials from GitHub Secrets
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

companies = [
    {"name": "Perk", "url": "https://jobs.ashbyhq.com/perk", "segment": "business-travel"},
    {"name": "Engine", "url": "https://engine.com/careers", "segment": "business-travel"},
    {"name": "Deem", "url": "https://deem.com/about/careers-us", "segment": "business-travel"},
    {"name": "Hopper", "url": "https://hopper.com/careers", "segment": "consumer"},
    {"name": "GetYourGuide", "url": "https://getyourguide.careers", "segment": "consumer"},
    {"name": "Duffel", "url": "https://duffel.com/careers", "segment": "consumer"},
    {"name": "Super.com", "url": "https://super.com/careers", "segment": "consumer"},
    {"name": "Stay22", "url": "https://stay22.com/careers", "segment": "consumer"},
    {"name": "Going", "url": "https://going.com/careers", "segment": "consumer"},
    {"name": "Airalo", "url": "https://airalo.com/airalo-careers/job-vacancies", "segment": "consumer"},
    {"name": "Mews", "url": "https://mews.com/en/careers", "segment": "hospitality"},
    {"name": "Canary Technologies", "url": "https://canarytechnologies.com/jobs", "segment": "hospitality"},
    {"name": "Lighthouse", "url": "https://mylighthouse.com/company/careers", "segment": "hospitality"},
    {"name": "Cloudbeds", "url": "https://cloudbeds.com/careers", "segment": "hospitality"},
    {"name": "Revinate", "url": "https://revinate.com/about/careers/", "segment": "hospitality"},
    {"name": "Guesty", "url": "https://guesty.com/careers", "segment": "hospitality"},
    {"name": "Optibus", "url": "https://optibus.com/company/careers/", "segment": "transit"},
    {"name": "Swiftly", "url": "https://jobs.lever.co/SwiftlySystems", "segment": "transit"},
    {"name": "Masabi", "url": "https://masabi.com/we-are-hiring/", "segment": "transit"},
    {"name": "Passport Labs", "url": "https://passportinc.com/company/careers/", "segment": "transit"},
    {"name": "Token Transit", "url": "https://tokentransit.com/company/careers", "segment": "transit"},
    {"name": "Transit", "url": "https://transitapp.com/jobs", "segment": "transit"},
    {"name": "Cubic Transportation Systems", "url": "https://cubic.com/careers", "segment": "transit"},
    {"name": "Brightline", "url": "https://gobrightline.com/people-and-culture", "segment": "transit"},
    {"name": "Travelport", "url": "https://travelport.com/careers", "segment": "gds"},
    {"name": "Mondee", "url": "https://mondee.com/careers/", "segment": "gds"},
    {"name": "Accelya", "url": "https://w3.accelya.com/careers/", "segment": "gds"},
    {"name": "Avis Budget Group", "url": "https://avisbudgetgroup.jobs/search-jobs?k=product+manager", "segment": "consumer"},
    {"name": "Loews Hotels & Co", "url": "https://www.loewshotels.com/careers", "segment": "hospitality"}
]

def get_level(title):
    t = title.lower()
    if "associate" in t or "junior" in t: return "Associate"
    if "senior" in t or "sr" in t: return "Senior"
    if "group" in t or "lead" in t or "principal" in t: return "Group"
    return "PM"

def is_pm_role(title):
    t = title.lower()
    return "product manager" in t or re.search(r'\bpm\b', t)

def scrape_jobs():
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for company in companies:
            try:
                page = browser.new_page()
                page.goto(company["url"], timeout=20000, wait_until="domcontentloaded")
                
                links = page.eval_on_selector_all("a", """elements => elements.map(e => {
                    return {title: e.innerText || e.textContent, href: e.href}
                })""")
                
                for link in links:
                    title = link.get('title', '').strip()
                    if title and is_pm_role(title):
                        results.append({
                            "company": company["name"],
                            "title": title.replace('\n', ' '),
                            "level": get_level(title),
                            "location": "See posting", 
                            "url": link.get('href') or company["url"],
                            "segment": company["segment"]
                        })
                
                page.close()
            except Exception as e:
                print(f"Skipping {company['name']} due to timeout or error.")
                
        browser.close()

    unique_results = [dict(t) for t in {tuple(d.items()) for d in results}]
    return unique_results

def send_email(job_data):
    json_output = json.dumps(job_data, indent=2)
    
    # Create the dynamic file name with the current month and day
    current_date = datetime.now().strftime("%m_%d")
    filename = f"job_scan_week_{current_date}_via_github.json"
    
    msg = EmailMessage()
    msg['Subject'] = f"Weekly PM Jobs Scan: {len(job_data)} found"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    
    # Set a short message for the email body
    msg.set_content(f"Your weekly scan is complete. Found {len(job_data)} PM roles. The JSON file is attached.")
    
    # Attach the JSON data as a downloadable file
    msg.add_attachment(
        json_output.encode('utf-8'), 
        maintype='application', 
        subtype='json', 
        filename=filename
    )
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(SENDER_EMAIL, EMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    jobs = scrape_jobs()
    print(f"Found {len(jobs)} PM roles. Sending email...")
    if SENDER_EMAIL and EMAIL_PASSWORD:
        send_email(jobs)
    else:
        print("Credentials missing. Printing to console instead:")
        print(json.dumps(jobs, indent=2))
