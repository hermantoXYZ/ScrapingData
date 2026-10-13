
# CELL 1 — IMPORT LIBRARY

import re
import os
import json
import warnings
import zipfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from IPython.display import display
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF

warnings.filterwarnings("ignore")

pd.set_option("display.max_columns", 100)
pd.set_option("display.max_colwidth", 180)

# URL CSV dari GitHub
DATA_URL = (
    "https://raw.githubusercontent.com/"
    "hermantoXYZ/ScrapingData/main/threads_ijazah_palsu.csv"
)

df_raw = pd.read_csv(DATA_URL, encoding="utf-8-sig", sep=None, engine="python")

print("Data berhasil dibaca.")
print("Jumlah baris:", len(df_raw))
print("Jumlah kolom:", len(df_raw.columns))
display(df_raw.head())


# CELL 2 — DATA AUDIT

print("Nama kolom:")
print(df_raw.columns.tolist())

print("\nTipe data:")
display(df_raw.dtypes.to_frame("data_type"))

audit = pd.DataFrame({
    "tipe_data": df_raw.dtypes.astype(str),
    "jumlah_kosong": df_raw.isna().sum(),
    "persen_kosong": (
        df_raw.isna().mean().mul(100).round(2)
    ),
    "jumlah_unik": df_raw.nunique(dropna=True)
})

display(audit)

print("Jumlah baris duplikat penuh:",
      df_raw.duplicated().sum())

print("\nContoh isi setiap kolom:")
for col in df_raw.columns:
    print(f"\n--- {col} ---")
    print(df_raw[col].dropna().astype(str).head(3).tolist())


def detect_column(columns, candidates):
    lookup = {str(c).lower().strip(): c for c in columns}

    # Pencocokan nama persis
    for name in candidates:
        if name in lookup:
            return lookup[name]

    # Pencocokan nama yang mengandung kata kunci
    for c in columns:
        cl = str(c).lower().strip()
        if any(name in cl for name in candidates):
            return c

    return None


TEXT_COL = detect_column(
    df_raw.columns,
    ["text", "content", "caption", "post_text",
     "full_text", "message", "body", "thread_text"]
)

DATE_COL = detect_column(
    df_raw.columns,
    ["created_at", "datetime", "timestamp",
     "posted_at", "date", "time", "tanggal"]
)

ID_COL = detect_column(
    df_raw.columns,
    ["post_id", "thread_id", "tweet_id", "id"]
)

print("Kolom teks:", TEXT_COL)
print("Kolom tanggal:", DATE_COL)
print("Kolom ID:", ID_COL)

# Jika hasil deteksi keliru, tetapkan secara manual, contoh:
# TEXT_COL = "text"
# DATE_COL = "created_at"
# ID_COL = "id"

if TEXT_COL is None:
    raise ValueError(
        "Kolom teks belum terdeteksi. "
        "Lihat daftar kolom pada CELL 2, lalu isi TEXT_COL secara manual."
    )

if DATE_COL is None:
    print(
        "PERHATIAN: kolom tanggal tidak terdeteksi. "
        "Analisis tren waktu akan dilewati."
    )


# CELL 4 — CLEANING DATA

df = df_raw.copy()

# Rapikan nama kolom
df.columns = df.columns.astype(str).str.strip()

# Buang baris yang seluruh kolomnya kosong
df = df.dropna(how="all").copy()

# Pastikan teks berbentuk string
df[TEXT_COL] = df[TEXT_COL].fillna("").astype(str).str.strip()

# Hapus teks kosong
df = df[df[TEXT_COL].ne("")].copy()

n_before_dedup = len(df)

# Hapus duplikasi berdasarkan ID jika tersedia
if ID_COL is not None:
    df = df.drop_duplicates(subset=[ID_COL], keep="first")

# Hapus duplikasi teks untuk mengurangi pengulangan unggahan
df = df.drop_duplicates(subset=[TEXT_COL], keep="first").copy()

print("Baris sebelum deduplikasi:", n_before_dedup)
print("Baris setelah cleaning:", len(df))
print("Baris yang terhapus:", n_before_dedup - len(df))

print("\nContoh data setelah cleaning:")
display(df.head())

print("\nKualitas data setelah cleaning:")
display(pd.DataFrame({
    "jumlah_kosong": df.isna().sum(),
    "persen_kosong": (df.isna().mean() * 100).round(2)
}))


# CELL 5 — TEXT PREPROCESSING

def clean_text(text):
    text = str(text).lower()

    # Hapus URL
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # Hapus mention
    text = re.sub(r"@\w+", " ", text)

    # Hapus tag HTML
    text = re.sub(r"<[^>]+>", " ", text)

    # Pertahankan huruf, angka, dan spasi
    # Angka dipertahankan agar informasi penting tidak hilang
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)

    # Rapikan spasi
    text = re.sub(r"\s+", " ", text).strip()

    return text


