"""
Threads Scraper Script
Menggunakan Playwright & Pandas untuk mengekstrak postingan dari profil Threads (threads.net)
"""

import time
import re
import pandas as pd
from playwright.sync_api import sync_playwright

def scrape_threads_profile(username: str, max_posts: int = 30, headless: bool = False):
    clean_username = username.lstrip("@").strip()
    profile_url = f"https://www.threads.net/@{clean_username}"
    
    print(f"[*] Memulai scraping untuk profil: @{clean_username}")
    print(f"[*] Target URL: {profile_url}")
    print(f"[*] Target jumlah postingan: {max_posts}")

    scraped_data = []
    seen_post_urls = set()

    with sync_playwright() as p:
        # Buka browser Chromium dengan User-Agent modern agar tidak diblokir
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, seperti Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="id-ID"
        )
        page = context.new_page()

        print("[*] Membuka halaman...")
        page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
        
        # Beri jeda agar konten awal termuat
        time.sleep(3)

        # Scroll bertahap untuk memuat postingan
        no_new_posts_count = 0
        max_scroll_attempts = 30
        scroll_attempt = 0

        while len(scraped_data) < max_posts and scroll_attempt < max_scroll_attempts:
            scroll_attempt += 1

            # Cari link postingan yang polanya: /@username/post/POST_ID
            post_links = page.query_selector_all(f'a[href*="/post/"]')

            initial_count = len(scraped_data)

            for link in post_links:
                href = link.get_attribute("href")
                if not href:
                    continue

                # Normalisasi URL postingan
                if href.startswith("/"):
                    full_post_url = f"https://www.threads.net{href}"
                else:
                    full_post_url = href

                # Pastikan URL valid untuk postingan dan belum pernah diambil
                if "/post/" in full_post_url and full_post_url not in seen_post_urls:
                    seen_post_urls.add(full_post_url)

                    # Cari container postingan terdekat (naik ke parent element)
                    try:
                        # Dapatkan elemen card / container postingan
                        post_card = link.evaluate_handle(
                            """el => {
                                let curr = el;
                                for (let i = 0; i < 10; i++) {
                                    if (!curr.parentElement) break;
                                    curr = curr.parentElement;
                                    // Cari elemen yang membungkus seluruh thread/post
                                    if (curr.querySelectorAll('time').length > 0 && curr.querySelectorAll('div[dir="auto"]').length > 0) {
                                        return curr;
                                    }
                                }
                                return el.closest('div[data-pressable-container="true"]') || el.parentElement.parentElement.parentElement;
                            }"""
                        )
                        card_element = post_card.as_element()

                        # Ambil teks postingan (elemen dengan dir="auto")
                        post_text = ""
                        timestamp = ""

                        if card_element:
                            text_elements = card_element.query_selector_all('div[dir="auto"]')
                            text_pieces = []
                            for te in text_elements:
                                t = te.inner_text().strip()
                                # Abaikan teks nama pengguna atau tombol aksi pendek
                                if t and t.lower() != clean_username.lower() and not re.match(r'^(balas|suka|repost|bagikan|\d+)$', t, re.IGNORECASE):
                                    text_pieces.append(t)
                            post_text = " \n".join(text_pieces) if text_pieces else ""

                            # Ambil timestamp jika ada
                            time_elem = card_element.query_selector('time')
                            if time_elem:
                                timestamp = time_elem.get_attribute('datetime') or time_elem.inner_text()
                    except Exception as e:
                        post_text = ""
                        timestamp = ""

                    scraped_data.append({
                        "username": clean_username,
                        "post_url": full_post_url,
                        "post_text": post_text,
                        "timestamp": timestamp,
                    })

                    print(f"[{len(scraped_data)}/{max_posts}] Berhasil ambil post: {full_post_url}")

                    if len(scraped_data) >= max_posts:
                        break

            # Cek apakah ada data baru setelah scroll
            if len(scraped_data) == initial_count:
                no_new_posts_count += 1
            else:
                no_new_posts_count = 0

            # Jika 5 kali scroll berturut-turut tidak ada post baru, kemungkinan sudah mencapai ujung feed
            if no_new_posts_count >= 5:
                print("[!] Tidak ada postingan baru lagi yang dimuat. Berhenti.")
                break

            # Scroll ke bawah secara halus
            page.evaluate("window.scrollBy(0, 1000);")
            time.sleep(2)

        browser.close()

    print(f"\n[✓] Selesai! Berhasil mengumpulkan {len(scraped_data)} postingan.")

    # Simpan ke DataFrame dan file CSV / JSON
    if scraped_data:
        df = pd.DataFrame(scraped_data)
        
        csv_filename = f"threads_{clean_username}.csv"
        json_filename = f"threads_{clean_username}.json"

        df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
        df.to_json(json_filename, orient="records", force_ascii=False, indent=2)

        print(f"[✓] Data tersimpan di: {csv_filename}")
        print(f"[✓] Data tersimpan di: {json_filename}")
        return df
    else:
        print("[!] Tidak ada data yang berhasil diambil.")
        return None


if __name__ == "__main__":
    # --- PENGATURAN TARGET ---
    TARGET_USERNAME = "sepeda"    # Ganti dengan username Threads yang ingin di-scrape (contoh: 'zuck', 'kemdikbud.ri', dll.)
    JUMLAH_POSTINGAN = 120       # Jumlah maksimal post yang ingin diambil
    MODE_HEADLESS = False       # False: Jendela browser terlihat | True: Berjalan di background

    df = scrape_threads_profile(
        username=TARGET_USERNAME,
        max_posts=JUMLAH_POSTINGAN,
        headless=MODE_HEADLESS
    )
    
    if df is not None:
        print("\nPratinjau Data:")
        print(df[["username", "post_url", "timestamp"]].head())
