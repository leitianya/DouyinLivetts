# config.py

# WebSocket and HTTP Request Configuration
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
DOUYIN_LIVE_URL = "https://live.douyin.com/"
WSS_URL_TEMPLATE = (
    "wss://webcast5-ws-web-hl.douyin.com/webcast/im/push/v2/?"
    "app_name=douyin_web&version_code=180800&webcast_sdk_version=1.0.14-beta.0"
    "&update_version_code=1.0.14-beta.0&compress=gzip&device_platform=web"
    "&cookie_enabled=true&screen_width=1536&screen_height=864"
    "&browser_language=zh-CN&browser_platform=Win32&browser_name=Mozilla"
    "&browser_version=5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,"
    "%20like%20Gecko)%20Chrome/126.0.0.0%20Safari/537.36"
    "&browser_online=true&tz_name=Asia/Shanghai"
    "&cursor=d-1_u-1_fh-7392091211001140287_t-1721106114633_r-1"
    "&internal_ext=internal_src:dim|wss_push_room_id:{room_id}|wss_push_did:7319483754668557238"
    "|first_req_ms:1721106114541|fetch_time:1721106114633|seq:1|wss_info:0-1721106114633-0-0|"
    "wrds_v:7392094459690748497"
    "&host=https://live.douyin.com&aid=6383&live_id=1&did_rule=3&endpoint=live_pc"
    "&support_wrds=1&user_unique_id=7319483754668557238&im_path=/webcast/im/fetch/"
    "&identity=audience&need_persist_msg_count=15&insert_task_id=&live_reason="
    "&room_id={room_id}&heartbeatDuration=0"
)

# TTS Configuration
TTS_VOICES = [
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-XiaoyiNeural",
    "zh-CN-YunjianNeural",
    "zh-CN-YunxiNeural",
    "zh-CN-YunxiaNeural",
    "zh-CN-YunyangNeural",
]
TTS_PROXY = "http://192.168.10.66:10707"
USE_TTS_PROXY = False
TTS_MAX_RETRIES = 3
TTS_RETRY_DELAY = 1  # in seconds
AUDIO_OUTPUT_DIR = "msic"

# GUI Configuration
WINDOW_TITLE = "抖音直播信息"
WINDOW_WIDTH = 320
WINDOW_HEIGHT = 120
WINDOW_BG_COLOR = "black"
FONT_FAMILY = "Microsoft YaHei UI"
FONT_SIZE_NORMAL = 12
FONT_SIZE_LARGE = 16

# WebSocket Connection
MESSAGE_TIMEOUT = 10  # in seconds
