import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import sqlite3
import re
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Load configuration from config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Connect to the SQLite database
logging.info("connecting to database...")
conn = sqlite3.connect("scraped_data.db")
cursor = conn.cursor()

# Create a table if it doesn't exist
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        uad_id INTEGER,
        url TEXT NOT NULL UNIQUE,
        title TEXT,
        price INTEGER,
        timestamp DATE,
        is_alive BOOLEAN
    )
"""
)
conn.commit()


def convert_price(price_str):
    numeric_part = re.sub("\D", "", price_str)  # Remove non-numeric characters
    if numeric_part:
        return int(numeric_part)
    return 0


def scrape_and_notify(search_term):
    base_url = f"https://hardverapro.hu/aprok/keres.php?stext={search_term}&stcid_text=&stcid=&stmid_text=&stmid=&minprice=&maxprice=&cmpid_text=&cmpid=&usrid_text=&usrid=&buying=0&stext_none=&search_title=1&noiced=1"

    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, "html.parser")
    ids = set()
    for i, item in enumerate(soup.find_all("li", class_="media")):
        uad_id = item.get("data-uadid")
        ids.add(int(uad_id))
        price = item.find("div", class_="uad-price").string
        url = item.find("div", class_="uad-title").h1.a["href"]
        title = item.find("div", class_="uad-title").h1.a.string
        timestamp = datetime.now()
        numeric_price = convert_price(price)

        cursor.execute("SELECT * FROM items WHERE uad_id = ?", (uad_id,))
        existing_item = cursor.fetchone()

        if not existing_item:
            cursor.execute(
                "INSERT INTO items (uad_id, url, title, price, timestamp, is_alive) VALUES (?, ?, ?, ?, ?, True)",
                (uad_id, url, title, numeric_price, timestamp),
            )
            conn.commit()

            log_message = f"New Item Found - ID: {uad_id}, Price: {numeric_price}, URL: {url}, Title: {title}"
            logging.info(log_message)
    cursor.execute("SELECT uad_id FROM items WHERE is_alive = True")
    existing_item = cursor.fetchall()
    existing_item = set(item[0] for item in existing_item)
    diff = existing_item.difference(ids)
    for id in diff:
        cursor.execute('UPDATE items SET is_alive = ? WHERE uad_id = ?', (False, id))
        conn.commit()


# Get configuration options
search_term = config["search_term"]
interval_minutes = config["interval_minutes"]

# Run the scraping and notification process with the specified interval
logging.info("start scraping...")
while True:
    scrape_and_notify(search_term)
    log_message = f"Waiting for {interval_minutes} minutes..."
    logging.info(log_message)
    time.sleep(interval_minutes * 60)  # Convert minutes to seconds

# Close the database connection when done
conn.close()
