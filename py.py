import requests
import pandas as pd
from datetime import datetime
import time

root = "https://ensembledata.com/apis"
endpoint = "/threads/keyword/search"

# ==================== PENGATURAN ====================
KEYWORD = "Ijazah Palsu"       # Kata kunci yang dicari
MAX_POSTS = 100                # Target jumlah postingan maksimal (bisa diubah: 50, 100, 200, dst.)
API_TOKEN = "F9wTFADF0u4Zp0ka"   # Token EnsembleData Anda
# ====================================================

rows = []
seen_post_ids = set()

# Threads memiliki 2 kategori sorting:
# 0 = Top (paling populer / relevan)
# 1 = Recent (paling baru secara kronologis)
sorting_modes = [
    {"code": 0, "label": "Top / Terpopuler"},
    {"code": 1, "label": "Recent / Terbaru"}
]

print(f"[*] Memulai pengumpulan data Threads untuk: '{KEYWORD}'")
print(f"[*] Target maksimal: {MAX_POSTS} postingan unik\n")

for mode in sorting_modes:
    if len(rows) >= MAX_POSTS:
        break

    print(f"[>] Mengambil kategori: {mode['label']} (sorting={mode['code']})...")
    cursor = None
    page = 1

    while len(rows) < MAX_POSTS:
        params = {
            "name": KEYWORD,
            "sorting": mode["code"],
            "token": API_TOKEN
        }
        if cursor:
            params["cursor"] = cursor

        try:
            res = requests.get(root + endpoint, params=params, timeout=20)
        except Exception as e:
            print(f"[!] Gagal menghubungi API: {e}")
            break

        if res.status_code != 200:
            print(f"[!] Request gagal (status {res.status_code}): {res.text}")
            break

        json_data = res.json()
        items = json_data.get("data", [])

        # Deteksi pagination cursor jika tersedia dari respons API
        next_cursor = (
            json_data.get("next_cursor")
            or json_data.get("cursor")
            or json_data.get("nextCursor")
        )
        if not next_cursor and isinstance(json_data.get("data"), dict):
            next_cursor = json_data["data"].get("next_cursor") or json_data["data"].get("cursor")

        if not items:
            print(f"    - Halaman {page}: Tidak ada data.")
            break

        new_items_count = 0

        for item in items:
            # Struktur hierarki EnsembleData: item -> node -> thread -> thread_items
            thread = item.get("node", {}).get("thread", {}) if isinstance(item, dict) else {}
            thread_items = thread.get("thread_items", [])
            
            # Fallback jika struktur langsung berisi thread_items atau post
            if not thread_items and isinstance(item, dict):
                if "thread_items" in item:
                    thread_items = item["thread_items"]
                elif "post" in item:
                    thread_items = [item]

            for ti in thread_items:
                post = ti.get("post", {})
                user = ti.get("user") or post.get("user", {})
                post_id = str(post.get("pk") or post.get("id") or "")
                code = post.get("code", "")

                # Hindari duplikasi postingan
                identifier = post_id if post_id else code
                if identifier and identifier in seen_post_ids:
                    continue
                if identifier:
                    seen_post_ids.add(identifier)

                # Ekstrak teks caption
                caption_obj = post.get("caption")
                caption_text = ""
                if isinstance(caption_obj, dict):
                    caption_text = caption_obj.get("text", "")
                elif isinstance(caption_obj, str):
                    caption_text = caption_obj

                # Format waktu
                taken_at = post.get("taken_at")
                created_at_str = ""
                if taken_at:
                    try:
                        created_at_str = datetime.fromtimestamp(taken_at).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        created_at_str = str(taken_at)

                username = user.get("username", "")
                post_url = f"https://www.threads.net/@{username}/post/{code}" if (username and code) else ""

                rows.append({
                    "keyword": KEYWORD,
                    "search_category": mode["label"],
                    "post_id": post_id,
                    "post_code": code,
                    "post_url": post_url,
                    "username": username,
                    "user_full_name": user.get("full_name", ""),
                    "is_verified": user.get("is_verified", False),
                    "created_at": created_at_str,
                    "caption": caption_text,
                    "like_count": post.get("like_count", 0),
                    "reply_count": post.get("reply_count", 0),
                    "repost_count": post.get("repost_count", 0),
                    "quote_count": post.get("quote_count", 0),
                })
                new_items_count += 1

                if len(rows) >= MAX_POSTS:
                    break

        print(f"    - Halaman {page}: Mendapatkan {new_items_count} post unik baru (Total terkumpul: {len(rows)})")

        # Jika tidak ada cursor berikutnya atau tidak ada post baru yang didapat, selesai untuk sorting ini
        if not next_cursor or next_cursor == cursor or new_items_count == 0:
            print(f"    - Selesai kategori {mode['label']}.")
            break

        cursor = next_cursor
        page += 1
        time.sleep(1)

# Simpan ke DataFrame
df = pd.DataFrame(rows)

keyword_clean = KEYWORD.replace(" ", "_").lower()
output_filename = f"threads_{keyword_clean}.csv"
df.to_csv(output_filename, index=False, encoding="utf-8-sig")

print(f"\n[✓] Selesai! Berhasil mengumpulkan total {len(df)} postingan unik.")
print(f"[✓] File tersimpan sebagai: {output_filename}\n")

print("--- Pratinjau 5 Data Pertama ---")
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
if not df.empty:
    print(df[["username", "created_at", "like_count", "reply_count", "caption"]].head())
else:
    print("[!] Data kosong atau tidak ada postingan yang cocok.")



