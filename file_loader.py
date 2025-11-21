import pandas as pd
from pypdf import PdfReader
import os

def parse_document(file_path: str) -> str:
    """Mendeteksi tipe file dan mengekstrak isinya menjadi teks"""
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.pdf':
            return read_pdf(file_path)
        elif ext in ['.xlsx', '.xls', '.csv']:
            return read_excel(file_path)
        else:
            return "Format file tidak didukung. Gunakan PDF atau Excel."
    except Exception as e:
        return f"Error membaca file: {str(e)}"

def read_pdf(file_path):
    text = ""
    reader = PdfReader(file_path)
    # Batasi halaman agar token tidak jebol (misal max 10 halaman awal)
    max_pages = min(len(reader.pages), 10) 
    
    for i in range(max_pages):
        page = reader.pages[i]
        text += page.extract_text() + "\n"
    return text

def read_excel(file_path):
    # Baca Excel/CSV
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    preview_df = df.head(50) 
    return preview_df.to_markdown(index=False)