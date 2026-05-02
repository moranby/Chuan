import asyncio
import re
from datetime import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain, Image
from .api_client import MiniWorldApiClient

@register("miniworld", "Chuan", "迷你世界权威查询 · 用户资料、地图列表一键获取", "2.0.0", "https://github.com/moranby/Chuan")
class MiniWorldPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api = MiniWorldApiClient()

    async def initialize(self):
        logger.info("[Chuan] 迷你世界查询引擎启动 | moranby/Chuan")

    def _parse_input(self, msg: str, cmd_aliases: list):
        """从消息中提取指令词和迷你号，支持无空格输入"""
        msg = msg.strip()
        parts = msg.split()
        if len(parts) >= 2:
            cmd = parts[0]
            uid = parts[1]
            return cmd, uid
        match = re.match(r'^(.*?)(\d+)$', msg)
        if match:
            cmd = match.group(1).strip()
            uid = match.group(2).strip()
            if cmd in cmd_aliases:
                return cmd, uid
        return msg, None

    # ── 指令：/查询 (多别名) ──
    @filter.command("查询")
    @filter.command("cx")
    @filter.command("查询用户")
    @filter.command("查询迷你号")
    @filter.command("迷你号查询")
    @filter.command("用户查询")
    async def query_profile(self, event: AstrMessageEvent):
        cmd_aliases = ["查询", "cx", "查询用户", "查询迷你号", "迷你号查询", "用户查询"]
        cmd, uid = self._parse_input(event.message_str, cmd_aliases)

        if not uid:
            yield event.plain_result("❌ 请提供迷你号，格式：/查询 123456")
            return

        try:
            profile_data, maps_data = await asyncio.gather(
                self.api.get_user_profile(uid),
                self.api.get_user_maps(uid),
                return_exceptions=True
            )
            if isinstance(profile_data, Exception) or profile_data.get("code") != 0:
                yield event.plain_result("❌ 用户不存在或资料接口异常，请检查迷你号。")
                return
            user = profile_data["data"]

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
            logger.error(f"[Chuan] 查询聚合失败: {e}")
            yield event.plain_result("⚠️ 查询服务暂时不可用，请稍后重试")
            return

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

        map_count = total_maps if maps_ok else user.get("map_total_count", 0)
        map_dl = total_dl if maps_ok else user.get("map_download_count", 0)
        map_like = total_like if maps_ok else user.get("map_like_count", 0)
        map_visit = user.get("map_visit_count", 0)

        # 修正：将多行 f-string 拆分为独立行，避免跨行引号闭合错误
        line1 = f"📇 迷你世界用户档案\n"
        line2 = f"━━━━━━━━━━━━━━━━━━\n"
        line3 = f"🆔 迷你号：{user.get('uin', uid)}\n"
        line4 = f"👤 昵称：{user.get('name', '未知')}\n"
        line5 = f"⭐ 等级：{user.get('level', 0)}\n"
        line6 = f"⚧ 性别：{user.get('gender', '未知')}\n"
        line7 = f"📅 注册时间：{ts2str(user.get('create_time'))}\n"
        line8 = f"🕒 最后登录：{ts2str(user.get('last_login_time'))}\n"
        line9 = f"💬 个性签名：{user.get('mood_text', '这个人很懒，什么都没留下')}\n"
        line10 = f"━━━━━━━━━━━━━━━━━━\n"
        line11 = f"👥 社交数据\n"
        line12 = f"  好友：{fmt(user.get('friend_num',0))}  关注：{fmt(user.get('follow_num',0))}  粉丝：{fmt(user.get('fans_num',0))}\n"
        line13 = f"  待处理申请：{fmt(user.get('friend_beapply',0))}\n"
        line14 = f"━━━━━━━━━━━━━━━━━━\n"
        line15 = f"🗺️ 创作数据 {'(实时统计)' if maps_ok else ''}\n"
        line16 = f"  地图总数：{fmt(map_count)}\n"
        line17 = f"  总下载量：{fmt(map_dl)}\n"
        line18 = f"  总获赞：{fmt(map_like)}\n"
        line19 = f"  地图访问量：{fmt(map_visit)}\n"
        line20 = f"━━━━━━━━━━━━━━━━━━\n"
        line21 = f"🎨 其他信息\n"
        line22 = f"  头像框数量：{fmt(user.get('avatar_frame_count',0))}\n"
        line23 = f"  人气值：{fmt(user.get('popularity',0))}\n"
        line24 = f"━━━━━━━━━━━━━━━━━━\n"
        line25 = f"⚡ 查询引擎：Chuan | github.com/moranby/Chuan"

        msg = (line1 + line2 + line3 + line4 + line5 + line6 + line7 + line8 + line9 +
               line10 + line11 + line12 + line13 + line14 + line15 + line16 + line17 +
               line18 + line19 + line20 + line21 + line22 + line23 + line24 + line25)

        avatar = user.get("avatar", "")
        if avatar:
            yield event.chain_result([Image.fromURL(avatar), Plain(msg)])
        else:
            yield event.plain_result(msg)

    # ── 指令：/查询地图 (多别名) ──
    @filter.command("查询地图")
    @filter.command("地图查询")
    @filter.command("cx地图")
    @filter.command("cxmap")
    @filter.command("map")
    async def query_maps(self, event: AstrMessageEvent):
        cmd_aliases = ["查询地图", "地图查询", "cx地图", "cxmap", "map"]
        cmd, uid = self._parse_input(event.message_str, cmd_aliases)

        if not uid:
            yield event.plain_result("❌ 请提供迷你号，格式：/查询地图 123456")
            return

        try:
            data = await self.api.get_user_maps(uid)
            if data.get("status") != "success":
                yield event.plain_result(f"❌ 地图数据获取失败：{data.get('message', '接口错误')}")
                return
            maps = data.get("maps", [])
        except Exception as e:
            logger.error(f"[Chuan] 地图查询失败: {e}")
            yield event.plain_result("⚠️ 地图查询服务暂时不可用，请稍后重试")
            return

        if not maps:
            yield event.plain_result("📭 该用户尚未发布任何地图")
            return

        limit = min(len(maps), 10)
        lines = [f"🗺️ 地图统计 (共 {len(maps)} 个，显示前 {limit} 个)"]
        for i, m in enumerate(maps[:limit], 1):
            season_str = f"  [赛季:{m.get('season')}]" if m.get('season') else ""
            lines.append(
                f"\n{i}. {m.get('name', '未知')}{season_str}\n"
                f"   📥 下载：{m.get('download_count',0)}  👍 点赞：{m.get('like',0)}  👎 踩：{m.get('dislike',0)}\n"
                f"   📅 创建：{m.get('create_time','未知')}  💾 大小：{m.get('size','未知')}"
            )
        lines.append("\n━━━━━━━━━━━━━━━━━━\n⚡ 查询引擎：Chuan | github.com/moranby/Chuan")
        yield event.plain_result("".join(lines))

    async def terminate(self):
        logger.info("[Chuan] 查询引擎已停止 | moranby/Chuan")