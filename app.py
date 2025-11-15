python
from flask import Flask, render_template, jsonify, request, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import json
import csv
import re
from collections import Counter
import os

# Skapa Flask-app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///laundry_news.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)

# Skapa databas
db = SQLAlchemy(app)

# Databasmodell för artiklar
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(200), nullable=False)
    title = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    url = db.Column(db.String(500))
    modus = db.Column(db.String(100))
    topic = db.Column(db.String(50))
    technique = db.Column(db.String(100))
    target = db.Column(db.String(100))
    severity = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'source': self.source,
            'title': self.title,
            'date': self.date,
            'url': self.url,
            'modus': self.modus,
            'topic': self.topic,
            'technique': self.technique,
            'target': self.target,
            'severity': self.severity
        }

# Huvudsida
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="sv">
    <head>
        <meta charset="UTF-8">
        <title>The Laundry News - Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                text-align: center;
                background: rgba(255,255,255,0.1);
                padding: 50px;
                border-radius: 20px;
            }
            h1 { font-size: 3em; margin-bottom: 20px; }
            p { font-size: 1.2em; opacity: 0.9; }
            .status {
                margin-top: 30px;
                padding: 15px;
                background: rgba(255,255,255,0.2);
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 The Laundry News</h1>
            <p>Dashboard är installerat och körs!</p>
            <div class="status">
                <strong>Status:</strong> ✅ Online<br>
                <strong>Tid:</strong> ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''
            </div>
        </div>
    </body>
    </html>
    '''

# API endpoint för hälsokontroll
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})

# API endpoint för artiklar
@app.route('/api/articles')
def get_articles():
    articles = Article.query.all()
    return jsonify([a.to_dict() for a in articles])

# Kör applikationen
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=port)

```
