import aiohttp
import re
from datetime import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain, Image

@register("miniworld", "HuanSui", "迷你世界全息查询引擎丨幻邃智能", "3.0.0")
class MiniWorldPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api = "https://moran.sylu.net/api"

    async def initialize(self):
        logger.info("[MiniWorld] 幻邃智能 · 全息查询引擎已启动")

    # ── 工具方法 ──
    def _uid(self, text: str) -> str:
        """从消息中提取迷你号：取最后一个连续数字"""
        match = re.findall(r'\d+', text)
        return match[-1] if match else ""

    @staticmethod
    def fmt_n(n):
        try: return f"{int(n):,}"
        except: return str(n)

    @staticmethod
    def ts2str(ts):
        try: return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
        except: return str(ts) if ts else "未知"

    async def _get_json(self, url: str) -> dict:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()

    # ── 指令：菜单 ──
    @filter.command("菜单")
    async def show_menu(self, event: AstrMessageEvent):
        menu = (
            "📋 迷你世界查询菜单 · 幻邃智能\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "/菜单 · 查看本列表\n"
            "/查询 <迷你号> · 全息档案\n"
            "/资料 <迷你号> · 基础资料\n"
            "/资料2 <迷你号> · 详细资料\n"
            "/地图 <迷你号> · 地图列表\n"
            "/追踪 <迷你号> · 在线状态\n"
            "/礼物 <迷你号> · 礼物背包\n"
            "/IP <迷你号> · 定位信息\n"
            "/家族 <迷你号> · 家族详情\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚡ 幻邃智能 · HuanSui AI"
        )
        yield event.plain_result(menu)

    # ── 指令：/查询 (全量) ──
    @filter.command("查询", aliases=["cx"])
    async def query_all(self, event: AstrMessageEvent):
        uid = self._uid(event.message_str)
        if not uid: yield event.plain_result("❌ 请提供迷你号"); return
        data = await self._get_json(f"{self.api}/aggregate.php?uin={uid}")
        if data.get("code") != 0:
            yield event.plain_result("❌ 查询失败")
            return
        d = data["data"]

        # 合并字段，优先 detail
        basic = d.get("profile_basic", {})
        detail = d.get("profile_detail", {})
        maps = d.get("maps")
        gifts = d.get("gifts", {})
        track = d.get("track")
        family = d.get("family")
        ip_info = d.get("ip")

        def getv(*keys, default="未知"):
            for k in keys:
                if k in detail: return detail[k]
            for k in keys:
                if k in basic: return basic[k]
            return default

        nick = getv("nickname", "name")
        uin_field = getv("uin", default=uid)
        level = getv("level", default=0)
        gender = getv("gender", default="未知")
        country = detail.get("country", "未知")
        ip = detail.get("IP", "未知") if detail else (ip_info.get("IP") if ip_info else "未知")
        is_vip = detail.get("VIP", False) if detail else (basic.get("vip_type", 0) > 0)
        developer = getv("developerLevel", "creator_level", default=0)
        popularity = getv("popularity", default=0)
        last_login = getv("last_login_time")
        register = getv("regist_account_time", "create_time")
        mood = basic.get("mood_text", "无") if basic else "无"
        friends = getv("friends", "friend_num", default=0)
        following = getv("following", "follow_num", default=0)
        fans = getv("fans", "fans_num", default=0)
        beapply = basic.get("friend_beapply", 0) if basic else 0  # 好友申请
        credit = getv("creditScore", default="--")
        charm = getv("charmValue", default=0)
        cube = getv("cubeValue", "tips_total", default=0)
        thumbs = getv("thumbs_up", default=0)
        works = getv("createdWorks", default=0)
        skins = getv("skinsCount", default=0)
        mounts = getv("mountsCount", "mounts_count", default=0)
        weapons = getv("weaponsCount", default=0)
        titles = getv("titlesCount", default=0)
        medals = getv("medalsCount", default=0)
        posts = getv("postsCount", default=0)
        avatar_frames = getv("headframesCount", "avatar_frame_count", default=0)
        vip_end = getv("vip_end_time", default="")

        # 地图统计
        maps_list = maps.get("maps", []) if maps else []
        map_count = len(maps_list)
        map_dl = sum(m.get("download_count", 0) for m in maps_list)
        map_like = sum(m.get("like", 0) for m in maps_list)
        if map_count == 0:
            map_count = basic.get("map_total_count", 0) or 0
            map_dl = basic.get("map_download_count", 0) or 0
            map_like = basic.get("map_like_count", 0) or 0

        # 礼物统计
        glist = gifts.get("gift_list", []) if gifts else []
        gift_total = sum(g.get("num", 0) for g in glist)

        # 家族信息
        family_str = ""
        if family:
            fm = family
            family_str = (
                f"🏠 家族：{fm.get('name','')} Lv.{fm.get('level','--')}\n"
                f"  介绍：{fm.get('desc','')}\n"
                f"  成员：{fm.get('member_count','')} | 活跃：{self.fmt_n(fm.get('active_val','0'))} | 地图：{self.fmt_n(fm.get('map_cnt','0'))}\n"
            )

        # 追踪信息
        track_str = ""
        if track:
            tr = track
            track_str = (
                f"📍 房间ID：{tr.get('roomId','--')} | {tr.get('num',0)}/{tr.get('cap',0)}人\n"
                f"🌐 IP：{tr.get('ip','--')} | {'🔒私有' if tr.get('private') else '🌍公开'}\n"
            )

        msg = (
            f"📇 迷你世界全息档案\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 迷你号：{uin_field}\n"
            f"👤 昵称：{nick}{'  👑VIP' if is_vip else ''}\n"
            f"⭐ 等级：{level} | ⚧ {gender}\n"
            f"🌍 地区：{country} | IP：{ip}\n"
            f"📅 注册：{self.ts2str(register)}\n"
            f"🕒 最近在线：{self.ts2str(last_login)}\n"
            f"💬 签名：{mood}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👥 社交与声望\n"
            f"  好友：{self.fmt_n(friends)}  关注：{self.fmt_n(following)}  粉丝：{self.fmt_n(fans)}\n"
            f"  待处理申请：{self.fmt_n(beapply)}\n"
            f"  信誉分：{credit} | 人气：{self.fmt_n(popularity)}\n"
            f"  魅力值：{self.fmt_n(charm)}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🛠 开发者等级：Lv.{developer}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🗺️ 创作统计\n"
            f"  地图：{map_count}个 | 下载：{self.fmt_n(map_dl)} | 赞：{self.fmt_n(map_like)}\n"
            f"  作品创建：{self.fmt_n(works)} | 收到点赞：{self.fmt_n(thumbs)}\n"
            f"  皮肤：{self.fmt_n(skins)} | 坐骑：{self.fmt_n(mounts)}\n"
            f"  武器：{self.fmt_n(weapons)} | 称号：{self.fmt_n(titles)}\n"
            f"  头像框：{self.fmt_n(avatar_frames)} | 勋章：{self.fmt_n(medals)} | 帖子：{self.fmt_n(posts)}\n"
            f"  方块总值：{self.fmt_n(cube)}\n"
        )
        if vip_end and vip_end != "未知":
            msg += f"👑 VIP到期：{self.ts2str(vip_end)}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"
        if family_str:
            msg += f"{family_str}━━━━━━━━━━━━━━━━━━\n"
        msg += f"🎁 礼物：{len(glist)}种 {gift_total}个\n"
        if track_str:
            msg += f"━━━━━━━━━━━━━━━━━━\n🔍 在线追踪\n{track_str}"
        msg += "━━━━━━━━━━━━━━━━━━\n⚡ 幻邃智能 · HuanSui AI"

        # 头像
        avatar = basic.get("avatar") if basic else None
        if not avatar and uin_field:
            avatar = f"https://api.4001314.xyz/mnw1/rest/v1/relicons/{uin_field}.png"
        if avatar:
            try:
                yield event.chain_result([Image.fromURL(avatar), Plain(msg)])
            except:
                yield event.plain_result(msg)
        else:
            yield event.plain_result(msg)

    # ── 指令：/资料  /资料2  /地图  /追踪  /礼物  /IP  /家族 ──
    @filter.command("资料")
    async def query_basic(self, event: AstrMessageEvent):
        uid = self._uid(event.message_str)
        if not uid: yield event.plain_result("❌ 请提供迷你号"); return
        d = await self._get_json(f"{self.api}/mini_cha.php?uin={uid}")
        if d.get("code") != 0: yield event.plain_result("❌ 查询失败"); return
        u = d["data"]
        msg = (
            f"📇 基础资料\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 迷你号：{u.get('uin',uid)}\n"
            f"👤 昵称：{u.get('name','未知')}\n"
            f"⭐ 等级：{u.get('level',0)} | ⚧ {u.get('gender','未知')}\n"
            f"💬 签名：{u.get('mood_text','无')}\n"
            f"🕒 最后登录：{self.ts2str(u.get('last_login_time'))}\n"
            f"👥 好友：{u.get('friend_num',0)} | 关注：{u.get('follow_num',0)} | 粉丝：{u.get('fans_num',0)}\n"
            f"📥 待处理申请：{u.get('friend_beapply',0)}\n"
            f"🗺️ 下载量：{self.fmt_n(u.get('map_download_count',0))}\n"
            f"━━━━━━━━━━━━━━━━━━\n⚡ 幻邃智能 · HuanSui AI"
        )
        yield event.plain_result(msg)

    @filter.command("资料2")
    async def query_detail(self, event: AstrMessageEvent):
        uid = self._uid(event.message_str)
        if not uid: yield event.plain_result("❌ 请提供迷你号"); return
        d = await self._get_json(f"{self.api}/profile_v2.php?uin={uid}")
        if d.get("code") != 0: yield event.plain_result("❌ 查询失败"); return
        u = d["data"]
        msg = (
            f"📇 详细资料\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 迷你号：{u.get('uin',uid)}\n"
            f"👤 昵称：{u.get('nickname','未知')}{' 👑VIP' if u.get('VIP') else ''}\n"
            f"🌍 地区：{u.get('country','未知')} | IP：{u.get('IP','未知')}\n"
            f"⭐ 等级：{u.get('level',0)} | 开发者：Lv.{u.get('developerLevel',0)}\n"
            f"📅 注册：{u.get('regist_account_time','')}\n"
            f"🕒 最后登录：{u.get('last_login_time','')}\n"
            f"👑 VIP到期：{self.ts2str(u.get('vip_end_time'))}\n"
            f"👥 好友：{u.get('friends',0)} | 关注：{u.get('following',0)} | 粉丝：{u.get('fans',0)}\n"
            f"💎 信誉分：{u.get('creditScore','--')} | 魅力：{self.fmt_n(u.get('charmValue',0))}\n"
            f"📦 方块总值：{self.fmt_n(u.get('cubeValue',0))}\n"
            f"🎨 皮肤：{u.get('skinsCount',0)} | 坐骑：{u.get('mountsCount',0)}\n"
            f"⚔️ 武器：{u.get('weaponsCount',0)} | 称号：{u.get('titlesCount',0)}\n"
            f"🎖️ 勋章：{u.get('medalsCount',0)} | 帖子：{u.get('postsCount',0)}\n"
            f"🖼️ 头像框：{u.get('headframesCount',0)} | 作品：{u.get('createdWorks',0)}\n"
            f"❤️ 被赞：{self.fmt_n(u.get('thumbs_up',0))}\n"
            f"🏠 家族：{u.get('family',{}).get('name','未加入')}\n"
            f"━━━━━━━━━━━━━━━━━━\n⚡ 幻邃智能 · HuanSui AI"
        )
        yield event.plain_result(msg)

    @filter.command("地图", aliases=["查询地图", "地图查询"])
    async def query_maps(self, event: AstrMessageEvent):
        uid = self._uid(event.message_str)
        if not uid: yield event.plain_result("❌ 请提供迷你号"); return
        d = await self._get_json(f"{self.api}/map_api.php?user_id={uid}")
        if d.get("status") != "success": yield event.plain_result("❌ 地图查询失败"); return
        maps = d.get("maps", [])
        if not maps: yield event.plain_result("📭 无地图"); return
        msg = f"🗺️ 地图列表 (共{len(maps)}个，显示前5)\n"
        for m in maps[:5]:
            season = m.get("season", "").strip() or "未知赛季"
            msg += (
                f"• {m.get('name','未知')} [{season}]\n"
                f"  📥{m.get('download_count',0)} 👍{m.get('like',0)} 👎{m.get('dislike',0)}\n"
            )
        msg += "━━━━━━━━━━━━━━━━━━\n⚡ 幻邃智能 · HuanSui AI"
        yield event.plain_result(msg)

    @filter.command("追踪")
    async def query_track(self, event: AstrMessageEvent):
        uid = self._uid(event.message_str)
        if not uid: yield event.plain_result("❌ 请提供迷你号"); return
        d = await self._get_json(f"{self.api}/track.php?uin={uid}")
        if d.get("code") != 0: yield event.plain_result("❌ 追踪失败"); return
        tr = d["data"]
        msg = (
            f"📍 在线追踪\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"房间ID：{tr.get('roomId','--')} | {tr.get('num',0)}/{tr.get('cap',0)}人\n"
            f"IP：{tr.get('ip','--')} | {'🔒私有' if tr.get('private') else '🌍公开'}\n"
            f"地图：{tr.get('mapName','无')}\n"
            f"━━━━━━━━━━━━━━━━━━\n⚡ 幻邃智能 · HuanSui AI"
        )
        yield event.plain_result(msg)

    @filter.command("礼物")
    async def query_gifts(self, event: AstrMessageEvent):
        uid = self._uid(event.message_str)
        if not uid: yield event.plain_result("❌ 请提供迷你号"); return
        d = await self._get_json(f"{self.api}/gifts.php?uin={uid}")
        if d.get("code") != 0: yield event.plain_result("❌ 礼物查询失败"); return
        glist = d["data"].get("gift_list", [])
        total = sum(g.get("num",0) for g in glist)
        msg = f"🎁 礼物列表 (共{len(glist)}种 {total}个)\n"
        for g in glist:
            msg += f"  {g.get('name','?')} x{g.get('num',0)}\n"
        msg += "━━━━━━━━━━━━━━━━━━\n⚡ 幻邃智能 · HuanSui AI"
        yield event.plain_result(msg)

    @filter.command("IP")
    async def query_ip(self, event: AstrMessageEvent):
        uid = self._uid(event.message_str)
        if not uid: yield event.plain_result("❌ 请提供迷你号"); return
        d = await self._get_json(f"{self.api}/ip.php?uin={uid}")
        if d.get("code") != 0: yield event.plain_result("❌ 查询失败"); return
        ipd = d["data"]
        msg = (
            f"🌍 IP 信息\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"国家：{ipd.get('country','未知')}\n"
            f"IP：{ipd.get('IP','未知')}\n"
            f"━━━━━━━━━━━━━━━━━━\n⚡ 幻邃智能 · HuanSui AI"
        )
        yield event.plain_result(msg)

    @filter.command("家族")
    async def query_family(self, event: AstrMessageEvent):
        uid = self._uid(event.message_str)
        if not uid: yield event.plain_result("❌ 请提供迷你号"); return
        d = await self._get_json(f"{self.api}/family.php?uin={uid}")
        if d.get("code") != 0: yield event.plain_result("❌ 未加入家族或查询失败"); return
        f = d["data"]
        msg = (
            f"🏠 家族信息\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"名称：{f.get('name','')}\n"
            f"等级：Lv.{f.get('level','--')}\n"
            f"介绍：{f.get('desc','')}\n"
            f"成员：{f.get('member_count','')}\n"
            f"活跃：{self.fmt_n(f.get('active_val','0'))}\n"
            f"地图：{self.fmt_n(f.get('map_cnt','0'))}\n"
            f"━━━━━━━━━━━━━━━━━━\n⚡ 幻邃智能 · HuanSui AI"
        )
        yield event.plain_result(msg)

    async def terminate(self):
        logger.info("[MiniWorld] 幻邃智能 引擎已关闭")