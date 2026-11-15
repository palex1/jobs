import sqlite3
import requests
from bs4 import BeautifulSoup

DB_NAME = "jobs.db"
HTML_FILE = "index.html"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def scrape_jobs():
    init_db()
    
    target_url = "https://www.kalimera-arkadia.gr/theseis-ergasias.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(target_url, headers=headers)
        if response.status_code != 200:
            print(f"Σφάλμα σύνδεσης: Status code {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, "html.parser")
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Αναζήτηση τίτλων σε h2 και h3
        items = soup.find_all(['h2', 'h3'])
        
        count = 0
        for item in items:
            a_tag = item.find('a')
            if a_tag and a_tag.get('href'):
                title = a_tag.get_text(strip=True)
                link = a_tag['href']
                
                if link.startswith('/'):
                    link = "https://www.arcadiaportal.gr" + link
                
                # Αφού βρισκόμαστε ήδη στη σελίδα κατηγορίας εργασίας, αποθηκεύουμε τους τίτλους
                if len(title) > 10:
                    try:
                        cursor.execute("INSERT INTO jobs (title, link) VALUES (?, ?)", (title, link))
                        conn.commit()
                        count += 1
                    except sqlite3.IntegrityError:
                        pass # Υπάρχει ήδη στη βάση

        print(f"Προστέθηκαν {count} νέες αγγελίες.")
        conn.close()
    except Exception as e:
        print(f"Σφάλμα κατά το scraping: {e}")

def generate_html():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT title, link, date_added FROM jobs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    html_content = f"""<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Θέσεις Εργασίας - Αρκαδία</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 min-h-screen py-10 px-4">
    <div class="max-w-4xl mx-auto">
        <header class="mb-8 text-center">
            <h1 class="text-3xl font-extrabold text-slate-800">💼 Αγγελίες Εργασίας - ArcadiaPortal</h1>
            <p class="text-slate-500 mt-2">Αυτόματη συγκέντρωση αγγελιών για την περιοχή μας</p>
        </header>

        <div class="bg-white shadow-lg rounded-xl overflow-hidden border border-slate-100">
            <div class="p-4 bg-slate-100 border-b border-slate-200 font-semibold text-slate-700 flex justify-between items-center">
                <span>Συνολικά αποθηκευμένες αγγελίες</span>
                <span class="bg-blue-600 text-white text-xs px-2.5 py-1 rounded-full">{len(rows)}</span>
            </div>
            <div class="divide-y divide-slate-100">
"""

    if not rows:
        html_content += """
                <div class="p-8 text-center text-slate-400">
                    Δεν βρέθηκαν αγγελίες ακόμα. Το σύστημα θα σαρώσει σύντομα!
                </div>
        """
    else:
        for title, link, date in rows:
            html_content += f"""
                <div class="p-6 hover:bg-slate-50 transition flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 class="text-lg font-semibold text-slate-800">{title}</h2>
                        <span class="text-xs text-slate-400 block mt-1">Καταγράφηκε: {date}</span>
                    </div>
                    <a href="{link}" target="_blank" class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition shadow-sm whitespace-nowrap">
                        Άνοιγμα Αγγελίας →
                    </a>
                </div>
"""

    html_content += """
            </div>
        </div>
    </div>
</body>
</html>
"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Το index.html δημιουργήθηκε επιτυχώς!")

if __name__ == "__main__":
    scrape_jobs()
    generate_html()
