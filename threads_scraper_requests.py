"""
Threads Single Post / Lightweight Scraper (Requests + BeautifulSoup)
Cocok untuk mengambil detail postingan tertentu dari URL post Threads secara cepat tanpa browser.
"""

import requests
from bs4 import BeautifulSoup
import json
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

def scrape_single_post(post_url: str):
    """
    Mengambil data konten dari URL postingan Threads publik.
    Contoh URL: https://www.threads.net/@zuck/post/Cx...
    """
    print(f"[*] Mengambil data dari: {post_url}")
    response = requests.get(post_url, headers=HEADERS, timeout=15)
    
    if response.status_code != 200:
        print(f"[!] Gagal mengakses halaman. Status code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Ekstraksi Open Graph & Meta Tags
    title = soup.find("meta", property="og:title")
    description = soup.find("meta", property="og:description")
    image = soup.find("meta", property="og:image")
    url = soup.find("meta", property="og:url")

    post_data = {
        "url": url["content"] if url else post_url,
        "title": title["content"] if title else "",
        "content": description["content"] if description else "",
        "image_url": image["content"] if image else "",
    }

    return post_data

if __name__ == "__main__":
    # Ganti dengan link postingan Threads yang ingin Anda ambil
    EXAMPLE_POST_URL = "https://www.threads.net/@zuck/post/CveBv2tr6h8"
    
    data = scrape_single_post(EXAMPLE_POST_URL)
    if data:
        print("\n[✓] Hasil Ekstraksi:")
        for k, v in data.items():
            print(f"  {k}: {v}")
