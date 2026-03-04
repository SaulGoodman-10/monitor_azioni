import logging
import yfinance as yf
from datetime import time
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 1. Configurazione Mercati e Azioni dalle tue immagini
MARKETS = {
    "🇺🇸 INDICI USA": {"S&P 500": "^GSPC", "Dow Jones": "^DJI", "Nasdaq 100": "^NDX"},
    "🇪🇺 INDICI EUROPA": {"Stoxx 600": "^STOXX", "FTSE MIB": "FTSEMIB.MI", "DAX": "^GDAXI", "CAC 40": "^FCHI", "FTSE 100": "^FTSE", "IBEX 35": "^IBEX"},
    "🌏 ASIA": {"Nikkei 225": "^N225", "Shanghai": "000001.SS", "KOSPI": "^KS11"},
    "🛢️ COMMODITIES": {"Petrolio WTI": "CL=F", "Gas Naturale": "NG=F"},
    
    # --- NUOVE AGGIUNTE DALLE TUE IMMAGINI ---
    "🇺🇸 AZIONI USA": {
        "NVIDIA": "NVDA", "AMD": "AMD", "Apple": "AAPL", 
        "Microsoft": "MSFT", "Meta": "META", "Alphabet": "GOOG",
        "Netflix": "NFLX", "Intel": "INTC", "Enphase": "ENPH", "DexCom": "DXCM"
    },
    "🇮🇹 AZIONI ITA": {
        "UniCredit": "UCG.MI", "Intesa SP": "ISP.MI", "Enel": "ENEL.MI",
        "Eni": "ENI.MI", "Leonardo": "LDO.MI", "Stellantis": "STLAM.MI",
        "Ferrari": "RACE.MI", "STMicro": "STMMI.MI", "Fineco": "FBK.MI",
        "Nexi": "NEXI.MI", "A2A": "A2A.MI", "OVS": "OVS.MI"
    }
}

def fetch_performance():
    text = "📊 <b>VARIAZIONI MERCATI & TITOLI</b>\n"
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
                    # Formattazione per mantenere l'allineamento
                    text += f"{status} <code>{name:<12}</code> <b>{sign}{change:.2f}%</b>\n"
            except:
                text += f"❌ <code>{name:<12}</code> Errore\n"
        text += "\n"
    return text + "────────────────────"

async def manual_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = fetch_performance()
    await update.message.reply_text(report, parse_mode='HTML')

async def auto_report_job(context: ContextTypes.DEFAULT_TYPE):
    tz = pytz.timezone('Europe/Rome')
    # Usiamo datetime.now(tz) per sicurezza sull'orario
    import datetime
    now = datetime.datetime.now(tz)
    
    if 10 <= now.hour <= 21:
        report = fetch_performance()
        await context.bot.send_message(chat_id=context.job.chat_id, text=report, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()

    context.job_queue.run_repeating(auto_report_job, interval=7200, first=10, chat_id=chat_id, name=str(chat_id))
    await update.message.reply_text("✅ Bot attivo e titoli aggiunti!\n\n- /quotazioni per i dati ora\n- Report automatico ogni 2 ore (10-21).")

if __name__ == '__main__':
    with open("token.txt", "r") as f:
        token = f.read().strip()
    
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quotazioni", manual_report))
    
    print("Bot in esecuzione con i nuovi titoli...")
    app.run_polling()
