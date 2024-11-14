# Prospectus Splitter for E-IPO Stock in IDX (Bursa EFek Indonesia)
### Splitter prospektus untuk ekstraksi prospektus saham yang akan IPO di E-IPO

`prospectus-splitter.py` bertujuan untuk memisahkan halaman tertentu dari file PDF prospektus berdasarkan kata kunci yang telah ditentukan. Skrip ini memungkinkan ekstraksi bagian-bagian penting, seperti laporan keuangan, laporan arus kas, dan laporan laba rugi, dari prospektus dengan berbagai struktur halaman.

## Fitur

- **Keyword-based Extraction**: Menentukan halaman yang mengandung informasi penting menggunakan keyword dan anti-keyword yang sudah ditentukan.
- **PDF Splitter**: Memisahkan file PDF asli menjadi beberapa bagian sesuai dengan jenis bagian yang ingin displit.
- **JSON Updater**: Menghasilkan dan mengupdate file JSON untuk setiap prospektus yang diproses, untuk melakukan koreksi secara manual.
- **Multiprocessing**: Memanfaatkan semua core CPU yang tersedia untuk mempercepat pemrosesan.

## Direktori

- **Input**: File PDF yang akan diproses harus ditempatkan dalam folder `input`.
- **Output**: File PDF hasil ekstraksi dan file JSON terkait akan disimpan dalam folder `output`.

## Requirements

Pastikan untuk menginstal library berikut:
- `PyMuPDF` (fitz) untuk pemrosesan teks dalam PDF.
- `PyPDF2` untuk manipulasi halaman PDF.
  
Instalasi library dapat dilakukan dengan:
```bash
pip install pymupdf PyPDF2
