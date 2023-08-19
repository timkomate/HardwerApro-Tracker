import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import sqlite3
import re

# Connect to the SQLite database
conn = sqlite3.connect('scraped_data.db')
cursor = conn.cursor()

# Create a table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        uad_id INTEGER,
        url TEXT NOT NULL UNIQUE,
        title TEXT,
        price INTEGER,
        timestamp DATE
    )
''')
conn.commit()

def convert_price(price_str):
    numeric_part = re.sub('\D', '', price_str)  # Remove non-numeric characters
    if numeric_part:
        return int(numeric_part)
    return 0

def scrape_and_notify():
    base_url = "https://hardverapro.hu/aprok/keres.php?stext=raspberry+pi&stcid_text=&stcid=&stmid_text=&stmid=&minprice=&maxprice=&cmpid_text=&cmpid=&usrid_text=&usrid=&buying=0&stext_none=&search_title=1&noiced=1"

    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    for i, item2 in enumerate(soup.find_all("li", class_="media")):
        uad_id = item2.get("data-uadid")
        price = item2.find("div", class_="uad-price").string
        url = item2.find("div", class_="uad-title").h1.a["href"]
        title = item2.find("div", class_="uad-title").h1.a.string
        timestamp = datetime.now()
        
        numeric_price = convert_price(price)

        cursor.execute('SELECT * FROM items WHERE uad_id = ?', (uad_id,))
        existing_item = cursor.fetchone()

        if not existing_item:
            cursor.execute('INSERT INTO items (uad_id, url, title, price, timestamp) VALUES (?, ?, ?, ?, ?)', (uad_id, url, title, numeric_price, timestamp))
            conn.commit()

            print(f"New Item Found - ID: {uad_id}, Price: {numeric_price}, URL: {url}, Title: {title}")

# Run the scraping and notification process every 30 minutes
while True:
    scrape_and_notify()
    print("Waiting for 30 minutes...")
    time.sleep(1800)  # 30 minutes in seconds

# Close the database connection when done
conn.close()