df["text_original"] = df[TEXT_COL].astype(str)
df["text_clean"] = df["text_original"].apply(clean_text)

# Hapus teks yang menjadi kosong setelah pembersihan
df = df[df["text_clean"].str.strip().ne("")].copy()

# Hitung panjang teks
df["word_count"] = df["text_clean"].str.split().str.len()
df["char_count"] = df["text_clean"].str.len()

display(df[["text_original", "text_clean",
            "word_count", "char_count"]].head(10))

print("Rata-rata jumlah kata:",
      round(df["word_count"].mean(), 2))


# CELL 6 — DESCRIPTIVE ANALYSIS

print("Jumlah observasi:", len(df))
print("Rata-rata kata per unggahan:",
      round(df["word_count"].mean(), 2))
print("Median kata per unggahan:",
      df["word_count"].median())
print("Total kata:",
      int(df["word_count"].sum()))

display(df["word_count"].describe().to_frame("word_count"))

# Distribusi panjang teks
plt.figure(figsize=(9, 5))
sns.histplot(df["word_count"], bins=30)
plt.title("Distribusi Panjang Unggahan")
plt.xlabel("Jumlah kata")
plt.ylabel("Frekuensi")
plt.tight_layout()
plt.show()

# Frekuensi kata
stopwords_id = set("""
yang dan di ke dari ini itu untuk dengan pada adalah atau juga
tidak bukan belum sudah akan dalam karena kalau jika maka saja
saya aku kami kita kamu anda dia mereka nya nya ya si nih deh
kok pun lah the a an of to is are was were be have has do does
""".split())

all_words = []

for text in df["text_clean"]:
    words = [
        w for w in text.split()
        if len(w) > 2 and w not in stopwords_id
    ]
    all_words.extend(words)

word_freq = pd.DataFrame(
    Counter(all_words).most_common(30),
    columns=["kata", "frekuensi"]
)

display(word_freq)

if not word_freq.empty:
    plt.figure(figsize=(10, 8))
    plot_data = word_freq.sort_values("frekuensi")
    plt.barh(plot_data["kata"], plot_data["frekuensi"])
    plt.title("30 Kata Paling Sering Muncul")
    plt.xlabel("Frekuensi")
    plt.tight_layout()
    plt.show()



# CELL 8 — VISUALISASI SENTIMEN

sentiment_counts = (
    df["sentiment"].value_counts()
    .reindex(["positif", "netral", "negatif"], fill_value=0)
)

display(sentiment_counts.to_frame("jumlah"))

plt.figure(figsize=(8, 5))
plt.bar(sentiment_counts.index, sentiment_counts.values)
plt.title("Distribusi Sentimen Unggahan")
plt.xlabel("Sentimen")
plt.ylabel("Jumlah unggahan")
plt.tight_layout()
plt.show()

sentiment_percent = (
    sentiment_counts / sentiment_counts.sum() * 100
).round(2)

display(sentiment_percent.to_frame("persentase"))


# CELL 9 — TOPIC MODELING

texts_for_topics = df["text_clean"].fillna("").astype(str)

# Buat representasi TF-IDF
vectorizer = TfidfVectorizer(
    max_features=3000,
    min_df=2,
    max_df=0.90,
    ngram_range=(1, 2),
    stop_words=list(stopwords_id)
)

try:
    X = vectorizer.fit_transform(texts_for_topics)
except ValueError as e:
    raise ValueError(
        "Kosakata tidak cukup untuk topic modeling. "
        "Periksa jumlah data dan parameter min_df/max_df."
    ) from e

N_TOPICS = min(5, X.shape[0] - 1, X.shape[1] - 1)

if N_TOPICS < 2:
    raise ValueError(
        "Data terlalu sedikit untuk topic modeling. "
        "Diperlukan lebih banyak teks yang beragam."
    )

nmf = NMF(
    n_components=N_TOPICS,
    random_state=42,
    init="nndsvda",
    max_iter=400
)

W = nmf.fit_transform(X)
H = nmf.components_
feature_names = vectorizer.get_feature_names_out()

topic_rows = []

for topic_idx, topic in enumerate(H):
    top_indices = topic.argsort()[-10:][::-1]
    top_words = [feature_names[i] for i in top_indices]

    topic_rows.append({
        "topic_id": topic_idx,
        "kata_kunci": ", ".join(top_words)
    })

topics_df = pd.DataFrame(topic_rows)
display(topics_df)

# Tetapkan topik dominan untuk setiap unggahan
df["topic_id"] = W.argmax(axis=1)
df["topic_strength"] = W.max(axis=1)

topic_distribution = (
    df["topic_id"].value_counts()
    .sort_index()
    .rename_axis("topic_id")
    .reset_index(name="jumlah_unggahan")
)

