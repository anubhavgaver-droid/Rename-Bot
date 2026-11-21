# ============ config.py ============
# Saari values yahin bharo. Baaki files ko chhedna nahi hai.

API_ID = 35320999                      # my.telegram.org se
API_HASH = "a59f29b9134e32b1f1e71f184350e4d3"          # my.telegram.org se
BOT_TOKEN = "9183562926:AAH6AOymmyD9DDF_dQsMtmmgaW9dheM2dVo"   # @BotFather se

# Sirf ye users bot chala sakte hain. Khaali [] rakhoge to sab chala sakenge.
AUTH_USERS = [8720933495]

# Rename ki hui file kahan jaye? 0 = usi chat me. Ya channel/group ID: -100xxxxxxxxxx
TARGET_CHAT = 0

# True = sab kuch Document ki tarah bhejega (file ka naam Telegram me dikhega)
# False = video ko video hi bhejega (naam sirf caption me dikhega)
FORCE_DOCUMENT = True

# Download temporary folder (Linux). Windows par "downloads/" kar lena.
DOWNLOAD_DIR = "/tmp/"

# Web server (Render jaise host ke liye zaroori, VPS par False kar do)
WEB_SERVER = True
PORT = 8080

# ---------- Default values (bot ke andar /commands se badal sakte ho) ----------
DEFAULT_TITLE = "My Story"
DEFAULT_ARTIST = "Artist Name"
DEFAULT_QUALITY = "720p"

# Placeholders: {title} {ep} {quality} {artist}
DEFAULT_NAME_TPL = "{title} - Episode {ep} [{quality}]"
DEFAULT_CAP_TPL = (
    "<b>{title} - Episode {ep}</b>\n\n"
    "🎨 Artist: {artist}\n"
    "📺 Quality: {quality}"
)
