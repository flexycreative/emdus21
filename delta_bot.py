import os
import requests
from datetime import datetime, timezone

TOKEN   = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

print(f"🔐 TOKEN uzunluk: {len(TOKEN)} karakter")
print(f"🔐 TOKEN ilk 10: {TOKEN[:10]}...")
print(f"🔐 CHAT_ID: {CHAT_ID}")

QUOTE            = "USDT"
INTERVAL         = "5m"
HOURS            = 24
MIN_VOLUME_USDT  = 50_000
TOP_N            = 10

STABLES = {"USDC", "RLUSD", "USD1", "UUSDT", "FDUSD", "TUSD", "DAI",
           "BUSD", "USDP", "PYUSD", "USDD", "USDE", "XUSD", "EUR",
           "EURI", "AEUR", "BUIDL"}


def scan(base_url, label):
    print(f"🔍 {label} pariteleri alınıyor...")
    try:
        r = requests.get(f"{base_url}/exchangeInfo", timeout=30)
        info = r.json()
    except Exception as e:
        print(f"❌ {label} bağlantı hatası: {e}")
        return []
    
    if not isinstance(info, dict) or "symbols" not in info:
        print(f"❌ {label} API hatası: {info}")
        return []
    
    symbols = [s["symbol"] for s in info["symbols"]
               if s.get("quoteAsset") == QUOTE and s.get("status") == "TRADING"]
    symbols = [s for s in symbols if not any(s.startswith(st) for st in STABLES)]
    print(f"  → {len(symbols)} parite taranacak")

    now      = datetime.now(timezone.utc)
    end_ms   = int(now.timestamp() * 1000)
    start_ms = end_ms - HOURS * 3600 * 1000

    results = []
    url = f"{base_url}/klines"

    for idx, sym in enumerate(symbols, 1):
        try:
            all_k = []
            cursor = start_ms
            while cursor < end_ms:
                r = requests.get(url, params={
                    "symbol": sym, "interval": INTERVAL,
                    "startTime": cursor, "endTime": end_ms, "limit": 500
                }, timeout=15)
                chunk = r.json()
                if not isinstance(chunk, list) or len(chunk) == 0:
                    break
                all_k.extend(chunk)
                if len(chunk) < 500:
                    break
                cursor = chunk[-1][0] + 60_000

            if len(all_k) == 0:
                continue

            tq = tbq = 0.0
            for k in all_k:
                tq  += float(k[7])
                tbq += float(k[10])

            if tq < MIN_VOLUME_USDT:
                continue

            results.append({
                "symbol": sym,
                "volume": tq,
                "delta":  tbq - (tq - tbq),
            })
        except Exception:
            pass

        if idx % 50 == 0:
            print(f"  ✓ {label}: {idx}/{len(symbols)}")

    print(f"✅ {label}: {len(results)} parite tarandı\n")
    results.sort(key=lambda x: x["delta"])
    return results


def fmt(x):
    a = abs(x)
    if a >= 1e9: return f"{x/1e9:+.2f}B"
    if a >= 1e6: return f"{x/1e6:+.2f}M"
    if a >= 1e3: return f"{x/1e3:+.2f}K"
    return f"{x:+.2f}"


def main():
    spot = scan("https://data-api.binance.vision/api/v3", "SPOT")

    now = datetime.now(timezone.utc)

    lines = [
        "📊 *Spot Delta Raporu*",
        f"🕒 {now.strftime('%d.%m.%Y %H:%M')} UTC",
        f"⏱️ Son {HOURS} saat",
        f"📊 {len(spot)} parite",
        "",
        "🔴 *En Çok Satış*",
    ]
    for r in spot[:TOP_N]:
        lines.append(f"`{r['symbol']:<13}` {fmt(r['delta'])}")

    lines.append("")
    lines.append("🟢 *En Çok Alış*")
    for r in spot[-TOP_N:][::-1]:
        lines.append(f"`{r['symbol']:<13}` {fmt(r['delta'])}")

    message = "\n".join(lines)
    print(f"📨 Mesaj uzunluğu: {len(message)} karakter")
    print(f"📨 Mesajın ilk satırı: {lines[0]}")

    url_tg = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        r = requests.post(url_tg, data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=30)
        print(f"📤 Telegram yanıtı: {r.status_code}")
        print(f"📤 Telegram JSON: {r.json()}")
        
        if not r.json().get("ok"):
            print(f"❌ TELEGRAM HATASI: {r.json()}")
        else:
            print(f"✅ TELEGRAM BAŞARILI")
    except Exception as e:
        print(f"❌ Telegram gönderim hatası: {e}")


if __name__ == "__main__":
    main()
