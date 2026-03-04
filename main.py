import logging
import yfinance as yf
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# Configurazione Log
logging.basicConfig(level=logging.INFO)
MARKETS = {
    "🇺🇸 INDICI USA": {"S&P 500": "^GSPC", "Dow Jones": "^DJI", "Nasdaq 100": "^NDX"},
    "🇪🇺 INDICI EUROPA": {"Stoxx 600": "^STOXX", "FTSE MIB": "FTSEMIB.MI", "DAX": "^GDAXI", "CAC 40": "^FCHI", "FTSE 100": "^FTSE", "IBEX 35": "^IBEX"},
    "🌏 ASIA": {"Nikkei 225": "^N225", "Shanghai": "000001.SS", "KOSPI": "^KS11"},
    "🛢️ COMMODITIES": {"Petrolio WTI": "CL=F", "Gas Naturale": "TTF=F"},
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

# --- LOGICA DATI ---
def generate_visual_bar(current, low, high, slots=10):
    if not low or not high or low == high: return "N/A"
    relative_pos = (current - low) / (high - low)
    dot_pos = max(0, min(slots, int(relative_pos * slots)))
    bar = ["-"] * (slots + 1)
    bar[dot_pos] = "●"
    return f"<code>[{''.join(bar)}]</code>"

def fetch_data():
    perf_text = "📊 <b>VARIAZIONI MERCATI</b>\n"
    perf_text += f"🕒 <i>{datetime.now(pytz.timezone('Europe/Rome')).strftime('%H:%M')}</i>\n"
    perf_text += "────────────────────\n\n"
    
    range_text = "📈 <b>RANGE 52 SETT. (L ↔ H)</b>\n"
    range_text += "────────────────────\n\n"

    for category, tickers in MARKETS.items():
        perf_text += f"<b>{category}</b>\n"
        range_text += f"<b>{category}</b>\n"
        for name, symbol in tickers.items():
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period="2d")
                if len(hist) < 2: continue
                
                curr = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change = ((curr - prev) / prev) * 100
                
                perf_text += f"{'🟢' if change >= 0 else '🔴'} <code>{name:<12}</code> <b>{'+' if change>=0 else ''}{change:.2f}%</b>\n"
                
                info = t.info
                range_text += f"<code>{name:<12}</code> {generate_visual_bar(curr, info.get('fiftyTwoWeekLow'), info.get('fiftyTwoWeekHigh'))}\n"
            except: pass
        perf_text += "\n"; range_text += "\n"
    return perf_text, range_text

# --- HANDLERS ---
async def send_report(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    perf_msg, range_msg = fetch_data()
    await context.bot.send_message(chat_id=chat_id, text=perf_msg, parse_mode='HTML')
    await context.bot.send_message(chat_id=chat_id, text=range_msg, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Tastiera fissa (ReplyKeyboard)
    keyboard = [["📊 QUOTAZIONI", "⏱️ IMPOSTA TIMER"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🚀 <b>Bot pronto!</b>\nUsa i tasti qui sotto per interagire velocemente.",
        reply_markup=reply_markup, parse_mode='HTML'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📊 QUOTAZIONI":
        await send_report(context, update.effective_chat.id)
    elif text == "⏱️ IMPOSTA TIMER":
        # Tastiera a scomparsa (Inline)
        keyboard = [
            [InlineKeyboardButton("15 Minuti", callback_data='900'),
             InlineKeyboardButton("30 Minuti", callback_data='1800')],
            [InlineKeyboardButton("1 Ora", callback_data='3600'),
             InlineKeyboardButton("2 Ore", callback_data='7200')],
            [InlineKeyboardButton("Disattiva", callback_data='stop')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Scegli ogni quanto ricevere gli aggiornamenti:", reply_markup=reply_markup)

async def timer_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    # Rimuovi vecchi job
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()

    if data == 'stop':
        await query.edit_message_text("❌ Invio automatico disattivato.")
        return

    interval = int(data)
    # Imposta nuovo job
    context.job_queue.run_repeating(
        auto_report_job, interval=interval, first=10, 
        chat_id=chat_id, name=str(chat_id)
    )
    
    mins = interval // 60
    await query.edit_message_text(f"✅ Timer impostato: riceverai i dati ogni <b>{mins} minuti</b> (h 10-22).", parse_mode='HTML')

async def auto_report_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(pytz.timezone('Europe/Rome'))
    if 10 <= now.hour <= 22:
        await send_report(context, context.job.chat_id)

if __name__ == '__main__':
    with open("token.txt", "r") as f:
        token = f.read().strip()
    
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(timer_button))
    
    print("Bot online con pulsanti e timer dinamico...")
    app.run_polling()
