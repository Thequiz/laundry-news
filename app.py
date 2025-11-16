import os
import json
import requests
from bs4 import BeautifulSoup
import re
from flask import Flask, jsonify, render_template_string
from datetime import datetime
import threading
import time

app = Flask(__name__)

# Global status
scrape_status = {
    "is_scraping": False,
    "completed": False,
    "progress": "Inte startad",
    "current_page": 0,
    "total_articles": 0,
    "error": None
}

articles_cache = []

def scrape_laundry_news():
    """Scrapa The Laundry News - körs i bakgrunden"""
    global articles_cache, scrape_status
    
    print("🔍 Startar background scraping...")
    scrape_status["is_scraping"] = True
    scrape_status["progress"] = "Startar scraping..."
    scrape_status["completed"] = False
    
    articles = []
    seen = set()
    
    try:
        for page in range(1, 50):  # Första 50 sidorna
            try:
                scrape_status["current_page"] = page
                scrape_status["progress"] = f"Scrapar sida {page}/50..."
                
                url = f"https://thelaundrynews.com/page/{page}/" if page > 1 else "https://thelaundrynews.com/"
                
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0'
                })
                
                if response.status_code != 200:
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Hitta alla externa länkar
                links = {}
                for a in soup.find_all('a', href=True):
                    href = a.get('href')
                    text = a.get_text(strip=True)
                    if href and 'http' in href and 'thelaundrynews' not in href and len(text) > 20:
                        links[text] = href
                
                # Hitta artiklar via text-parsing
                text = soup.get_text()
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                
                source = None
                for i, line in enumerate(lines):
                    if re.match(r'\d{1,2} \w+,? \d{4}', line) and i > 0 and i < len(lines) - 1:
                        date = line
                        potential_source = lines[i-1]
                        title = lines[i+1]
                        
                        if (potential_source and len(potential_source) < 100 and 
                            title and 30 < len(title) < 400 and
                            title not in seen):
                            
                            # Hitta länk
                            url = None
                            for link_text, link_url in links.items():
                                if len(set(title.lower().split()) & set(link_text.lower().split())) > 3:
                                    url = link_url
                                    break
                            
                            # Klassificera
                            tl = title.lower()
                            if any(w in tl for w in ['fraud', 'scam']):
                                topic, severity = 'fraud', 'high'
                            elif any(w in tl for w in ['trafficking', 'smuggling']):
                                topic, severity = 'crime', 'high'
                            elif 'corruption' in tl:
                                topic, severity = 'corruption', 'high'
                            else:
                                topic, severity = 'crime', 'medium'
                            
                            # Källtyp
                            sl = potential_source.lower()
                            if any(w in sl for w in ['eppo', 'europol', 'fca', 'gov']):
                                source_type = 'official'
                            elif any(w in sl for w in ['guardian', 'bbc']):
                                source_type = 'news'
                            elif any(w in sl for w in ['occrp', 'global initiative']):
                                source_type = 'report'
                            else:
                                source_type = 'unknown'
                            
                            articles.append({
                                'source': potential_source,
                                'title': title,
                                'date': date,
                                'url': url,
                                'source_type': source_type,
                                'topic': topic,
                                'severity': severity
                            })
                            
                            seen.add(title)
                
                scrape_status["total_articles"] = len(articles)
                
                if page % 10 == 0:
                    print(f"   Scrapade {page} sidor, {len(articles)} artiklar hittills...")
                
            except Exception as e:
                print(f"   Fel på sida {page}: {e}")
                break
        
        # Spara
        with open('articles.json', 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        articles_cache = articles
        scrape_status["completed"] = True
        scrape_status["is_scraping"] = False
        scrape_status["progress"] = f"Klart! {len(articles)} artiklar scrapade."
        
        print(f"✅ Scraping klar! {len(articles)} artiklar sparade.")
        
    except Exception as e:
        scrape_status["error"] = str(e)
        scrape_status["is_scraping"] = False
        scrape_status["progress"] = f"Fel: {str(e)}"
        print(f"❌ Scraping-fel: {e}")

def load_existing_articles():
    """Ladda existerande artiklar från fil"""
    global articles_cache
    
    if os.path.exists('articles.json'):
        try:
            with open('articles.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)
                if len(articles) > 10:
                    articles_cache = articles
                    print(f"✅ Laddade {len(articles)} artiklar från cache")
                    return True
        except Exception as e:
            print(f"⚠️ Kunde inte ladda cache: {e}")
    
    return False

# Försök ladda befintliga artiklar vid uppstart
if not load_existing_articles():
    # Starta scraping i bakgrunden automatiskt
    print("📥 Ingen cache hittades, startar automatisk scraping...")
    thread = threading.Thread(target=scrape_laundry_news, daemon=True)
    thread.start()

@app.route('/')
def index():
    global articles_cache, scrape_status
    
    # Om scraping pågår, visa statusida
    if scrape_status["is_scraping"]:
        return f"""
        <!DOCTYPE html>
        <html lang="sv">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="5">
            <title>Scraping pågår...</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    text-align: center;
                }}
                .loader {{
                    border: 8px solid #f3f3f3;
                    border-top: 8px solid #2a5298;
                    border-radius: 50%;
                    width: 60px;
                    height: 60px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                .status {{
                    background: rgba(255,255,255,0.1);
                    padding: 40px;
                    border-radius: 12px;
                    backdrop-filter: blur(10px);
                }}
            </style>
        </head>
        <body>
            <div class="status">
                <h1>⏳ Scraping pågår...</h1>
                <div class="loader"></div>
                <p style="font-size: 1.2em; margin: 20px 0;">{scrape_status['progress']}</p>
                <p>Sida: {scrape_status['current_page']}/50</p>
                <p>Artiklar hittade: {scrape_status['total_articles']}</p>
                <p style="opacity: 0.7; margin-top: 20px;">Sidan uppdateras automatiskt var 5:e sekund...</p>
            </div>
        </body>
        </html>
        """
    
    # Om inga artiklar finns ännu
    if not articles_cache:
        return """
        <!DOCTYPE html>
        <html lang="sv">
        <head>
            <meta charset="UTF-8">
            <title>Startar scraping...</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    text-align: center;
                }
                button {
                    background: white;
                    color: #1e3c72;
                    border: none;
                    padding: 15px 40px;
                    font-size: 1.2em;
                    border-radius: 8px;
                    cursor: pointer;
                    margin-top: 20px;
                }
                button:hover {
                    background: #f0f0f0;
                }
            </style>
        </head>
        <body>
            <div>
                <h1>🚀 Välkommen till The Laundry News</h1>
                <p style="font-size: 1.1em; margin: 20px 0;">Ingen data tillgänglig ännu.</p>
                <button onclick="window.location.href='/start-scrape'">Starta Scraping</button>
            </div>
        </body>
        </html>
        """
    
    articles = articles_cache
    
    html = """
    <!DOCTYPE html>
    <html lang="sv">
    <head>
        <meta charset="UTF-8">
        <title>The Laundry News - Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            header {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 40px;
                text-align: center;
                position: relative;
            }
            h1 { font-size: 2.8em; margin-bottom: 10px; }
            .refresh-btn {
                position: absolute;
                top: 20px;
                right: 20px;
                background: rgba(255,255,255,0.2);
                color: white;
                border: 2px solid white;
                padding: 10px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 1em;
            }
            .refresh-btn:hover {
                background: rgba(255,255,255,0.3);
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                padding: 30px;
                background: #f8f9fa;
            }
            .stat-card {
                padding: 25px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                border-left: 5px solid #2a5298;
            }
            .stat-value {
                font-size: 2.5em;
                font-weight: bold;
                color: #2a5298;
            }
            .stat-label {
                color: #666;
                font-size: 0.95em;
                margin-top: 5px;
            }
            .content {
                padding: 30px;
                max-height: 800px;
                overflow-y: auto;
            }
            .article {
                padding: 20px;
                margin-bottom: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 5px solid #2a5298;
                transition: all 0.3s;
            }
            .article:hover {
                background: #e9ecef;
                transform: translateX(8px);
            }
            .article-title {
                font-weight: 600;
                color: #1e3c72;
                margin-bottom: 10px;
                font-size: 1.1em;
            }
            .article-title a {
                color: #1e3c72;
                text-decoration: none;
            }
            .article-title a:hover {
                color: #2a5298;
                text-decoration: underline;
            }
            .article-meta {
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
                font-size: 0.9em;
            }
            .article-source {
                color: #2a5298;
                font-weight: 700;
            }
            .source-badge {
                background: #e3f2fd;
                color: #1565c0;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 0.85em;
                font-weight: 600;
            }
            .link-icon {
                color: #2a5298;
                font-size: 0.85em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <button class="refresh-btn" onclick="window.location.href='/start-scrape'">🔄 Ny scraping</button>
                <h1>🔍 The Laundry News</h1>
                <p style="opacity: 0.9; font-size: 1.1em;">Auto-scrapade artiklar med källänkar</p>
            </header>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">""" + str(len(articles)) + """</div>
                    <div class="stat-label">📰 Totalt artiklar</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">""" + str(len(set(a['source'] for a in articles))) + """</div>
                    <div class="stat-label">🌐 Unika källor</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">""" + str(len([a for a in articles if a.get('url')])) + """</div>
                    <div class="stat-label">🔗 Med länkar</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">""" + str(len([a for a in articles if a.get('severity') == 'high'])) + """</div>
                    <div class="stat-label">🔴 Högrisk</div>
                </div>
            </div>
            
            <div class="content">
                <h2 style="color: #1e3c72; margin-bottom: 20px;">Artiklar</h2>
    """
    
    type_emoji = {'official': '🏛️', 'news': '📰', 'report': '📋', 'unknown': '❓'}
    type_name = {'official': 'Officiellt', 'news': 'Nyhet', 'report': 'Rapport', 'unknown': 'Okänd'}
    
    for a in articles[:100]:
        title_html = a['title']
        if a.get('url'):
            title_html = f'<a href="{a["url"]}" target="_blank">{a["title"]} ↗</a>'
        
        st = a.get('source_type', 'unknown')
        
        html += f"""
                <div class="article">
                    <div class="article-title">{title_html}</div>
                    <div class="article-meta">
                        <span class="article-source">{a['source']}</span>
                        <span>{a['date']}</span>
                        <span class="source-badge">{type_emoji[st]} {type_name[st]}</span>
        """
        
        if a.get('url'):
            html += f'<span class="link-icon">🔗 Originallänk</span>'
        
        html += """
                    </div>
                </div>
        """
    
    html += """
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/start-scrape')
def start_scrape():
    """Starta en ny scraping manuellt"""
    global scrape_status
    
    if scrape_status["is_scraping"]:
        return "<h1>⏳ Scraping pågår redan! <a href='/'>Tillbaka</a></h1>"
    
    # Starta scraping i bakgrunden
    thread = threading.Thread(target=scrape_laundry_news, daemon=True)
    thread.start()
    
    # Redirecta till huvudsidan som visar status
    return """
    <html>
    <head>
        <meta http-equiv="refresh" content="2;url=/">
    </head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>✅ Scraping startad!</h1>
        <p>Redirectar om 2 sekunder...</p>
    </body>
    </html>
    """

@app.route('/api/articles')
def api_articles():
    return jsonify(articles_cache)

@app.route('/api/status')
def api_status():
    return jsonify(scrape_status)

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok', 
        'articles': len(articles_cache),
        'scraping': scrape_status['is_scraping']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
