import logging
import yfinance as yf
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configurazione Log
logging.basicConfig(level=logging.INFO)

# Configurazione Mercati e Titoli
MARKETS = {
    "🇺🇸 INDICI USA": {"S&P 500": "^GSPC", "Dow Jones": "^DJI", "Nasdaq 100": "^NDX"},
    "🇪🇺 INDICI EUROPA": {"Stoxx 600": "^STOXX", "FTSE MIB": "FTSEMIB.MI", "DAX": "^GDAXI", "CAC 40": "^FCHI", "FTSE 100": "^FTSE", "IBEX 35": "^IBEX"},
    "🌏 ASIA": {"Nikkei 225": "^N225", "Shanghai": "000001.SS", "KOSPI": "^KS11"},
    "🛢️ COMMODITIES": {"Petrolio WTI": "CL=F", "Gas Naturale": "NG=F"},
    "🇺🇸 AZIONI USA": {
        "NVIDIA": "NVDA", "AMD": "AMD", "Apple": "AAPL", 
        "Microsoft": "MSFT", "Meta": "META", "Alphabet": "GOOG",
        "Netflix": "NFLX", "Intel": "INTC", "Enphase": "ENPH", "DexCom": "DXCM"
    },
    "🇮🇹 AZIONI EU": {
        "UniCredit": "UCG.MI", "Intesa SP": "ISP.MI", "MPS": "BMPS.MI", "Fineco": "FBK.MI", "Nexi": "NEXI.MI",
        "Enel": "ENEL.MI", "Eni": "ENI.MI", "A2A": "A2A.MI", 
        "Leonardo": "LDO.MI", "STMicro": "STMMI.MI", "Cy4gate": "CY4.MI",
        "Stellantis": "STLAM.MI", "Ferrari": "RACE.MI", "Volkswagen": "VOW3.DE",
        "OVS": "OVS.MI"
    }
}

def fetch_performance():
    text = "📊 <b>VARIAZIONI MERCATI & TITOLI</b>\n"
    text += f"🕒 <i>Aggiornamento: {datetime.now(pytz.timezone('Europe/Rome')).strftime('%H:%M')}</i>\n"
    text += "────────────────────\n\n"
    for category, tickers in MARKETS.items():
        text += f"<b>{category}</b>\n"
        for name, symbol in tickers.items():
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period="2d")
                if len(hist) >= 2:
                    change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                    status = "🟢" if change >= 0 else "🔴"
                    sign = "+" if change >= 0 else ""
                    text += f"{status} <code>{name:<12}</code> <b>{sign}{change:.2f}%</b>\n"
            except:
                pass # Salta errori silenziosamente per non sporcare il report
        text += "\n"
    return text + "────────────────────"

# Funzione per l'invio (usata sia da comando che da job)
async def send_report(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    report = fetch_performance()
    await context.bot.send_message(chat_id=chat_id, text=report, parse_mode='HTML')

# Handler comando manuale
async def manual_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_report(context, update.effective_chat.id)

# Funzione richiamata dal timer ogni ora
async def auto_report_job(context: ContextTypes.DEFAULT_TYPE):
    tz = pytz.timezone('Europe/Rome')
    now = datetime.now(tz)
    
    # Controllo finestra temporale: dalle 10 alle 22 incluse
    if 10 <= now.hour <= 22:
        await send_report(context, context.job.chat_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Pulizia job esistenti per evitare messaggi multipli
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()

    # Programma: ogni 3600 secondi (1 ora)
    context.job_queue.run_repeating(
        auto_report_job, 
        interval=3600, 
        first=5, 
        chat_id=chat_id, 
        name=str(chat_id)
    )
    
    await update.message.reply_text(
        "✅ <b>Bot configurato!</b>\n\n"
        "• Riceverai aggiornamenti ogni ora dalle 10:00 alle 22:00.\n"
        "• Usa /quotazioni per un report istantaneo.",
        parse_mode='HTML'
    )

if __name__ == '__main__':
    try:
        with open("token.txt", "r") as f:
            token = f.read().strip()
    except FileNotFoundError:
        print("Errore: Crea un file token.txt con il tuo API Token.")
        exit()
    
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quotazioni", manual_report))
    
    print("Bot avviato. In attesa di comandi...")
    app.run_polling()