topic_distribution = topic_distribution.merge(
    topics_df, on="topic_id", how="left"
)

display(topic_distribution)


# CELL 10 — TEMPORAL ANALYSIS

if DATE_COL is not None:
    df["date_parsed"] = pd.to_datetime(
        df[DATE_COL],
        errors="coerce",
        utc=True
    )

    dated_df = df.dropna(subset=["date_parsed"]).copy()

    if not dated_df.empty:
        dated_df["date"] = (
            dated_df["date_parsed"].dt.floor("D")
        )

        daily_volume = (
            dated_df.groupby("date")
            .size()
            .rename("jumlah_unggahan")
            .reset_index()
        )

        display(daily_volume.head())

        plt.figure(figsize=(12, 5))
        plt.plot(
            daily_volume["date"],
            daily_volume["jumlah_unggahan"]
        )
        plt.title("Volume Unggahan per Hari")
        plt.xlabel("Tanggal")
        plt.ylabel("Jumlah unggahan")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

        daily_sentiment = (
            dated_df.groupby(["date", "sentiment"])
            .size()
            .unstack(fill_value=0)
        )

        daily_sentiment.plot(
            figsize=(12, 5),
            marker="o"
        )
        plt.title("Perubahan Sentimen per Hari")
        plt.xlabel("Tanggal")
        plt.ylabel("Jumlah unggahan")
        plt.tight_layout()
        plt.show()

    else:
        print("Kolom tanggal ada, tetapi tidak ada tanggal valid.")
else:
    print("Analisis tren waktu dilewati karena kolom tanggal tidak tersedia.")


# CELL 11 — CROSS-TABULATION

cross_tab = pd.crosstab(
    df["topic_id"],
    df["sentiment"],
    margins=True
)

display(cross_tab)

# Proporsi sentimen di dalam setiap topik
topic_sentiment_pct = pd.crosstab(
    df["topic_id"],
    df["sentiment"],
    normalize="index"
).mul(100).round(2)

display(topic_sentiment_pct)

plt.figure(figsize=(9, 5))
sns.heatmap(
    topic_sentiment_pct,
    annot=True,
    fmt=".1f",
    cmap="Blues"
)
plt.title("Proporsi Sentimen Berdasarkan Topik (%)")
plt.xlabel("Sentimen")
plt.ylabel("ID topik")
plt.tight_layout()
plt.show()



# CELL 13 — EXPORT HASIL

OUTPUT_DIR = "/content/hasil_analisis_ijazah"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Simpan data mentah dan hasil olahan
df_raw.to_csv(
    f"{OUTPUT_DIR}/data_mentah.csv",
    index=False,
    encoding="utf-8-sig"
)

df.to_csv(
    f"{OUTPUT_DIR}/data_bersih_dan_analisis.csv",
    index=False,
    encoding="utf-8-sig"
)

topics_df.to_csv(
    f"{OUTPUT_DIR}/hasil_topic_modeling.csv",
    index=False,
    encoding="utf-8-sig"
)

word_freq.to_csv(
    f"{OUTPUT_DIR}/frekuensi_kata.csv",
    index=False,
    encoding="utf-8-sig"
)

cross_tab.to_csv(
    f"{OUTPUT_DIR}/tabulasi_topik_sentimen.csv",
    encoding="utf-8-sig"
)

topic_sentiment_pct.to_csv(
    f"{OUTPUT_DIR}/proporsi_sentimen_per_topik.csv",
    encoding="utf-8-sig"
)

# Statistik ringkas
summary = {
    "jumlah_data_mentah": int(len(df_raw)),
    "jumlah_data_akhir": int(len(df)),
    "jumlah_topik": int(N_TOPICS),
    "distribusi_sentimen": {
        str(k): int(v)
        for k, v in df["sentiment"].value_counts().items()
    },
    "kolom_teks": str(TEXT_COL),
    "kolom_tanggal": str(DATE_COL)
}

with open(
    f"{OUTPUT_DIR}/ringkasan_analisis.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

# Simpan grafik
for i, fig_num in enumerate(plt.get_fignums(), start=1):
    fig = plt.figure(fig_num)
    fig.savefig(
        f"{OUTPUT_DIR}/grafik_{i}.png",
        dpi=200,
        bbox_inches="tight"
    )

# Kompres semua hasil
zip_path = "/content/hasil_analisis_ijazah.zip"

with zipfile.ZipFile(
    zip_path, "w", zipfile.ZIP_DEFLATED
) as zf:
    for filename in os.listdir(OUTPUT_DIR):
        full_path = os.path.join(OUTPUT_DIR, filename)
        zf.write(full_path, arcname=filename)

print("Analisis selesai.")
print("File hasil:", zip_path)

