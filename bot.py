import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from langchain_core.messages import HumanMessage

# import agent & pdf export
from agent import product_agent_graph
from pdf_utils import create_pdf_report
from file_loader import parse_document

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# inisialisasi variabel analisis
user_last_analysis = {}

# start bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler the /start command."""
    first_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"Halo {first_name}! 🚀\n"
        "Saya adalah AI Product Strategist kamu.\n\n"
        "💡 *Cara pakai:*\n"
        "- Tanyakan analisis kompetitor (cth: 'Analisis Gojek vs Grab')\n"
        "- Minta ide fitur (cth: 'Ide fitur AI untuk aplikasi e-commerce')\n"
        "- Atau sekadar sapa saya!"
        "- ketik /export untuk download laporan"
    )

async def export_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /export"""
    chat_id = update.effective_chat.id
    
    # 1. Cek apakah ada data analisis sebelumnya
    analysis_text = user_last_analysis.get(chat_id)
    
    if not analysis_text:
        await update.message.reply_text("⚠️ Belum ada laporan yang dibuat. Silakan minta analisis dulu (misal: 'Analisis Gojek').")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action='upload_document')
    
    try:
        # 2. Generate PDF (Memanggil fungsi dari pdf_utils.py)
        pdf_file = create_pdf_report(analysis_text)
        
        # 3. Kirim File ke Telegram
        await update.message.reply_document(
            document=pdf_file,
            filename="Strategy_Report.pdf",
            caption="📄 Ini laporan lengkap Anda dalam format PDF."
        )
    except Exception as e:
        logging.error(f"PDF Error: {e}")
        await update.message.reply_text("Gagal membuat PDF. Terjadi kesalahan sistem.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani file PDF/Excel yang dikirim user"""
    chat_id = update.effective_chat.id
    document = update.message.document
    
    await update.message.reply_text(
        f"📂 Menerima file: *{document.file_name}*\n⏳ Sedang membaca & menganalisis data...",
        parse_mode='Markdown'
    )
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    try:
        file = await context.bot.get_file(document.file_id)
        file_path = f"temp_{document.file_name}" 
        await file.download_to_drive(file_path)
        
        extracted_text = parse_document(file_path)
        
        # Hapus file setelah dibaca agar hemat storage
        if os.path.exists(file_path):
            os.remove(file_path)
            
        inputs = {
            "messages": [HumanMessage(content=f"Tolong analisis data dari file {document.file_name} ini.")],
            "research_data": "", # Kosongkan riset awal, biarkan dia fokus ke file dulu atau searching nanti
            "file_content": extracted_text
        }
        
        # Invoke Graph
        results = await product_agent_graph.ainvoke(inputs)
        response = results["messages"][-1].content
        
        user_last_analysis[chat_id] = response

        try:
            await context.bot.send_message(chat_id=chat_id, text=response, parse_mode='Markdown')
        except:
            await context.bot.send_message(chat_id=chat_id, text=response)
            
        await context.bot.send_message(chat_id=chat_id, text="💡 Ketik /export untuk simpan ke PDF.")

    except Exception as e:
        logging.error(f"File Error: {e}")
        await update.message.reply_text("❌ Gagal membaca file. Pastikan formatnya PDF, Excel, atau CSV.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pesan dengan fitur Safe Send (Anti-Crash)"""
    user_msg = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🤖 *Pesan dari kamu:* {user_msg}\n\n⏳ _Sedang melakukan riset pasar & menyusun strategi..._",
        parse_mode='Markdown'
    )

    # Indikator typing
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    inputs = {
        "messages": [HumanMessage(content=user_msg)],
        "research_data": "",
        "file_content": ""
    }

    try:
        # 1. Proses Agent
        results = await product_agent_graph.ainvoke(inputs)
        response = results["messages"][-1].content

        user_last_analysis[chat_id] = response
            # Coba kirim dengan Markdown agar rapi (Bold, dll)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=response,
                parse_mode='Markdown' 
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=response
            )

            await context.bot.send_message(
                chat_id=chat_id,
                text="💡 *Tips:* Ketik /export untuk mengunduh hasil ini dalam bentuk PDF.",
                parse_mode='Markdown'
            )

    except Exception as e:
        logging.error(f"Error processing message: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat memproses data.")

# run bot
if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN belum diisi di file .env")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    
    # Daftarkan Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("export", export_pdf_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🤖 Bot Product Strategist sedang berjalan... Tekan Ctrl+C untuk berhenti.")
    app.run_polling()


