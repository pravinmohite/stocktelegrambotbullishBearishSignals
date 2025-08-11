import os, requests, yfinance as yf
import pandas as pd

BOT_TOKEN = '7745153783:AAHYmV0ZPdU6reeiwv3nrMO2fS_naQoJ10w'
CHAT_ID = '806642925'

from nsetools import Nse


def get_top_gainers():
    nse = Nse()
    try:
        top = nse.get_top_gainers()
        return [item["symbol"] + ".NS" for item in top[:10]]
    except Exception as e:
        print("Error using nsetools:", e)
        return []


def get_top_losers():
    nse = Nse()
    try:
        top = nse.get_top_losers()
        return [item["symbol"] + ".NS" for item in top[:10]]
    except Exception as e:
        print("Error using nsetools:", e)
        return []


def compute_rsi(data, window=14):
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi  # This is a Pandas Series


def analyze_stocks():
    import yfinance as yf

    messages = []
    indices = ["^NSEI", "^NSEBANK"]  # Nifty 50, Bank Nifty
    symbols = get_top_gainers() + get_top_losers() + indices

    for s in symbols:
        df = yf.download(s,
                         period="25d",
                         interval="1d",
                         progress=False,
                         auto_adjust=True)

        if df.empty or len(df) < 20:
            continue

        # Indicators
        df["SMA5"] = df["Close"].rolling(5).mean()
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["RSI"] = compute_rsi(df)
        df["AvgVol10"] = df["Volume"].rolling(10).mean()

        # Skip if any recent values are null
        if df[["SMA5", "SMA20", "RSI",
               "AvgVol10"]].iloc[-2:].isnull().values.any():
            continue

        try:
            sma5 = df["SMA5"].iloc[-1]
            sma5_prev = df["SMA5"].iloc[-2]
            sma20 = df["SMA20"].iloc[-1]
            sma20_prev = df["SMA20"].iloc[-2]
            rsi = df["RSI"].iloc[-1]
            today_vol = df["Volume"].iloc[-1]
            avg_vol = df["AvgVol10"].iloc[-2]
            close = df["Close"].iloc[-1]
            open_price = df["Open"].iloc[-1]
            recent_high = df["Close"].iloc[-10:].max()
            recent_low = float(df["Close"].iloc[-10:].min())

            # Convert to float explicitly (avoids Series ambiguity)
            today_vol = float(today_vol)
            avg_vol = float(avg_vol)
            close = float(close)
            open_price = float(open_price)
            recent_high = float(recent_high)

            change_percent = ((close - open_price) / open_price) * 100
        except Exception as e:
            print(f"❌ Error processing {s}: {e}")
            continue

        # Signal Strength Score (0–100)
        score = 0
        if sma5 > sma20 and sma5_prev < sma20_prev:
            score += 30
        if 55 < rsi < 70:
            score += 20
        if today_vol > 1.5 * avg_vol:
            score += 20
        if close >= 0.98 * recent_high:
            score += 15
        if change_percent > 0.8:
            score += 15

        if score >= 50:  # should be 90, atleast more than 50
            name = s.replace("^NSEI", "NIFTY").replace("^NSEBANK", "BANKNIFTY")
            msg = (f"🚀 High Probability Bullish Move Detected: {name}\n"
                   f"📈 Change: {change_percent:.2f}%\n"
                   f"📊 RSI: {rsi:.1f}, SMA5: {sma5:.2f} > SMA20: {sma20:.2f}\n"
                   f"🔊 Vol: {today_vol:,} vs Avg: {avg_vol:,.0f}\n"
                   f"🎯 Close: {close:.2f} (10d High: {recent_high:.2f})\n"
                   f"🔥 Confidence Score: {score}/100")
            messages.append(msg)
            print(f"✅ {s} passed:\n{msg}\n")
        else:
            print(f"❌ {s} bullish score {score}, skipping.")

        # Bearish Score
        bear_score = 0
        if sma5 < sma20 and sma5_prev > sma20_prev:
            bear_score += 30
        if 30 < rsi < 45:
            bear_score += 20
        if today_vol > 1.5 * avg_vol:
            bear_score += 20
        if close <= 1.02 * recent_low:
            bear_score += 15
        if change_percent < -0.8:
            bear_score += 15

        if bear_score >= 50:  # should be 90, atleast more than 50
            name = s.replace("^NSEI", "NIFTY").replace("^NSEBANK", "BANKNIFTY")
            msg = (f"🔻 Bearish Signal: {name}\n"
                   f"📉 Change: {change_percent:.2f}%\n"
                   f"📊 RSI: {rsi:.1f}, SMA5: {sma5:.2f} < SMA20: {sma20:.2f}\n"
                   f"🔊 Vol: {today_vol:,} vs Avg: {avg_vol:,.0f}\n"
                   f"🎯 Close: {close:.2f} (10d Low: {recent_low:.2f})\n"
                   f"⚠️ Confidence Score: {bear_score}/100")
            messages.append(msg)
            print(f"✅ Bearish {s}:\n{msg}\n")
        else:
            print(f"❌ {s} bearish score {bear_score}, skipping.")

    if not messages:
        messages.append("⚠️ No high-confidence signals today.")
    return messages


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    if response.status_code != 200:
        print("❌ Telegram Error:", response.text)


if __name__ == "__main__":
    picks = analyze_stocks()
    message = "🔔 Dynamic bullish/bearish picks from today's gainers/losers:\n\n"

if picks:
    message += "\n\n".join(picks)
else:
    message += "⚠️ No signals found"

send_telegram(message)
