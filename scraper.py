import sqlite3
import requests
from bs4 import BeautifulSoup

DB_NAME = "jobs.db"
HTML_FILE = "index.html"

TARGETS = [
    {
        "name": "Καλημέρα Αρκαδία",
        "url": "https://www.kalimera-arkadia.gr/theseis-ergasias.html",
        "domain": "kalimera-arkadia.gr"
    },
    {
        "name": "Περιφέρεια Πελοποννήσου",
        "url": "https://www.ppel.gov.gr/category/diakyrixeis-prokyrixeis/",
        "domain": "ppel.gov.gr"
    }
]

KEYWORDS = [
    "συμβασης", "μισθωσης", "εργου", "προκηρυξης", "προκηρυξη", 
    "πινακες", "καταταξης", "ασεπ", "προσληψη", "πληροφορικη", 
    "πληροφορικής", "εργασια", "εργασία", "σοχ"
]

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            source TEXT DEFAULT 'Άλλο',
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def scrape_jobs():
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    total_added = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for target in TARGETS:
        target_url = target["url"]
        source_name = target["name"]
        domain = target["domain"]

        try:
            response = requests.get(target_url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.find_all('a')
            
            for a_tag in links:
                href = a_tag.get('href')
                title = a_tag.get_text(strip=True)
                
                if href and title and len(title) > 10:
                    if href.startswith('/'):
                        link = f"https://{domain}" + href
                    elif href.startswith('http'):
                        link = href
                    else:
                        continue
                    
                    if domain in link and link != target_url:
                        title_lower = title.lower()
                        matched = any(kw in title_lower for kw in KEYWORDS)
                        
                        if matched:
                            try:
                                cursor.execute(
                                    "INSERT INTO jobs (title, link, source) VALUES (?, ?, ?)", 
                                    (title, link, source_name)
                                )
                                conn.commit()
                                total_added += 1
                            except sqlite3.IntegrityError:
                                pass
        except Exception as e:
            print(f"Σφάλμα στο {target_url}: {e}")

    conn.close()
    print(f"Συνολικά προστέθηκαν {total_added} νέες σχετικές αγγελίες.")

def generate_html():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, link, source, date_added FROM jobs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    # Μετατροπή δεδομένων σε JavaScript array για έξυπνο filtering στον browser
    js_jobs = []
    for r in rows:
        job_id, title, link, source, date = r
        js_jobs.append({
            "id": job_id,
            "title": title,
            "link": link,
            "source": source,
            "date": date
        })

    import json
    jobs_json = json.dumps(js_jobs, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Έξυπνο Dashboard Αγγελιών</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
<body class="bg-slate-50 min-h-screen py-8 px-4" x-data="jobApp({{jobs: {jobs_json}}})">
    <div class="max-w-4xl mx-auto">
        
        <!-- HEADER -->
        <header class="mb-6 text-center">
            <h1 class="text-3xl font-extrabold text-slate-800">💼 Dashboard Αγγελιών & Προκηρύξεων</h1>
            <p class="text-slate-500 mt-1">Αυτόματη παρακολούθηση & έξυπνη αποθήκευση</p>
        </header>

        <!-- SEARCH & TABS -->
        <div class="bg-white p-4 rounded-xl shadow-md mb-6 border border-slate-100 space-y-4">
            <div class="relative">
                <input type="text" x-model="search" placeholder="🔍 Αναζήτηση με λέξη-κλειδί (π.χ. Πληροφορική, ΣΟΧ, Δήμος)..." 
                    class="w-full px-4 py-3 pl-12 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm">
                <span class="absolute left-4 top-3.5 text-slate-400">⚡</span>
            </div>

            <div class="flex flex-wrap gap-2 justify-between items-center pt-2 border-t border-slate-100">
                <div class="flex flex-wrap gap-2">
                    <button @click="currentTab = 'all'" :class="currentTab === 'all' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'" class="px-3 py-1.5 rounded-lg text-xs font-semibold transition">
                        Όλες (<span x-text="jobs.length"></span>)
                    </button>
                    <button @click="currentTab = 'saved'" :class="currentTab === 'saved' ? 'bg-amber-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'" class="px-3 py-1.5 rounded-lg text-xs font-semibold transition">
                        ⭐ Αγαπημένες (<span x-text="savedIds.length"></span>)
                    </button>
                    <button @click="currentTab = 'ppel'" :class="currentTab === 'ppel' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'" class="px-3 py-1.5 rounded-lg text-xs font-semibold transition">
                        Περιφέρεια Πελοποννήσου
                    </button>
                    <button @click="currentTab = 'kalimera'" :class="currentTab === 'kalimera' ? 'bg-sky-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'" class="px-3 py-1.5 rounded-lg text-xs font-semibold transition">
                        Καλημέρα Αρκαδία
                    </button>
                </div>
            </div>
        </div>

        <!-- LIST OF JOBS -->
        <div class="bg-white shadow-lg rounded-xl overflow-hidden border border-slate-100">
            <div class="divide-y divide-slate-100" x-show="filteredJobs.length > 0">
                <template x-for="job in filteredJobs" :key="job.id">
                    <div class="p-5 hover:bg-slate-50 transition flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-1.5">
                                <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full" 
                                    :class="job.source.includes('Περιφέρεια') ? 'bg-emerald-100 text-emerald-800' : 'bg-sky-100 text-sky-800'" 
                                    x-text="job.source"></span>
                                <span class="text-xs text-slate-400" x-text="'Καταγράφ
