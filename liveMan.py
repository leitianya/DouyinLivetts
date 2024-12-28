#!/usr/bin/python
# coding:utf-8

# @FileName:    liveMan.py
# @Time:        2024/1/2 21:51
# @Author:      bubu
# @Project:     douyinLiveWebFetcher

import codecs
import gzip
import hashlib
import os
import random
import re
import string
import subprocess
import sys
import time
import urllib.parse
from contextlib import contextmanager
import tkinter as tk
from py_mini_racer import MiniRacer
from unittest.mock import patch
import requests
import websocket
from protobuf.douyin import *
import uuid
import threading
from txt_speak import play_speech_thread


@contextmanager
def patched_popen_encoding(encoding='utf-8'):
    original_popen_init = subprocess.Popen.__init__

    def new_popen_init(self, *args, **kwargs):
        kwargs['encoding'] = encoding
        original_popen_init(self, *args, **kwargs)

    with patch.object(subprocess.Popen, '__init__', new_popen_init):
        yield


def generateSignature(wss, script_file='sign.js'):
    """
    出现gbk编码问题则修改 python模块subprocess.py的源码中Popen类的__init__函数参数encoding值为 "utf-8"
    """
    # 获取运行路径
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径
        base_path = sys._MEIPASS
    else:
        # 脚本直接运行时的路径
        base_path = os.path.dirname(__file__)

    # 获取sign.js的完整路径
    script_path = os.path.join(base_path, script_file)
    params = ("live_id,aid,version_code,webcast_sdk_version,"
              "room_id,sub_room_id,sub_channel_id,did_rule,"
              "user_unique_id,device_platform,device_type,ac,"
              "identity").split(',')
    wss_params = urllib.parse.urlparse(wss).query.split('&')
    wss_maps = {i.split('=')[0]: i.split("=")[-1] for i in wss_params}
    tpl_params = [f"{i}={wss_maps.get(i, '')}" for i in params]
    param = ','.join(tpl_params)
    md5 = hashlib.md5()
    md5.update(param.encode())
    md5_param = md5.hexdigest()

    with codecs.open(script_path, 'r', encoding='utf8') as f:
        script = f.read()

    ctx = MiniRacer()
    ctx.eval(script)

    try:
        signature = ctx.call("get_sign", md5_param)
        return signature
    except Exception as e:
        print(e)

    # 以下代码对应js脚本为sign_v0.js
    # context = execjs.compile(script)
    # with patched_popen_encoding(encoding='utf-8'):
    #     ret = context.call('getSign', {'X-MS-STUB': md5_param})
    # return ret.get('X-Bogus')


def generateMsToken(length=107):
    """
    产生请求头部cookie中的msToken字段，其实为随机的107位字符
    :param length:字符位数
    :return:msToken
    """
    random_str = ''
    base_str = string.ascii_letters + string.digits + '=_'
    _len = len(base_str) - 1
    for _ in range(length):
        random_str += base_str[random.randint(0, _len)]
    return random_str


