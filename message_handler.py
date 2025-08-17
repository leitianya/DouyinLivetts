# message_handler.py
from protobuf.douyin import (
    ChatMessage, GiftMessage, LikeMessage, MemberMessage, SocialMessage,
    RoomUserSeqMessage, FansclubMessage, ControlMessage, EmojiChatMessage,
    RoomMessage, RoomStatsMessage, RoomRankMessage
)
from logger import log

class MessageHandler:
    def __init__(self, tts_manager, gui_update_callback):
        self.tts_manager = tts_manager
        self.gui_update_callback = gui_update_callback
        self.speech_enabled = False
        self.gift_enabled = False
        self.follow_enabled = False
        self.welcome_enabled = False
        self.message_handlers = {
            'WebcastChatMessage': self._parse_chat_msg,
            'WebcastGiftMessage': self._parse_gift_msg,
            'WebcastLikeMessage': self._parse_like_msg,
            'WebcastMemberMessage': self._parse_member_msg,
            'WebcastSocialMessage': self._parse_social_msg,
            'WebcastRoomUserSeqMessage': self._parse_room_user_seq_msg,
            'WebcastFansclubMessage': self._parse_fansclub_msg,
            'WebcastControlMessage': self._parse_control_msg,
            'WebcastEmojiChatMessage': self._parse_emoji_chat_msg,
            'WebcastRoomMessage': self._parse_room_msg,
            'WebcastRoomStatsMessage': self._parse_room_stats_msg,
            'WebcastRoomRankMessage': self._parse_rank_msg,
        }

    def handle_message(self, method, payload):
        handler = self.message_handlers.get(method)
        if handler:
            try:
                handler(payload)
            except Exception as e:
                log.error(f"Error handling message {method}: {e}")

    def _parse_chat_msg(self, payload):
        message = ChatMessage().parse(payload)
        user_name = message.user.nick_name
        content = message.content
        log.info(f"【聊天】{user_name}: {content}")
        if self.speech_enabled:
            text = f"{user_name}说：{content}。"
            self.tts_manager.add_task(text, 0)

    def _parse_gift_msg(self, payload):
        message = GiftMessage().parse(payload)
        user_name = message.user.nick_name
        gift_name = message.gift.name
        log.info(f"【礼物】{user_name} 送出 {gift_name}")
        if self.gift_enabled:
            text = f"感谢 {user_name} 送出的 {gift_name}！"
            self.tts_manager.add_task(text, 1)

    def _parse_like_msg(self, payload):
        message = LikeMessage().parse(payload)
        user_name = message.user.nick_name
        count = message.count
        log.info(f"【点赞】{user_name} 点赞了 {count} 次")

    def _parse_member_msg(self, payload):
        message = MemberMessage().parse(payload)
        user_name = message.user.nick_name
        log.info(f"【成员】{user_name} 进入直播间！")
        if self.welcome_enabled:
            text = f"欢迎 {user_name} 进入直播间！"
            self.tts_manager.add_task(text, 1)

    def _parse_social_msg(self, payload):
        message = SocialMessage().parse(payload)
        user_name = message.user.nick_name
        log.info(f"【社交】{user_name} 关注了主播！")
        if self.follow_enabled:
            text = f"感谢 {user_name} 关注主播！"
            self.tts_manager.add_task(text, 3)

    def _parse_room_user_seq_msg(self, payload):
        message = RoomUserSeqMessage().parse(payload)
        current = message.total
        self.gui_update_callback(current)
        log.info(f"【统计】当前观众: {current}")

    def _parse_fansclub_msg(self, payload):
        message = FansclubMessage().parse(payload)
        log.info(f"【粉丝团】{message.content}")

    def _parse_control_msg(self, payload):
        message = ControlMessage().parse(payload)
        if message.status == 3:
            log.info("直播间已结束。")
            # Here you might want to signal the main controller to stop everything.

    def _parse_emoji_chat_msg(self, payload):
        message = EmojiChatMessage().parse(payload)
        log.info(f"【表情】{message.user.nick_name} 发送了一个表情。")

    def _parse_room_msg(self, payload):
        message = RoomMessage().parse(payload)
        log.info(f"【房间】房间消息: {message.common.room_id}")

    def _parse_room_stats_msg(self, payload):
        message = RoomStatsMessage().parse(payload)
        log.info(f"【房间统计】{message.display_long}")

    def _parse_rank_msg(self, payload):
        message = RoomRankMessage().parse(payload)
        log.info(f"【排行】收到排行消息。")
