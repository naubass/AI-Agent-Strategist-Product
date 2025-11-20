import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from langchain_core.messages import HumanMessage

# import agent
from agent import product_agent_graph

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

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
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pesan dengan fitur Safe Send (Anti-Crash)"""
    user_msg = update.message.text
    chat_id = update.effective_chat.id

    # Indikator typing
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    inputs = {
        "messages": [HumanMessage(content=user_msg)],
        "research_data": ""
    }

    try:
        # 1. Proses Agent
        results = await product_agent_graph.ainvoke(inputs)
        response = results["messages"][-1].content

        # 2. Kirim Pesan (Try Markdown first)
        try:
            # Coba kirim dengan Markdown agar rapi (Bold, dll)
            await context.bot.send_message(
                chat_id=chat_id,
                text=response,
                parse_mode='Markdown' 
            )
        except Exception as e:
            print(f"⚠️ Markdown gagal ({e}), mengirim plain text...")
            # Jika gagal (Error Can't parse entities), kirim Plain Text biasa
            await context.bot.send_message(
                chat_id=chat_id,
                text=response
                # parse_mode dihapus agar dikirim apa adanya
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
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🤖 Bot Product Strategist sedang berjalan... Tekan Ctrl+C untuk berhenti.")
    app.run_polling()


