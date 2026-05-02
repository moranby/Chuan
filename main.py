import asyncio
import re
from datetime import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain, Image
from .api_client import MiniWorldApiClient

@register("miniworld", "HuanSui", "迷你世界权威查询 · 用户资料、地图列表一键获取", "2.1.0")
class MiniWorldPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api = MiniWorldApiClient()

    async def initialize(self):
        logger.info("[MiniWorld] 幻邃智能 · HuanSui AI 迷你世界查询引擎启动")

    # ── UID 提取工具：支持无空格、多个别名 ──
    def _extract_uid(self, event: AstrMessageEvent, aliases: list):
        """从消息中提取迷你号，支持有/无斜杠，有/无空格"""
        text = event.message_str.strip()
        if text.startswith('/'):
            text = text[1:]
        text_lower = text.lower()
        for alias in aliases:
            alias_lower = alias.lower()
            if text_lower.startswith(alias_lower):
                rest = text[len(alias):].strip()
                if not rest:
                    return None
                # 提取第一串连续数字作为迷你号
                match = re.search(r'\d+', rest)
                if match:
                    return match.group()
                return None
        return None

    # ── 资料查询核心逻辑 ──
    async def _fetch_profile_data(self, uid: str):
        """返回用户档案文本，失败时返回错误提示"""
        try:
            profile_data, maps_data = await asyncio.gather(
                self.api.get_user_profile(uid),
                self.api.get_user_maps(uid),
                return_exceptions=True
            )
            if isinstance(profile_data, Exception) or profile_data.get("code") != 0:
                return "❌ 用户不存在或资料接口异常，请检查迷你号。"

            user = profile_data["data"]

            # 用真实地图列表修正统计（如果地图接口成功）
            maps_ok = False
            total_maps = 0
            total_dl = 0
            total_like = 0
            if isinstance(maps_data, dict) and maps_data.get("status") == "success":
                maps_ok = True
                maps_list = maps_data.get("maps", [])
                total_maps = len(maps_list)
                total_dl = sum(m.get("download_count", 0) for m in maps_list)
                total_like = sum(m.get("like", 0) for m in maps_list)

        except Exception as e:
            logger.error(f"[MiniWorld] 查询聚合失败: {e}")
            return "⚠️ 查询服务暂时不可用，请稍后重试"

        def ts2str(ts):
            try:
                return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
            except:
                return str(ts) if ts else "未知"

        def fmt(n):
            try:
                return f"{int(n):,}"
            except:
                return str(n)

        map_count = total_maps if maps_ok else user.get('map_total_count', 0)
        map_dl = total_dl if maps_ok else user.get('map_download_count', 0)
        map_like = total_like if maps_ok else user.get('map_like_count', 0)
        map_visit = user.get('map_visit_count', 0)

        msg = (
            f"📇 迷你世界用户档案\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 迷你号：{user.get('uin', uid)}\n"
            f"👤 昵称：{user.get('name', '未知')}\n"
            f"⭐ 等级：{user.get('level', 0)}\n"
            f"⚧ 性别：{user.get('gender', '未知')}\n"
            f"📅 注册时间：{ts2str(user.get('create_time'))}\n"
            f"🕒 最后登录：{ts2str(user.get('last_login_time'))}\n"
            f"💬 个性签名：{user.get('mood_text', '这个人很懒，什么都没留下')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👥 社交数据\n"
            f"  好友：{fmt(user.get('friend_num',0))}  "
            f"关注：{fmt(user.get('follow_num',0))}  "
            f"粉丝：{fmt(user.get('fans_num',0))}\n"
            f"  待处理申请：{fmt(user.get('friend_beapply',0))}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🗺️ 创作数据 {'(实时)' if maps_ok else ''}\n"
            f"  地图总数：{fmt(map_count)}\n"
            f"  总下载量：{fmt(map_dl)}\n"
            f"  总获赞：{fmt(map_like)}\n"
            f"  地图访问量：{fmt(map_visit)}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎨 其他信息\n"
            f"  头像框数量：{fmt(user.get('avatar_frame_count',0))}\n"
            f"  人气值：{fmt(user.get('popularity',0))}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ 幻邃智能 · HuanSui AI"
        )
        return msg

    # ── 指令：/查询 (及所有别名) ──
    @filter.command("查询", aliases=["cx", "chaxun", "查询迷你号", "迷你号查询", "query", "user", "profile"])
    async def query_profile(self, event: AstrMessageEvent):
        """查询迷你世界用户完整资料"""
        aliases = ["查询", "cx", "chaxun", "查询迷你号", "迷你号查询", "query", "user", "profile"]
        uid = self._extract_uid(event, aliases)
        if not uid:
            yield event.plain_result("❌ 请提供迷你号，例如：查询 123456")
            return

        msg = await self._fetch_profile_data(uid)
        if msg.startswith("📇"):
            # 成功时尝试发送头像
            try:
                profile = await self.api.get_user_profile(uid)
                avatar = profile.get("data", {}).get("avatar", "")
                if avatar:
                    yield event.chain_result([Image.fromURL(avatar), Plain(msg)])
                    return
            except:
                pass
        yield event.plain_result(msg)

    # ── 指令：/查询地图 (及所有别名) ──
    @filter.command("查询地图", aliases=["地图查询", "map", "maps", "cxmap", "mini地图"])
    async def query_maps(self, event: AstrMessageEvent):
        """查询用户发布的地图列表"""
        aliases = ["查询地图", "地图查询", "map", "maps", "cxmap", "mini地图"]
        uid = self._extract_uid(event, aliases)
        if not uid:
            yield event.plain_result("❌ 请提供迷你号，例如：查询地图 123456")
            return

        try:
            data = await self.api.get_user_maps(uid)
            if data.get("status") != "success":
                yield event.plain_result(f"❌ 地图数据获取失败：{data.get('message', '接口错误')}")
                return
            maps = data.get("maps", [])
        except Exception as e:
            logger.error(f"[MiniWorld] 地图查询失败: {e}")
            yield event.plain_result("⚠️ 地图查询服务暂时不可用，请稍后重试")
            return

        if not maps:
            yield event.plain_result("📭 该用户尚未发布任何地图")
            return

        limit = min(len(maps), 10)
        lines = [f"🗺️ 地图统计 (共 {len(maps)} 个，显示前 {limit} 个)"]
        for i, m in enumerate(maps[:limit], 1):
            name = m.get('name', '未知')
            season = m.get('season', '').strip()
            if not season:
                season = "未知赛季"
            lines.append(
                f"\n{i}. {name}  [{season}]\n"
                f"   📥 下载：{m.get('download_count',0)}  "
                f"👍 点赞：{m.get('like',0)}  👎 踩：{m.get('dislike',0)}\n"
                f"   📅 创建：{m.get('create_time','未知')}  "
                f"💾 大小：{m.get('size','未知')}"
            )
        lines.append("\n━━━━━━━━━━━━━━━━━━\n⚡ 幻邃智能 · HuanSui AI")
        yield event.plain_result("".join(lines))

    async def terminate(self):
        logger.info("[MiniWorld] 幻邃智能查询引擎已停止")