import logging
import yfinance as yf
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configurazione Log
logging.basicConfig(level=logging.INFO)

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
    "🇪🇺 AZIONI EU": {
        "UniCredit": "UCG.MI", "Intesa SP": "ISP.MI", "MPS": "BMPS.MI", "Fineco": "FBK.MI", "Nexi": "NEXI.MI",
        "Enel": "ENEL.MI", "Eni": "ENI.MI", "A2A": "A2A.MI", 
        "Leonardo": "LDO.MI", "STMicro": "STMMI.MI", "Cy4gate": "CY4.MI",
        "Stellantis": "STLAM.MI", "Ferrari": "RACE.MI", "Volkswagen": "VOW3.DE",
        "OVS": "OVS.MI"
    }
}
def generate_visual_bar(current, low, high, slots=12):
    """Crea una barra tipo [---●-----] per il posizionamento nel range"""
    if not (low < current < high):
        if current <= low: return "<b>[●----------]</b> L"
        if current >= high: return "<b>[----------●]</b> H"
    
    relative_pos = (current - low) / (high - low)
    dot_pos = int(relative_pos * slots)
    bar = ["-"] * (slots + 1)
    if 0 <= dot_pos <= slots:
        bar[dot_pos] = "●"
    return f"<code>[{''.join(bar)}]</code>"

def fetch_data():
    perf_text = "📊 <b>VARIAZIONI MERCATI</b>\n"
    perf_text += f"🕒 <i>{datetime.now(pytz.timezone('Europe/Rome')).strftime('%H:%M')}</i>\n"
    perf_text += "────────────────────\n\n"
    
    range_text = "📈 <b>POSIZIONAMENTO 52 SETT.</b>\n"
    range_text += "<i>(Distanza Minimo L ↔ Massimo H)</i>\n"
    range_text += "────────────────────\n\n"

    for category, tickers in MARKETS.items():
        perf_text += f"<b>{category}</b>\n"
        range_text += f"<b>{category}</b>\n"
        
        for name, symbol in tickers.items():
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period="2d")
                info = t.info
                
                if len(hist) >= 2:
                    # Parte 1: Performance
                    curr_price = hist['Close'].iloc[-1]
                    prev_price = hist['Close'].iloc[-2]
                    change = ((curr_price - prev_price) / prev_price) * 100
                    status = "🟢" if change >= 0 else "🔴"
                    perf_text += f"{status} <code>{name:<12}</code> <b>{"+" if change>=0 else ""}{change:.2f}%</b>\n"
                    
                    # Parte 2: Range 52w
                    low_52 = info.get('fiftyTwoWeekLow')
                    high_52 = info.get('fiftyTwoWeekHigh')
                    if low_52 and high_52:
                        bar = generate_visual_bar(curr_price, low_52, high_52)
                        range_text += f"<code>{name:<12}</code> {bar}\n"
            except:
                pass
        perf_text += "\n"
        range_text += "\n"
        
    return perf_text, range_text

async def send_report(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    perf_msg, range_msg = fetch_data()
    # Invio separato per pulizia visiva
    await context.bot.send_message(chat_id=chat_id, text=perf_msg, parse_mode='HTML')
    await context.bot.send_message(chat_id=chat_id, text=range_msg, parse_mode='HTML')

async def manual_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_report(context, update.effective_chat.id)

async def auto_report_job(context: ContextTypes.DEFAULT_TYPE):
    tz = pytz.timezone('Europe/Rome')
    now = datetime.now(tz)
    if 10 <= now.hour <= 22:
        await send_report(context, context.job.chat_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()
    
    context.job_queue.run_repeating(auto_report_job, interval=3600, first=5, chat_id=chat_id, name=str(chat_id))
    await update.message.reply_text("✅ <b>Bot attivo!</b>\nRiceverai due messaggi: variazioni e analisi range.", parse_mode='HTML')

if __name__ == '__main__':
    with open("token.txt", "r") as f:
        token = f.read().strip()
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quotazioni", manual_report))
    app.run_polling()
