import os
import time
import logging
import feedparser
import google.generativeai as genai
from telegram import Bot
import asyncio

# Pengaturan Catatan Sistem
logging.basicConfig(level=logging.INFO)

# Mengambil Kunci Rahasia dari Pengaturan Server
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SHOPEE_LINK = os.environ.get("SHOPEE_LINK", "https://s.shopee.co.id/default")

# Konfigurasi Google Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Sumber Berita Otomatis (RSS Feed CNN Indonesia)
RSS_URL = "https://www.cnnindonesia.com/nasional/rss"

# Tempat Menyimpan Judul Berita yang Sudah Diposting Agar Tidak Double
berita_terposting = set()

def ambil_url_gambar(berita):
    """Mencari tautan/URL gambar dari entri berita RSS."""
    # 1. Cek dari tag 'media_content' atau 'enclosures'
    if 'media_content' in berita and len(berita.media_content) > 0:
        return berita.media_content[0].get('url')
    if 'enclosures' in berita and len(berita.enclosures) > 0:
        for enc in berita.enclosures:
            if enc.get('type', '').startswith('image/'):
                return enc.get('href')
    # 2. Jika tidak ada, kembalikan None
    return None

async def proses_dan_kirim_berita():
    bot = Bot(token=TELEGRAM_TOKEN)
    feed = feedparser.parse(RSS_URL)
    
    if not feed.entries:
        print("Tidak ada berita ditemukan.")
        return

    # Ambil berita paling terbaru
    berita_terbaru = feed.entries[0]
    judul_berita = berita_terbaru.title
    ringkasan_berita = berita_terbaru.summary

    # Cek apakah berita ini sudah pernah diposting
    if judul_berita in berita_terposting:
        print("Berita ini sudah diposting sebelumnya. Menunggu berita baru...")
        return

    print(f"Memproses berita baru: {judul_berita}")

    # Ambil Gambar dari Berita
    url_gambar = ambil_url_gambar(berita_terbaru)

    # Instruksi untuk Google Gemini AI
    prompt_ai = f"""
    Kamu adalah seorang pembuat konten berita viral yang pandai menarik perhatian pembaca.
    Buatkan postingan berita berdasarkan data berikut:
    Judul: {judul_berita}
    Ringkasan: {ringkasan_berita}

    Aturan Penulisan:
    1. Buat kalimat pembuka (hook) yang bikin penasaran dengan emotikon yang sesuai.
    2. Tuliskan ringkasan berita dalam 2-3 kalimat singkat yang mudah dipahami.
    3. Ajukan pertanyaan di akhir berita untuk mengajak pembaca berdiskusi di kolom komentar.
    4. Jangan sebutkan kata 'artikel' atau 'sumber'.
    """

    # Meminta AI membuatkan kalimat
    response = model.generate_content(prompt_ai)
    teks_berita_ai = response.text

    # Menyusun Teks/Caption Akhir
    pesan_akhir = f"{teks_berita_ai}\n\n" \
                  f"━━━━━━━━━━━━━━━━━━━\n" \
                  f"🛒 **Rekomendasi Promo Hari Ini:**\n" \
                  f"Cek barang murah & diskon Shopee di sini 👉 {SHOPEE_LINK}"

    # Mengirim Pesan ke Saluran Telegram
    if url_gambar:
        # Jika berita memiliki gambar, kirim sebagai Foto + Caption
        print(f"Mengirim berita dengan gambar: {url_gambar}")
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=url_gambar,
            caption=pesan_akhir,
            parse_mode='Markdown'
        )
    else:
        # Jika berita tidak memiliki gambar, kirim Teks biasa
        print("Gambar tidak ditemukan, mengirim teks biasa...")
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=pesan_akhir,
            parse_mode='Markdown'
        )
    
    # Simpan judul berita agar tidak terulang
    berita_terposting.add(judul_berita)
    print("Berita berhasil diposting ke Saluran Telegram!")

async def main():
    print("Bot Berita Otomatis Mulai Berjalan...")
    while True:
        try:
            await proses_dan_kirim_berita()
        except Exception as e:
            print(f"Terjadi kesalahan: {e}")
        
        # Jeda waktu posting (Contoh: 7200 detik = 2 Jam Sekali)
        await asyncio.sleep(7200)

if __name__ == "__main__":
    asyncio.run(main())