class DouyinLiveWebFetcher:

    def __init__(self, live_id):
        """
        直播间弹幕抓取对象
        :param live_id: 直播间的直播id，打开直播间web首页的链接如：https://live.douyin.com/261378947940，
                        其中的261378947940即是live_id
        """
        self.__ttwid = None
        self.__room_id = None
        self.live_id = live_id
        self.live_url = "https://live.douyin.com/"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                          "Chrome/120.0.0.0 Safari/537.36"
        self.window = None  # 只初始化窗口一次
        self.label = None  # 显示数据的标签
        self.chat_checkbox = None
        self.gift_checkbox = None
        self.follow_checkbox = None
        self.welcome_checkbox = None
        self.speech_enabled = False
        self.gift_enabled = False
        self.follow_enabled = False
        self.welcome_enabled = False
        self.ws_thread = None

    def gui(self):
        print("初始化gui窗口！")
        # 创建主窗口
        window = tk.Tk()

        # 设置窗口标题
        window.title("抖音直播信息")

        # 设置窗口大小
        width, height = 250, 80  # 窗口的宽和高

        # 获取屏幕宽度和高度
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # 计算窗口位置：水平居中，上方稍微靠下（以屏幕高度的1/4为例）
        x = (screen_width - width) // 2
        y = -32

        # 设置窗口大小
        window.geometry(f"{width}x{height}+{x}+{y}")
        # 设置窗口透明度（背景颜色透明）
        window.attributes("-alpha", 1)
        window.attributes("-transparentcolor", "red")
        window.configure(bg="red")
        # 禁止调整窗口大小
        window.resizable(False, False)

        # window.overrideredirect(True)
        window.attributes("-topmost", True)

        # 创建标签来显示 `display_long` 数据（设置不透明背景）
        self.label = tk.Label(window, text="直播间人数", font=("Arial", 16), bg="black", fg="white")
        self.label.pack(pady=5)

        # 创建一个框架容器，用于并列放置按钮
        checkbox_frame = tk.Frame(window, bg="black")  # 设置背景为黑色以匹配复选框
        checkbox_frame.pack(pady=5)  # 添加框架的边距

        # 在框架中添加聊天复选框
        self.chat_checkbox = tk.Checkbutton(checkbox_frame, text="聊天",
                                            variable=tk.BooleanVar(value=self.speech_enabled),
                                            command=self.toggle_speech,
                                            bg="black", fg="white",
                                            activebackground="red",
                                            selectcolor="red")
        self.chat_checkbox.pack(side=tk.LEFT, padx=5)

        # 在框架中添加谢礼物复选框
        self.gift_checkbox = tk.Checkbutton(checkbox_frame, text="礼物",
                                            variable=tk.BooleanVar(value=self.gift_enabled),
                                            command=self.gift_speech,
                                            bg="black", fg="white",
                                            activebackground="red",
                                            selectcolor="red")
        self.gift_checkbox.pack(side=tk.LEFT, padx=5)

        # 在框架中添加谢关注复选框
        self.follow_checkbox = tk.Checkbutton(checkbox_frame, text="关注",
                                            variable=tk.BooleanVar(value=self.follow_enabled),
                                            command=self.follow_speech,
                                            bg="black", fg="white",
                                            activebackground="red",
                                            selectcolor="red")
        self.follow_checkbox.pack(side=tk.LEFT, padx=5)

        # 在框架中添加进场复选框
        self.welcome_checkbox = tk.Checkbutton(checkbox_frame, text="进场",
                                              variable=tk.BooleanVar(value=self.welcome_enabled),
                                              command=self.welcome_speech,
                                              bg="black", fg="white",
                                              activebackground="red",
                                              selectcolor="red")
        self.welcome_checkbox.pack(side=tk.LEFT, padx=5)

        # 添加一个按钮
        # button = tk.Button(window, text="关闭", command=window.quit)
        # button.pack(pady=10)

        # 运行主循环
        window.mainloop()

    def toggle_speech(self):
        """
        切换聊天播报的启用状态
        """
        self.speech_enabled = not self.speech_enabled
        print(f"聊天播报 {'启用' if self.speech_enabled else '禁用'}")

    def gift_speech(self):
        """
        切换礼物播报的启用状态
        """
        self.gift_enabled = not self.gift_enabled
        print(f"礼物播报 {'启用' if self.gift_enabled else '禁用'}")

    def follow_speech(self):
        """
        切换关注播报的启用状态
        """
        self.follow_enabled = not self.follow_enabled
        print(f"关注播报 {'启用' if self.follow_enabled else '禁用'}")

    def welcome_speech(self):
        """
        切换关注播报的启用状态
        """
        self.welcome_enabled = not self.welcome_enabled
        print(f"进场播报 {'启用' if self.welcome_enabled else '禁用'}")

    def start(self):
        threading.Thread(target=self._connectWebSocket, daemon=True).start()
        self.gui()

    def stop(self):
        self.ws.close()

    @property
    def ttwid(self):
        """
        产生请求头部cookie中的ttwid字段，访问抖音网页版直播间首页可以获取到响应cookie中的ttwid
        :return: ttwid
        """
        if self.__ttwid:
            return self.__ttwid
        headers = {
            "User-Agent": self.user_agent,
        }
        try:
            response = requests.get(self.live_url, headers=headers)
            response.raise_for_status()
        except Exception as err:
            print("【X】Request the live url error: ", err)
        else:
            self.__ttwid = response.cookies.get('ttwid')
            return self.__ttwid

    @property
    def room_id(self):
        """
        根据直播间的地址获取到真正的直播间roomId，有时会有错误，可以重试请求解决
        :return:room_id
        """
        if self.__room_id:
            return self.__room_id
        url = self.live_url + self.live_id
        headers = {
            "User-Agent": self.user_agent,
            "cookie": f"ttwid={self.ttwid}&msToken={generateMsToken()}; __ac_nonce=0123407cc00a9e438deb4",
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except Exception as err:
            print("【X】Request the live room url error: ", err)
        else:
            match = re.search(r'roomId\\":\\"(\d+)\\"', response.text)
            if match is None or len(match.groups()) < 1:
                print("【X】No match found for roomId")

            self.__room_id = match.group(1)

            return self.__room_id

    def _connectWebSocket(self):
        """
        连接抖音直播间websocket服务器，请求直播间数据，支持自动重连。
        """
        while True:
            try:
                wss = ("wss://webcast5-ws-web-hl.douyin.com/webcast/im/push/v2/?app_name=douyin_web"
                       "&version_code=180800&webcast_sdk_version=1.0.14-beta.0"
                       "&update_version_code=1.0.14-beta.0&compress=gzip&device_platform=web&cookie_enabled=true"
                       "&screen_width=1536&screen_height=864&browser_language=zh-CN&browser_platform=Win32"
                       "&browser_name=Mozilla"
                       "&browser_version=5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,"
                       "%20like%20Gecko)%20Chrome/126.0.0.0%20Safari/537.36"
                       "&browser_online=true&tz_name=Asia/Shanghai"
                       "&cursor=d-1_u-1_fh-7392091211001140287_t-1721106114633_r-1"
                       f"&internal_ext=internal_src:dim|wss_push_room_id:{self.room_id}|wss_push_did:7319483754668557238"
                       f"|first_req_ms:1721106114541|fetch_time:1721106114633|seq:1|wss_info:0-1721106114633-0-0|"
                       f"wrds_v:7392094459690748497"
                       f"&host=https://live.douyin.com&aid=6383&live_id=1&did_rule=3&endpoint=live_pc&support_wrds=1"
                       f"&user_unique_id=7319483754668557238&im_path=/webcast/im/fetch/&identity=audience"
                       f"&need_persist_msg_count=15&insert_task_id=&live_reason=&room_id={self.room_id}&heartbeatDuration=0")

                signature = generateSignature(wss)
                wss += f"&signature={signature}"

                headers = {
                    "cookie": f"ttwid={self.ttwid}",
                    'user-agent': self.user_agent,
                }
                self.ws = websocket.WebSocketApp(wss,
                                                 header=headers,
                                                 on_open=self._wsOnOpen,
                                                 on_message=self._wsOnMessage,
                                                 on_error=self._wsOnError,
                                                 on_close=self._wsOnClose)

                print("尝试连接到 WebSocket...")
                self.ws.run_forever()

            except Exception as e:
                print(f"WebSocket连接异常: {e}")

            print("尝试重新连接...")
            time.sleep(5)  # 等待 5 秒后重试

    def _wsOnOpen(self, ws):
        """
        连接建立成功
        """
        print("WebSocket connected.")

    def _wsOnMessage(self, ws, message):
        """
        接收到数据
        :param ws: websocket实例
        :param message: 数据
        """

        # 根据proto结构体解析对象
        package = PushFrame().parse(message)
        response = Response().parse(gzip.decompress(package.payload))

        # 返回直播间服务器链接存活确认消息，便于持续获取数据
        if response.need_ack:
            ack = PushFrame(log_id=package.log_id,
                            payload_type='ack',
                            payload=response.internal_ext.encode('utf-8')
                            ).SerializeToString()
            ws.send(ack, websocket.ABNF.OPCODE_BINARY)

        # 根据消息类别解析消息体
        for msg in response.messages_list:
            method = msg.method
            try:
                {
                    'WebcastChatMessage': self._parseChatMsg,  # 聊天消息
                    'WebcastGiftMessage': self._parseGiftMsg,  # 礼物消息
                    'WebcastLikeMessage': self._parseLikeMsg,  # 点赞消息
                    'WebcastMemberMessage': self._parseMemberMsg,  # 进入直播间消息
                    'WebcastSocialMessage': self._parseSocialMsg,  # 关注消息
                    'WebcastRoomUserSeqMessage': self._parseRoomUserSeqMsg,  # 直播间统计
                    'WebcastFansclubMessage': self._parseFansclubMsg,  # 粉丝团消息
                    'WebcastControlMessage': self._parseControlMsg,  # 直播间状态消息
                    'WebcastEmojiChatMessage': self._parseEmojiChatMsg,  # 聊天表情包消息
                    'WebcastRoomStatsMessage': self._parseRoomStatsMsg,  # 直播间统计信息
                    'WebcastRoomMessage': self._parseRoomMsg,  # 直播间信息
                    'WebcastRoomRankMessage': self._parseRankMsg,  # 直播间排行榜信息
                }.get(method)(msg.payload)
            except Exception:
                pass

    def _wsOnError(self, ws, error):
        print("WebSocket error: ", error)

    def _wsOnClose(self, ws, *args):
        print("WebSocket connection closed.")

    def handle_chat_message(self, user_name, content):
        unique_id = str(uuid.uuid4())
        output_file = f"msic/MemberMsg_{unique_id}.mp3"
        text = f"{user_name}说：{content}。"
        play_speech_thread(text, output_file, v_num=0)

    def _parseChatMsg(self, payload):
        """聊天消息"""
        message = ChatMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        content = message.content
        print(f"【聊天msg】[{user_id}]{user_name}: {content}")
        if self.speech_enabled:
            # 如果chat_thread线程已存在并且仍在运行，则不创建新的线程
            if self.ws_thread is not None and self.ws_thread.is_alive():
                print("当前线程正在处理消息，跳过新线程创建。")
                return

            # 启动新线程处理消息
            self.ws_thread = threading.Thread(target=self.handle_chat_message, args=(user_name, content))
            self.ws_thread.start()

    def handle_gift_message(self, user_name, gift_name):
        # 生成唯一的语音文件名
        unique_id = str(uuid.uuid4())
        output_file = f"msic/MemberMsg_{unique_id}.mp3"
        text = f"超级感谢{user_name}老板送出的{gift_name}。"
        play_speech_thread(text, output_file, v_num=1)

    def _parseGiftMsg(self, payload):
        """礼物消息"""
        message = GiftMessage().parse(payload)
        user_name = message.user.nick_name
        gift_name = message.gift.name
        gift_cnt = message.combo_count
        print(f"【礼物msg】{user_name} 送出了 {gift_name}x{gift_cnt}")
        if self.gift_enabled:
            # 如果chat_thread线程已存在并且仍在运行，则不创建新的线程
            if self.ws_thread is not None and self.ws_thread.is_alive():
                print("当前线程正在处理消息，跳过新线程创建。")
                return

            # 启动新线程处理消息
            self.ws_thread = threading.Thread(target=self.handle_gift_message, args=(user_name, gift_name))
            self.ws_thread.start()

    def _parseLikeMsg(self, payload):
        '''点赞消息'''
        message = LikeMessage().parse(payload)
        user_name = message.user.nick_name
        count = message.count
        print(f"【点赞msg】{user_name} 点了{count}个赞")

        # unique_id = str(uuid.uuid4())
        # count_cn = cn2an.an2cn(str(count), "low")
        # output_file = f"msic/MemberMsg_{unique_id}.mp3"
        # text = "感谢" + user_name + f"给主播点了{count_cn}个赞。"
        # threading.Thread(target=play_speech_thread, args=(text, output_file)).start()

    def handle_welcome_message(self, user_name):
        # 生成唯一的语音文件名
        v_num = random.randint(0, 5)
        unique_id = str(uuid.uuid4())
        output_file = f"msic/MemberMsg_{unique_id}.mp3"
        text = f"欢迎{user_name} 进入了直播间。"
        play_speech_thread(text, output_file, v_num=v_num)

    def _parseMemberMsg(self, payload):
        '''进入直播间消息'''
        message = MemberMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        gender = ["女", "男"][message.user.gender]
        print(f"【进场msg】[{user_id}][{gender}]{user_name} 进入了直播间")
        if self.welcome_enabled:
            if self.ws_thread is not None and self.ws_thread.is_alive():
                print("当前线程正在处理消息，跳过新线程创建。")
                return
            # 启动新线程处理消息
            self.ws_thread = threading.Thread(target=self.handle_welcome_message, args=(user_name,))
            self.ws_thread.start()

    def handle_follow_message(self, user_name):
        # 生成唯一的语音文件名
        unique_id = str(uuid.uuid4())
        output_file = f"msic/MemberMsg_{unique_id}.mp3"
        text = f"感谢{user_name}关注主播。"
        play_speech_thread(text, output_file, v_num=3)

    def _parseSocialMsg(self, payload):
        '''关注消息'''
        message = SocialMessage().parse(payload)
        user_name = message.user.nick_name
        user_id = message.user.id
        print(f"【关注msg】[{user_id}]{user_name} 关注了主播")
        if self.follow_enabled:
            if self.ws_thread is not None and self.ws_thread.is_alive():
                print("当前线程正在处理消息，跳过新线程创建。")
                return
            # 启动新线程处理消息
            self.ws_thread = threading.Thread(target=self.handle_follow_message, args=(user_name,))
            self.ws_thread.start()

    def _parseRoomUserSeqMsg(self, payload):
        '''直播间统计'''
        message = RoomUserSeqMessage().parse(payload)
        current = message.total
        total = message.total_pv_for_anchor
        print(f"【统计msg】当前观看人数: {current}, 累计观看人数: {total}")
        # 如果有 label，更新显示的数据
        if self.label:
            self.label.config(text=f"当前观看：{current} 人")

    def _parseFansclubMsg(self, payload):
        '''粉丝团消息'''
        message = FansclubMessage().parse(payload)
        content = message.content
        print(f"【粉丝团msg】 {content}")

    def _parseEmojiChatMsg(self, payload):
        '''聊天表情包消息'''
        message = EmojiChatMessage().parse(payload)
        emoji_id = message.emoji_id
        user = message.user
        common = message.common
        default_content = message.default_content
        print(f"【聊天表情包id】 {emoji_id},user：{user},common:{common},default_content:{default_content}")

    def _parseRoomMsg(self, payload):
        message = RoomMessage().parse(payload)
        common = message.common
        room_id = common.room_id
        print(f"【直播间msg】直播间id:{room_id}")

    def _parseRoomStatsMsg(self, payload):
        message = RoomStatsMessage().parse(payload)
        display_long = message.display_long
        print(f"【直播间统计msg】{display_long}")

    def _parseRankMsg(self, payload):
        message = RoomRankMessage().parse(payload)
        ranks_list = message.ranks_list
        print(f"【直播间排行榜msg】{ranks_list}")

    def _parseControlMsg(self, payload):
        '''直播间状态消息'''
        message = ControlMessage().parse(payload)

        if message.status == 3:
            print("直播间已结束")
            self.stop()
