import sqlite3
import requests
from bs4 import BeautifulSoup
import json

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

# Απαγορευμένες λέξεις (κόβει ατυχήματα, ειδήσεις, αγγελίες ακινήτων κλπ.)
BLACKLIST = [
    "τροχαίο", "τροχαιο", "νεκρός", "νεκρος", "πωλείται", "πωλειται", 
    "ενοικιάζεται", "ενοικιαζεται", "διαμέρισμα", "διαμερισμα", "οικία", 
    "εκκλησία", "εορτή", "εορτη", "συλλυπητήρια", "συνάντηση"
]

# ΥΠΟΧΡΕΩΤΙΚΕΣ λέξεις: Πρέπει ΟΠΩΣΔΗΠΟΤΕ ο τίτλος να περιέχει έστω και μία από αυτές
MANDATORY_KEYWORDS = [
    "εργασία", "εργασια", "θέση", "θεσεισ", "θέσεις", "θεση", 
    "πρόσληψη", "προσληψη", "προσλήψεις", "προσληψεις", 
    "προκήρυξη", "προκηρυξη", "προκηρύξεις", "προκηρυξεις", 
    "διαγωνισμ", "συμβασ", "σοχ", "ασεπ", "υπάλληλ", "υπαλληλ", 
    "προσωπικό", "προσωπικο", "έργο", "εργο", "μίσθωση", "μιθωσ",
    "κατάταξη", "καταταξη", "εποπ"
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
            items = soup.find_all(['h2', 'h3'])
            
            for item in items:
                a_tag = item.find('a')
                if a_tag and a_tag.get('href'):
                    title = a_tag.get_text(strip=True)
                    href = a_tag['href']
                    
                    if href.startswith('/'):
                        link = f"https://{domain}" + href
                    elif href.startswith('http'):
                        link = href
                    else:
                        continue
                    
                    if len(title) > 10:
                        title_lower = title.lower()
                        
                        # 1. Έλεγχος Blacklist
                        if any(bad in title_lower for bad in BLACKLIST):
                            continue
                        
                        # 2. Έλεγχος Mandatory Keywords (υποχρεωτικά)
                        if not any(kw in title_lower for kw in MANDATORY_KEYWORDS):
                            continue
                        
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
            print(f"Σφάλμα: {e}")

    conn.close()
    print(f"Προστέθηκαν {total_added} καθαρές αγγελίες.")

def generate_html():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, link, source, date_added FROM jobs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

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

    jobs_json = json.dumps(js_jobs, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Radar - Προσωπικό Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen py-6 px-4" x-data="jobApp({{jobs: {jobs_json}}})">
    <div class="max-w-4xl mx-auto">
        
        <!-- HEADER -->
        <header class="mb-6 flex flex-col md:flex-row justify-between items-center bg-slate-800 p-5 rounded-2xl shadow-xl border border-slate-700 gap-4">
            <div>
                <h1 class="text-2xl font-black text-white flex items-center gap-2">
                    <span>💼</span> Job Radar Αρκαδίας
                </h1>
                <p class="text-slate-400 text-xs mt-1">Αυτόματη παρακολούθηση & φιλτράρισμα θέσεων εργασίας</p>
            </div>
            <div class="flex items-center gap-3">
                <span class="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-3 py-1.5 rounded-xl font-medium">
                    Ενεργές: <strong x-text="jobs.length"></strong>
                </span>
            </div>
        </header>

        <!-- CONTROL PANEL (SEARCH & TABS) -->
        <div class="bg-slate-800 p-4 rounded-2xl shadow-xl mb-6 border border-slate-700 space-y-3">
            <div class="relative">
                <input type="text" x-model="search" placeholder="🔍 Αναζήτηση (π.χ. Πληροφορική, ΣΟΧ, Δήμος, Τρίπολη)..." 
                    class="w-full bg-slate-900 text-slate-100 px-4 py-3 pl-11 rounded-xl border border-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm placeholder-slate-500">
                <span class="absolute left-4 top-3.5 text-slate-500">⚡</span>
            </div>

            <div class="flex flex-wrap gap-2 pt-2 border-t border-slate-700/60">
                <button @click="currentTab = 'all'" :class="currentTab === 'all' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' : 'bg-slate-900 text-slate-400 hover:bg-slate-700'" class="px-3.5 py-2 rounded-xl text-xs font-bold transition">
                    Όλες (<span x-text="jobs.length"></span>)
                </button>
                <button @click="currentTab = 'saved'" :class="currentTab === 'saved' ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/30' : 'bg-slate-900 text-slate-400 hover:bg-slate-700'" class="px-3.5 py-2 rounded-xl text-xs font-bold transition">
                    ⭐ Αγαπημένες (<span x-text="savedIds.length"></span>)
                </button>
                <button @click="currentTab = 'ppel'" :class="currentTab === 'ppel' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/30' : 'bg-slate-900 text-slate-400 hover:bg-slate-700'" class="px-3.5 py-2 rounded-xl text-xs font-bold transition">
                    Περιφέρεια
                </button>
                <button @click="currentTab = 'kalimera'" :class="currentTab === 'kalimera' ? 'bg-sky-600 text-white shadow-lg shadow-sky-500/30' : 'bg-slate-900 text-slate-400 hover:bg-slate-700'" class="px-3.5 py-2 rounded-xl text-xs font-bold transition">
                    Καλημέρα Αρκαδία
                </button>
            </div>
        </div>

        <!-- LISTING CONTAINER -->
        <div class="space-y-3" x-show="filteredJobs.length > 0">
            <template x-for="job in filteredJobs" :key="job.id">
                <div class="bg-slate-800 p-5 rounded-2xl shadow-md border border-slate-700/80 hover:border-slate-600 transition flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-2">
                            <span class="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-md" 
                                :class="job.source.includes('Περιφέρεια') ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-sky-950 text-sky-400 border border-sky-800'" 
                                x-text="job.source"></span>
                            <span class="text-xs text-slate-400" x-text="'📅 ' + job.date"></span>
                        </div>
                        <h2 class="text-sm md:text-base font-semibold text-slate-100 leading-snug" x-text="job.title"></h2>
                    </div>
                    <div class="flex items-center gap-2.5 w-full md:w-auto justify-end">
                        <button @click="toggleSave(job.id)" class="p-2.5 rounded-xl border transition text-sm"
                            :class="savedIds.includes(job.id) ? 'bg-amber-500/20 border-amber-500 text-amber-400' : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-amber-400'"
                            title="Αποθήκευση στα αγαπημένα">
                            <span x-text="savedIds.includes(job.id) ? '⭐' : '☆'"></span>
                        </button>
                        <a :href="job.link" target="_blank" @click="markAsRead(job.id)" 
                            class="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-xl transition shadow-lg shadow-blue-600/20 whitespace-nowrap flex items-center gap-1.5">
                            <span>Άνοιγμα</span>
                            <span>→</span>
                        </a>
                    </div>
                </div>
            </template>
        </div>

        <!-- EMPTY STATE -->
        <div class="bg-slate-800 p-12 rounded-2xl shadow-xl text-center border border-slate-700 text-slate-400" x-show="filteredJobs.length === 0">
            <p class="text-lg">Δεν βρέθηκαν αγγελίες με βάση τα κριτήρια αναζήτησης.</p>
        </div>

    </div>

    <script>
        function jobApp(data) {{
            return {{
                jobs: data.jobs,
                search: '',
                currentTab: 'all',
                savedIds: JSON.parse(localStorage.getItem('saved_job_ids') || '[]'),
                readIds: JSON.parse(localStorage.getItem('read_job_ids') || '[]'),

                toggleSave(id) {{
                    if (this.savedIds.includes(id)) {{
                        this.savedIds = this.savedIds.filter(i => i !== id);
                    }} else {{
                        this.savedIds.push(id);
                    }}
                    localStorage.setItem('saved_job_ids', JSON.stringify(this.savedIds));
                }},

                markAsRead(id) {{
                    if (!this.readIds.includes(id)) {{
                        this.readIds.push(id);
                        localStorage.setItem('read_job_ids', JSON.stringify(this.readIds));
                    }}
                }},

                get filteredJobs() {{
                    return this.jobs.filter(job => {{
                        let matchesSearch = job.title.toLowerCase().includes(this.search.toLowerCase());
                        
                        let matchesTab = true;
                        if (this.currentTab === 'saved') {{
                            matchesTab = this.savedIds.includes(job.id);
                        }} else if (this.currentTab === 'ppel') {{
                            matchesTab = job.source.includes('Περιφέρεια');
                        }} else if (this.currentTab === 'kalimera') {{
                            matchesTab = job.source.includes('Καλημέρα');
                        }}

                        return matchesSearch && matchesTab;
                    }});
                }}
            }}
        }}
    </script>
</body>
</html>
"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Το index.html δημιουργήθηκε επιτυχώς!")

if __name__ == "__main__":
    scrape_jobs()
    generate_html()
