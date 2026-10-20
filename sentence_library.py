"""句库：总部审核一次的成句素材，快发模式按人群与平台组合。"""
from __future__ import annotations

import re
import unicodedata

from facts import SLOT_ALIASES
from policy import BANNED, DYNAMIC

PLATFORMS = ("小红书", "门店朋友圈", "微信公众号")
AUDIENCES = ("学生", "教师", "商务差旅", "内容创作", "管理者", "企业采购", "旧机换新")
# 第一期先做满前三类人群（学生 / 教师 / 商务差旅）；其余四类先各给少量通用片段，后续补齐。

KINDS = ("hook", "scene", "benefit", "evidence", "store", "ending", "tag")

FRAGMENT_KEYS = frozenset({"id", "kind", "text", "slots", "audiences", "platforms", "weight"})

# 片段长度上限（按模板原文字数计，槽位占位符也算在内）。
LENGTH_LIMITS = {"hook": 30, "scene": 50, "benefit": 45,
                 "evidence": 55, "store": 40, "ending": 30, "tag": 12}

# 最低数量：键是 (类型, 人群)，人群写 "总计" 表示该类型总数，"通用" 表示不带人群标签的片段。
MINIMUMS = {
    ("hook", "学生"): 8, ("hook", "教师"): 8, ("hook", "商务差旅"): 8,
    ("scene", "学生"): 8, ("scene", "教师"): 8, ("scene", "商务差旅"): 8,
    ("benefit", "总计"): 36, ("benefit", "通用"): 4,
    ("benefit", "学生"): 6, ("benefit", "教师"): 6, ("benefit", "商务差旅"): 6,
    ("evidence", "总计"): 18,
    ("store", "总计"): 8,
    ("ending", "总计"): 10,
    ("tag", "学生"): 8, ("tag", "教师"): 8, ("tag", "商务差旅"): 8,
}

# 去 AI 味：总部统一禁用的套话，命中即整句不合格。
BANNED_PHRASES = (
    "在这个快节奏的时代", "快节奏的时代", "内卷的时代", "时代变了",
    "赋能", "助力", "打造", "引领", "重塑", "颠覆",
    "小伙伴们", "宝子们", "家人们", "朋友们冲",
    "不仅", "堪称", "极致", "天花板", "封神", "绝绝子", "yyds", "狠狠",
    "为你而生", "匠心", "重磅", "焕新", "解锁", "满分", "懂的都懂", "值得拥有",
    "不二之选", "首选", "闭眼", "顶级", "第一", "唯一", "绝对", "保证",
)

SLOT_PATTERN = re.compile(r"\{([^{}]*)\}")


FRAGMENTS: tuple[dict, ...] = (
    # ---------------------------------------------------------------- hook：学生
    {"id": "hook-学生-01", "kind": "hook",
     "text": "开学前一周，宿舍里问得最多的就是这台能不能跑专业软件。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 3},
    {"id": "hook-学生-02", "kind": "hook",
     "text": "新生群里刷屏的同一个问题：作业要用的软件装得上吗。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "hook-学生-03", "kind": "hook",
     "text": "晚自习回来，室友把电脑往床上一放，说这台真不沉。",
     "slots": (), "audiences": ("学生",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-学生-04", "kind": "hook",
     "text": "大一新生在店里坐了很久，问的都是能不能用到毕业。",
     "slots": (), "audiences": ("学生",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-学生-05", "kind": "hook",
     "text": "图书馆占座那天，桌上摊开的电脑都开着好几个文档和网页。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "hook-学生-06", "kind": "hook",
     "text": "期末周自习室的插座位不够用，续航就成了绕不开的话题。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "hook-学生-07", "kind": "hook",
     "text": "今天来了位大一新生，开口就问能不能装工程制图软件。",
     "slots": (), "audiences": ("学生",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-学生-08", "kind": "hook",
     "text": "选课那几天宿舍网卡，几个人围着屏幕逐个比参数。",
     "slots": (), "audiences": ("学生",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "hook-学生-09", "kind": "hook",
     "text": "开学清单里电脑那一栏最难填，因为专业不同要求差得远。",
     "slots": (), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 2},
    {"id": "hook-学生-10", "kind": "hook",
     "text": "同样写着轻薄，装进书包后的差别要去店里试过才知道。",
     "slots": (), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-学生-11", "kind": "hook",
     "text": "宿舍里几个人的电脑摆在桌上，厚度差别一眼就看得出。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 1},
    {"id": "hook-学生-12", "kind": "hook",
     "text": "同一门课，装不装得上软件，比跑分更影响上课体验。",
     "slots": (), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    # ---------------------------------------------------------------- hook：教师
    {"id": "hook-教师-01", "kind": "hook",
     "text": "开学前备课，老师问得最多的是课件和录课软件能不能装。",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 3},
    {"id": "hook-教师-02", "kind": "hook",
     "text": "教研室换电脑，先在纸上列了必装软件，再去看机器。",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 2},
    {"id": "hook-教师-03", "kind": "hook",
     "text": "一位带毕业班的老师到店，只关心投影切换顺不顺。",
     "slots": (), "audiences": ("教师",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-教师-04", "kind": "hook",
     "text": "今天有位老师带着U盘来，说要把课件现场打开看看。",
     "slots": (), "audiences": ("教师",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-教师-05", "kind": "hook",
     "text": "上课前十分钟投影连不上，是最耽误事的那种尴尬。",
     "slots": (), "audiences": ("教师",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-教师-06", "kind": "hook",
     "text": "老师选电脑先问重量，因为一天要跑几个教室。",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 2},
    {"id": "hook-教师-07", "kind": "hook",
     "text": "改作业改到晚上，屏幕看着累不累，比参数表更实际。",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 2},
    {"id": "hook-教师-08", "kind": "hook",
     "text": "教务处发的软件清单，常常比配置单更能决定买哪款。",
     "slots": (), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-教师-09", "kind": "hook",
     "text": "同一间办公室里，教龄不同，对电脑的期待也差得远。",
     "slots": (), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-教师-10", "kind": "hook",
     "text": "课件、录课、成绩表，老师在店里演示的常是这几样。",
     "slots": (), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 2},
    {"id": "hook-教师-11", "kind": "hook",
     "text": "老师们的电脑包里，除了电脑还有扩音器和翻页笔。",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 1},
    {"id": "hook-教师-12", "kind": "hook",
     "text": "教室里那台投影用了好几年，接得上接不上得先试。",
     "slots": (), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    # ---------------------------------------------------------------- hook：商务差旅
    {"id": "hook-商务差旅-01", "kind": "hook",
     "text": "一周飞几趟的人，对重量的容忍度低得离谱。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 3},
    {"id": "hook-商务差旅-02", "kind": "hook",
     "text": "高铁上打开电脑，前排靠背一放，屏幕角度就没了。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 2},
    {"id": "hook-商务差旅-03", "kind": "hook",
     "text": "出差前一晚收拾行李，电脑包那一格永远最纠结。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 2},
    {"id": "hook-商务差旅-04", "kind": "hook",
     "text": "今天有位客户拖着登机箱进店，说要能塞进前袋的机器。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-商务差旅-05", "kind": "hook",
     "text": "会议室里投屏那一下，比任何参数都让人紧张。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-商务差旅-06", "kind": "hook",
     "text": "常年在外跑的人，最怕的是找不到插座。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-商务差旅-07", "kind": "hook",
     "text": "有人进店先掂了掂样机，再问能不能连公司内网。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "hook-商务差旅-08", "kind": "hook",
     "text": "出差在外，电脑能不能连上酒店的网络，比参数实在。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-商务差旅-09", "kind": "hook",
     "text": "同事之间比来比去，落到最后都是重量和续航。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 2},
    {"id": "hook-商务差旅-10", "kind": "hook",
     "text": "两台机器摆一起，出差的人往往先看接口够不够。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-商务差旅-11", "kind": "hook",
     "text": "飞机上想改两页方案，小桌板一放下就知道屏幕多要紧。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 1},
    {"id": "hook-商务差旅-12", "kind": "hook",
     "text": "出差的人挑电脑，先算一天跑几个地方，再算带多少东西。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    # ---------------------------------------------------------------- hook：其余人群与通用
    {"id": "hook-内容创作-01", "kind": "hook",
     "text": "剪片子的人挑电脑，先看屏幕，再看接口够不够用。",
     "slots": (), "audiences": ("内容创作",), "platforms": ("小红书",), "weight": 1},
    {"id": "hook-内容创作-02", "kind": "hook",
     "text": "素材一多，硬盘空间和屏幕颜色就同时成了问题。",
     "slots": (), "audiences": ("内容创作",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-管理者-01", "kind": "hook",
     "text": "给团队配电脑，负责人更在意统一管理和售后响应。",
     "slots": (), "audiences": ("管理者",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-管理者-02", "kind": "hook",
     "text": "开会多的人，电脑更接近随身的会议屏。",
     "slots": (), "audiences": ("管理者",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "hook-企业采购-01", "kind": "hook",
     "text": "采购同事到店，开口先问能不能对接现有系统。",
     "slots": (), "audiences": ("企业采购",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-企业采购-02", "kind": "hook",
     "text": "批量换机前，IT更想先做一轮小规模试用。",
     "slots": (), "audiences": ("企业采购",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-旧机换新-01", "kind": "hook",
     "text": "旧电脑还能开机，但打开文档要等很久。",
     "slots": (), "audiences": ("旧机换新",), "platforms": ("小红书",), "weight": 1},
    {"id": "hook-旧机换新-02", "kind": "hook",
     "text": "换新之前，旧机器里的资料怎么搬，是很多人卡住的地方。",
     "slots": (), "audiences": ("旧机换新",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "hook-通用-01", "kind": "hook",
     "text": "到店十分钟，先弄清这台机器适不适合你手上的活儿。",
     "slots": (), "audiences": (), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "hook-通用-02", "kind": "hook",
     "text": "参数表看不懂很正常，把常用软件列出来反而更快。",
     "slots": (), "audiences": (), "platforms": ("微信公众号",), "weight": 2},
    # ---------------------------------------------------------------- scene：学生
    {"id": "scene-学生-01", "kind": "scene",
     "text": "宿舍书桌不宽，电脑摊开还要放得下键盘和水杯。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-学生-02", "kind": "scene",
     "text": "早八的教室，包里塞着电脑、充电器和水杯，走起来咣当响。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-学生-03", "kind": "scene",
     "text": "图书馆靠窗那排位置光线好，屏幕反光也明显，得换个角度再看。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-学生-04", "kind": "scene",
     "text": "期末周几个人共享一个插排，谁先占上谁安心。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-学生-05", "kind": "scene",
     "text": "新生报到那天，行李箱里留出的位置不多，电脑得挑薄的。",
     "slots": (), "audiences": ("学生",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "scene-学生-06", "kind": "scene",
     "text": "专业课上要现场跑软件，卡一下就要重来一遍。",
     "slots": (), "audiences": ("学生",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "scene-学生-07", "kind": "scene",
     "text": "实验室和宿舍两头跑，电脑一天要开合好几次。",
     "slots": (), "audiences": ("学生",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "scene-学生-08", "kind": "scene",
     "text": "小组作业在群里传文件，一份文档改到后面，谁手里的是最新版都说不清。",
     "slots": (), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-学生-09", "kind": "scene",
     "text": "宿舍熄灯后还有人赶作业，屏幕亮度得往低调，键盘也尽量别吵到室友。",
     "slots": (), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-学生-10", "kind": "scene",
     "text": "开学头几天，宿舍里拉了根长线，插排摊在地上。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 1},
    {"id": "scene-学生-11", "kind": "scene",
     "text": "同一门课，有人用实验室的机器，有人得自己带电脑，软件版本还不一定一致。",
     "slots": (), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-学生-12", "kind": "scene",
     "text": "开学前买机器，家长看预算，学生看能不能装上课要用的软件，两头都得对上。",
     "slots": (), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-学生-13", "kind": "scene",
     "text": "一门课一份讲义，资料散在群里、网盘和U盘里，找起来比做作业还花时间。",
     "slots": (), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-学生-14", "kind": "scene",
     "text": "自习室一坐一下午，中间要开浏览器查资料，再切回文档接着写。",
     "slots": (), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    # ---------------------------------------------------------------- scene：教师
    {"id": "scene-教师-01", "kind": "scene",
     "text": "早上连着两节课，课间十分钟要换教室，电脑得随手拎走。",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-教师-02", "kind": "scene",
     "text": "讲台上投影线不够长，电脑只能放在讲桌角落。",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-教师-03", "kind": "scene",
     "text": "录一节课的视频，要同时开摄像头、录屏和课件。",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-教师-04", "kind": "scene",
     "text": "办公室桌上摊着作业本和电脑，位置只剩一半。",
     "slots": (), "audiences": ("教师",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "scene-教师-05", "kind": "scene",
     "text": "年级组开会，几个人围着一台电脑看成绩表。",
     "slots": (), "audiences": ("教师",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "scene-教师-06", "kind": "scene",
     "text": "课件里插了很多图片，翻页时等的那几秒很显眼。",
     "slots": (), "audiences": ("教师",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "scene-教师-07", "kind": "scene",
     "text": "学生交上来的作业是电子版，批注要一页页翻，改完还得按学号把文件理一遍。",
     "slots": (), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-教师-08", "kind": "scene",
     "text": "教研组的软件版本不统一，同一份课件在别的机器上打开，格式可能就走样。",
     "slots": (), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-教师-09", "kind": "scene",
     "text": "带学生做演示，机器要能连上教室那台旧投影，线材和分辨率都得提前对上。",
     "slots": (), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-教师-10", "kind": "scene",
     "text": "课间，老师在讲台边把课件从自己电脑拷到教室机器。",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 1},
    {"id": "scene-教师-11", "kind": "scene",
     "text": "教研组共享一份课件，几个人轮流改，版本对不上就得来回传、来回核对。",
     "slots": (), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    # ---------------------------------------------------------------- scene：商务差旅
    {"id": "scene-商务差旅-01", "kind": "scene",
     "text": "高铁小桌板放不下太多东西，电脑打开后就没地方放水杯。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-商务差旅-02", "kind": "scene",
     "text": "机场候机两小时，找个带插座的座位比找咖啡店还难。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-商务差旅-03", "kind": "scene",
     "text": "酒店房间的桌子很窄，电脑、手机、充电器挤在一起。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 2},
    {"id": "scene-商务差旅-04", "kind": "scene",
     "text": "客户会议室的桌子是玻璃的，线一多就显得乱。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "scene-商务差旅-05", "kind": "scene",
     "text": "出差几天只带登机箱，电脑包还得塞进前袋。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "scene-商务差旅-06", "kind": "scene",
     "text": "在客户那儿改方案，最怕临时要接一个投屏。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "scene-商务差旅-07", "kind": "scene",
     "text": "早班机落地直接去开会，电脑从包里拿出来就得上场。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "scene-商务差旅-08", "kind": "scene",
     "text": "项目群里消息不断，回酒店还要逐条对一遍文档，第二天开会前再核一次口径。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-商务差旅-09", "kind": "scene",
     "text": "跨时区开会，电脑电量撑不撑得住要先算好，插座和转接头也得一起带上。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-商务差旅-10", "kind": "scene",
     "text": "机场安检要把电脑单独拿出来，包里的线也跟着散一地。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 1},
    {"id": "scene-商务差旅-11", "kind": "scene",
     "text": "一天跑两个客户，中间那段路只能在车上回邮件，靠的就是包里那台机器。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-商务差旅-12", "kind": "scene",
     "text": "客户的会议室里没有多余的插座，电脑只剩半格电，方案还得再讲一遍。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-商务差旅-13", "kind": "scene",
     "text": "行程临时改签，候机时间从一小时拖成半天，能不能接着干活全看电量。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-商务差旅-14", "kind": "scene",
     "text": "出差回来整理票据和文档，才发现这一趟用到的软件比预想的多。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    # ---------------------------------------------------------------- scene：其余人群与通用
    {"id": "scene-内容创作-01", "kind": "scene",
     "text": "外拍回来，素材卡一插就要开始挑片子，屏幕颜色得先看准。",
     "slots": (), "audiences": ("内容创作",), "platforms": ("小红书",), "weight": 1},
    {"id": "scene-管理者-01", "kind": "scene",
     "text": "部门里的机器型号不统一，出了小毛病各找各的办法。",
     "slots": (), "audiences": ("管理者",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-企业采购-01", "kind": "scene",
     "text": "新同事入职前一天，IT还在装系统、配账号。",
     "slots": (), "audiences": ("企业采购",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "scene-旧机换新-01", "kind": "scene",
     "text": "旧机器里的照片和文档要搬过来，家里人还得重新学一遍操作。",
     "slots": (), "audiences": ("旧机换新",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "scene-通用-01", "kind": "scene",
     "text": "门店里常有人拿手机比参数，其实更该看的是手感和接口。",
     "slots": (), "audiences": (), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "scene-通用-02", "kind": "scene",
     "text": "同一款机器，做表格的人和剪视频的人关心的地方不一样，配置得按活儿来配。",
     "slots": (), "audiences": (), "platforms": ("微信公众号",), "weight": 2},
    {"id": "scene-通用-03", "kind": "scene",
     "text": "同一款机器摆在展台上看着差不多，拎起来、打开、敲两下，差别就出来了。",
     "slots": (), "audiences": (), "platforms": ("微信公众号",), "weight": 2},
    {"id": "scene-通用-04", "kind": "scene",
     "text": "来店里的人大多带着具体问题，比如某个软件能不能装、旧机器的资料怎么搬。",
     "slots": (), "audiences": (), "platforms": ("微信公众号",), "weight": 2},
    # ---------------------------------------------------------------- benefit：学生
    {"id": "benefit-学生-01", "kind": "benefit",
     "text": "整机{重量}，装进书包侧袋，走楼梯也不坠肩。",
     "slots": ("重量",), "audiences": ("学生",), "platforms": ("小红书",), "weight": 3},
    {"id": "benefit-学生-02", "kind": "benefit",
     "text": "{屏幕尺寸}的屏幕摊开，宿舍桌上还能放下键盘和水杯。",
     "slots": ("屏幕尺寸",), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "benefit-学生-03", "kind": "benefit",
     "text": "电池是{电池}，能撑多久要按你怎么用算。",
     "slots": ("电池",), "audiences": ("学生",), "platforms": (), "weight": 2},
    {"id": "benefit-学生-04", "kind": "benefit",
     "text": "课件里的小字，放大着看也清楚，分辨率是{分辨率}。",
     "slots": ("分辨率",), "audiences": ("学生",), "platforms": ("小红书",), "weight": 1},
    {"id": "benefit-学生-05", "kind": "benefit",
     "text": "内存是{内存}，课件和浏览器可以同时开着。",
     "slots": ("内存",), "audiences": ("学生",), "platforms": (), "weight": 2},
    {"id": "benefit-学生-06", "kind": "benefit",
     "text": "机身厚{厚度}，夹在课本和练习册中间，包不鼓。",
     "slots": ("厚度",), "audiences": ("学生",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "benefit-学生-07", "kind": "benefit",
     "text": "课件翻页、表格滚动跟不跟手，看的是{刷新率}。",
     "slots": ("刷新率",), "audiences": ("学生",), "platforms": (), "weight": 1},
    {"id": "benefit-学生-08", "kind": "benefit",
     "text": "宿舍里连耳机、连鼠标都省事，靠的是{蓝牙}。",
     "slots": ("蓝牙",), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "benefit-学生-09", "kind": "benefit",
     "text": "预装{操作系统}，课程要用的软件能不能装，到店对版本。",
     "slots": ("操作系统",), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 2},
    # ---------------------------------------------------------------- benefit：教师
    {"id": "benefit-教师-01", "kind": "benefit",
     "text": "整机{重量}，从教研室到教室来回几趟，拎着不费劲。",
     "slots": ("重量",), "audiences": ("教师",), "platforms": ("小红书",), "weight": 3},
    {"id": "benefit-教师-02", "kind": "benefit",
     "text": "{屏幕尺寸}的屏幕，放课件时左边还能并排开一份教案。",
     "slots": ("屏幕尺寸",), "audiences": ("教师",), "platforms": ("小红书",), "weight": 2},
    {"id": "benefit-教师-03", "kind": "benefit",
     "text": "搭载{处理器}，课件和录课软件同时开着也转得动。",
     "slots": ("处理器",), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "benefit-教师-04", "kind": "benefit",
     "text": "电池是{电池}，上午连着两堂课，不用背着充电器跑。",
     "slots": ("电池",), "audiences": ("教师",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "benefit-教师-05", "kind": "benefit",
     "text": "机身做到{防尘抗水}，粉笔灰多的教室更省心。",
     "slots": ("防尘抗水",), "audiences": ("教师",), "platforms": (), "weight": 1},
    {"id": "benefit-教师-06", "kind": "benefit",
     "text": "自带{摄像头}，录课和线上教研都用得上。",
     "slots": ("摄像头",), "audiences": ("教师",), "platforms": (), "weight": 1},
    {"id": "benefit-教师-07", "kind": "benefit",
     "text": "内存给到{内存}，成绩表和教学视频来回切，不用等。",
     "slots": ("内存",), "audiences": ("教师",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "benefit-教师-08", "kind": "benefit",
     "text": "屏占比是{屏占比}，同样的机身里装下更大的屏。",
     "slots": ("屏占比",), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "benefit-教师-09", "kind": "benefit",
     "text": "机身厚{厚度}，夹在教案和作业本中间，包里不鼓。",
     "slots": ("厚度",), "audiences": ("教师",), "platforms": ("小红书",), "weight": 1},
    # ---------------------------------------------------------------- benefit：商务差旅
    {"id": "benefit-商务差旅-01", "kind": "benefit",
     "text": "整机{重量}，登机箱前袋能平着塞进去。",
     "slots": ("重量",), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 3},
    {"id": "benefit-商务差旅-02", "kind": "benefit",
     "text": "机身厚{厚度}，电脑包侧兜塞进去，拉链还合得上。",
     "slots": ("厚度",), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 2},
    {"id": "benefit-商务差旅-03", "kind": "benefit",
     "text": "电池是{电池}，高铁上开一路文档，回酒店再充。",
     "slots": ("电池",), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "benefit-商务差旅-04", "kind": "benefit",
     "text": "屏占比是{屏占比}，桌角那点地方摆得下，画面还够看。",
     "slots": ("屏占比",), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "benefit-商务差旅-05", "kind": "benefit",
     "text": "{屏幕尺寸}的屏幕，小桌板上摊开，前面椅背放下来要留神。",
     "slots": ("屏幕尺寸",), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 2},
    {"id": "benefit-商务差旅-06", "kind": "benefit",
     "text": "问的人不少：星闪到底支不支持？官方写的是{星闪}。",
     "slots": ("星闪",), "audiences": ("商务差旅",), "platforms": (), "weight": 1},
    {"id": "benefit-商务差旅-07", "kind": "benefit",
     "text": "预装{操作系统}，公司那套办公软件能不能装，到店对一下版本。",
     "slots": ("操作系统",), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 2},
    {"id": "benefit-商务差旅-08", "kind": "benefit",
     "text": "耳机和鼠标可以同时连着开会，靠的是{蓝牙}。",
     "slots": ("蓝牙",), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "benefit-商务差旅-09", "kind": "benefit",
     "text": "影像部分是{摄像头}，拍白板、开视频会都够用。",
     "slots": ("摄像头",), "audiences": ("商务差旅",), "platforms": (), "weight": 1},
    {"id": "benefit-商务差旅-10", "kind": "benefit",
     "text": "内存是{内存}，开会时翻方案来回切，不用先关一个。",
     "slots": ("内存",), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 1},
    # ---------------------------------------------------------------- benefit：通用
    {"id": "benefit-通用-01", "kind": "benefit",
     "text": "整机{重量}，拎着走一段路，手不累。",
     "slots": ("重量",), "audiences": (), "platforms": (), "weight": 3},
    {"id": "benefit-通用-02", "kind": "benefit",
     "text": "看图看表都够用，分辨率是{分辨率}。",
     "slots": ("分辨率",), "audiences": (), "platforms": (), "weight": 2},
    {"id": "benefit-通用-03", "kind": "benefit",
     "text": "搭载{处理器}，多开几个窗口也不至于转圈。",
     "slots": ("处理器",), "audiences": (), "platforms": (), "weight": 2},
    {"id": "benefit-通用-04", "kind": "benefit",
     "text": "存储是{存储}，资料和素材放得下，不用天天清盘。",
     "slots": ("存储",), "audiences": (), "platforms": (), "weight": 2},
    {"id": "benefit-通用-05", "kind": "benefit",
     "text": "预装{操作系统}，常用软件按系统版本装，少走弯路。",
     "slots": ("操作系统",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "benefit-通用-06", "kind": "benefit",
     "text": "内存给到{内存}，表格、网页和聊天窗口一起开着也不慌。",
     "slots": ("内存",), "audiences": (), "platforms": (), "weight": 2},
    {"id": "benefit-通用-07", "kind": "benefit",
     "text": "整机{重量}，机身厚{厚度}，两个数放一起才看得出便携。",
     "slots": ("重量", "厚度"), "audiences": (), "platforms": ("微信公众号",), "weight": 2},
    # ---------------------------------------------------------------- benefit：其余人群
    {"id": "benefit-内容创作-01", "kind": "benefit",
     "text": "屏幕是{屏幕类型}，素材颜色对不对，现场对一张就知道。",
     "slots": ("屏幕类型",), "audiences": ("内容创作",), "platforms": ("小红书",), "weight": 1},
    {"id": "benefit-内容创作-02", "kind": "benefit",
     "text": "存储是{存储}，外拍素材先倒进来，硬盘不用随身带。",
     "slots": ("存储",), "audiences": ("内容创作",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "benefit-管理者-01", "kind": "benefit",
     "text": "预装{操作系统}，部门软件统一到同一个版本更容易。",
     "slots": ("操作系统",), "audiences": ("管理者",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "benefit-管理者-02", "kind": "benefit",
     "text": "存储是{存储}，会议纪要和资料留在本机，交接时一起转。",
     "slots": ("存储",), "audiences": ("管理者",), "platforms": (), "weight": 1},
    {"id": "benefit-企业采购-01", "kind": "benefit",
     "text": "预装{操作系统}，批量部署前先按这个版本对业务系统。",
     "slots": ("操作系统",), "audiences": ("企业采购",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "benefit-企业采购-02", "kind": "benefit",
     "text": "无线这块是{蓝牙}，现有蓝牙外设能不能沿用，到店先配一遍。",
     "slots": ("蓝牙",), "audiences": ("企业采购",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "benefit-旧机换新-01", "kind": "benefit",
     "text": "存储是{存储}，旧机器里的照片和文档搬过来，空间还有富余。",
     "slots": ("存储",), "audiences": ("旧机换新",), "platforms": ("小红书",), "weight": 1},
    {"id": "benefit-旧机换新-02", "kind": "benefit",
     "text": "预装{操作系统}，新旧系统的操作差别，到店先摸一遍。",
     "slots": ("操作系统",), "audiences": ("旧机换新",), "platforms": ("门店朋友圈",), "weight": 1},
    # ---------------------------------------------------------------- evidence：规格陈述
    {"id": "evidence-通用-01", "kind": "evidence",
     "text": "整机{重量}，销售版本不同，以包装内说明为准。",
     "slots": ("重量",), "audiences": (), "platforms": (), "weight": 2},
    {"id": "evidence-通用-02", "kind": "evidence",
     "text": "这块屏用的是{屏幕类型}，具体观感以实机为准。",
     "slots": ("屏幕类型",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-03", "kind": "evidence",
     "text": "屏幕刷新这一项，官方给的是{刷新率}，具体模式在系统设置里切。",
     "slots": ("刷新率",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-04", "kind": "evidence",
     "text": "电池是{电池}，续航长短还看亮度、外接设备和后台开多少。",
     "slots": ("电池",), "audiences": (), "platforms": (), "weight": 2},
    {"id": "evidence-通用-05", "kind": "evidence",
     "text": "屏幕是{屏幕尺寸}，窗口并排时不用把字调小。",
     "slots": ("屏幕尺寸",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-06", "kind": "evidence",
     "text": "这颗芯片是{处理器}，频率和核心数在官方参数页能查到。",
     "slots": ("处理器",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-07", "kind": "evidence",
     "text": "出厂预装{操作系统}，常用软件要不要另对版本，可以现场确认。",
     "slots": ("操作系统",), "audiences": (), "platforms": (), "weight": 2},
    {"id": "evidence-通用-08", "kind": "evidence",
     "text": "内存是{内存}，开几个窗口够不够，可以到店同时开给你看。",
     "slots": ("内存",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-09", "kind": "evidence",
     "text": "官方给的影像配置是{摄像头}，效果和光线条件有关。",
     "slots": ("摄像头",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-10", "kind": "evidence",
     "text": "摄像头这块，官方给的是{摄像头}，视频通话的画质还看网络。",
     "slots": ("摄像头",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-11", "kind": "evidence",
     "text": "机身能做到{防尘抗水}，等级不等于可以泡水，说明书里写得更细。",
     "slots": ("防尘抗水",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-12", "kind": "evidence",
     "text": "无线这块是{蓝牙}，配对设备的兼容性以设备说明为准。",
     "slots": ("蓝牙",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-13", "kind": "evidence",
     "text": "分辨率是{分辨率}，放大看小字也清楚。",
     "slots": ("分辨率",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-14", "kind": "evidence",
     "text": "厚度给到{厚度}，不同版本的口径可能不同，具体以官方页面为准。",
     "slots": ("厚度",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-15", "kind": "evidence",
     "text": "星闪这一项，官方原文是“{星闪}”，可用配件以官方公布的清单为准。",
     "slots": ("星闪",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-16", "kind": "evidence",
     "text": "屏占比是{屏占比}，边框多宽以实机为准，照片有角度差。",
     "slots": ("屏占比",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-17", "kind": "evidence",
     "text": "整机{重量}，厚度是{厚度}，两个数放一起才看得出便携。",
     "slots": ("重量", "厚度"), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-18", "kind": "evidence",
     "text": "整机{重量}，同一型号的不同销售版本，重量会有细微差别。",
     "slots": ("重量",), "audiences": (), "platforms": (), "weight": 2},
    {"id": "evidence-通用-19", "kind": "evidence",
     "text": "存储标称{存储}，可用容量会小一点，系统和预装软件要占一部分。",
     "slots": ("存储",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-通用-20", "kind": "evidence",
     "text": "屏幕刷新给到{刷新率}，模式随系统设置切换。",
     "slots": ("刷新率",), "audiences": (), "platforms": (), "weight": 1},
    {"id": "evidence-学生-01", "kind": "evidence",
     "text": "课程软件能不能装，按{操作系统}对应的清单一项项对。",
     "slots": ("操作系统",), "audiences": ("学生",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "evidence-教师-01", "kind": "evidence",
     "text": "老师录课用的{摄像头}，教室光线和网络都会影响画面。",
     "slots": ("摄像头",), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "evidence-商务差旅-01", "kind": "evidence",
     "text": "出差更在意电池能给到多少，官方数字是{电池}，实际还看亮度与外接设备。",
     "slots": ("电池",), "audiences": ("商务差旅",), "platforms": ("微信公众号",), "weight": 1},
    # ---------------------------------------------------------------- store：到店引导
    {"id": "store-通用-01", "kind": "store",
     "text": "到店可以直接上手，把常用的软件打开试一遍再决定。",
     "slots": (), "audiences": (), "platforms": (), "weight": 3},
    {"id": "store-通用-02", "kind": "store",
     "text": "带上课程表或工作软件清单，现场逐项对版本。",
     "slots": (), "audiences": (), "platforms": (), "weight": 2},
    {"id": "store-通用-03", "kind": "store",
     "text": "门店的样机可以自己调，键盘手感、屏幕角度都试试。",
     "slots": (), "audiences": (), "platforms": (), "weight": 2},
    {"id": "store-通用-04", "kind": "store",
     "text": "想试哪个场景都可以说，我们把对应的演示打开。",
     "slots": (), "audiences": (), "platforms": (), "weight": 2},
    {"id": "store-通用-05", "kind": "store",
     "text": "来之前私信说一声，我们提前把机器准备好。",
     "slots": (), "audiences": (), "platforms": (), "weight": 2},
    {"id": "store-通用-06", "kind": "store",
     "text": "带旧机器来也行，现场比一比新旧两台的差别。",
     "slots": (), "audiences": (), "platforms": (), "weight": 1},
    {"id": "store-通用-07", "kind": "store",
     "text": "拿不准配置的话，先到店坐十分钟，再定型号。",
     "slots": (), "audiences": (), "platforms": (), "weight": 2},
    {"id": "store-通用-08", "kind": "store",
     "text": "外设和投影可以现场连，能不能用当场就清楚。",
     "slots": (), "audiences": (), "platforms": (), "weight": 1},
    {"id": "store-学生-01", "kind": "store",
     "text": "学生可以带着作业本和课程软件来，边试边问。",
     "slots": (), "audiences": ("学生",), "platforms": (), "weight": 1},
    {"id": "store-商务差旅-01", "kind": "store",
     "text": "出差路过也能进来，登机箱和电脑包都可以试装。",
     "slots": (), "audiences": ("商务差旅",), "platforms": (), "weight": 1},
    # ---------------------------------------------------------------- ending：结尾互动
    {"id": "ending-通用-01", "kind": "ending",
     "text": "你平时主要用它做什么？评论区说说，我帮你对配置。",
     "slots": (), "audiences": (), "platforms": ("小红书",), "weight": 3},
    {"id": "ending-通用-02", "kind": "ending",
     "text": "拿不准就私信，把常用软件发我，我按软件给你筛。",
     "slots": (), "audiences": (), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "ending-通用-03", "kind": "ending",
     "text": "到店试过再决定，不用急着当天买单。",
     "slots": (), "audiences": (), "platforms": (), "weight": 2},
    {"id": "ending-通用-04", "kind": "ending",
     "text": "想要哪款的实拍图，评论区留个型号，我拍给你看。",
     "slots": (), "audiences": (), "platforms": ("小红书",), "weight": 2},
    {"id": "ending-通用-05", "kind": "ending",
     "text": "有具体型号想对比，私信报名字，我们摆一起给你看。",
     "slots": (), "audiences": (), "platforms": ("门店朋友圈",), "weight": 2},
    {"id": "ending-通用-06", "kind": "ending",
     "text": "把你的使用场景写下来，比翻一堆参数贴有用。",
     "slots": (), "audiences": (), "platforms": ("微信公众号",), "weight": 2},
    {"id": "ending-通用-07", "kind": "ending",
     "text": "欢迎带着设备清单来门店，我们一条条对。",
     "slots": (), "audiences": (), "platforms": ("微信公众号",), "weight": 1},
    {"id": "ending-学生-01", "kind": "ending",
     "text": "开学前想好专业要用的软件，再来挑机器更省事。",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 1},
    {"id": "ending-学生-02", "kind": "ending",
     "text": "宿舍里几个人一起用，也可以来店里试同一个场景。",
     "slots": (), "audiences": ("学生",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "ending-教师-01", "kind": "ending",
     "text": "老师可以把课件带来，投影和录屏都现场走一遍。",
     "slots": (), "audiences": ("教师",), "platforms": ("微信公众号",), "weight": 1},
    {"id": "ending-教师-02", "kind": "ending",
     "text": "教研组统一换机，先来两个人试，合适了再定。",
     "slots": (), "audiences": ("教师",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "ending-商务差旅-01", "kind": "ending",
     "text": "常出差的话，带上自己的电脑包来试装最直接。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 1},
    {"id": "ending-商务差旅-02", "kind": "ending",
     "text": "出差前想加急看机，提前私信约个时间。",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("门店朋友圈",), "weight": 1},
    {"id": "ending-企业采购-01", "kind": "ending",
     "text": "采购前先小批量试用，比一次订完稳妥。",
     "slots": (), "audiences": ("企业采购",), "platforms": ("微信公众号",), "weight": 1},
    # ---------------------------------------------------------------- tag：话题标签
    {"id": "tag-学生-01", "kind": "tag",
     "text": "#学生笔记本",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 3},
    {"id": "tag-学生-02", "kind": "tag",
     "text": "#开学换电脑",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "tag-学生-03", "kind": "tag",
     "text": "#大学生选本",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 2},
    {"id": "tag-学生-04", "kind": "tag",
     "text": "#宿舍生产力",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-学生-05", "kind": "tag",
     "text": "#自习室搭子",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-学生-06", "kind": "tag",
     "text": "#校园数码",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-学生-07", "kind": "tag",
     "text": "#新生入学",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-学生-08", "kind": "tag",
     "text": "#课程软件适配",
     "slots": (), "audiences": ("学生",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-教师-01", "kind": "tag",
     "text": "#教师办公本",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 3},
    {"id": "tag-教师-02", "kind": "tag",
     "text": "#备课日常",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 2},
    {"id": "tag-教师-03", "kind": "tag",
     "text": "#教室投影",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-教师-04", "kind": "tag",
     "text": "#老师换电脑",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 2},
    {"id": "tag-教师-05", "kind": "tag",
     "text": "#教研组换机",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-教师-06", "kind": "tag",
     "text": "#课件与录课",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-教师-07", "kind": "tag",
     "text": "#讲台数码",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-教师-08", "kind": "tag",
     "text": "#录课设备",
     "slots": (), "audiences": ("教师",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-商务差旅-01", "kind": "tag",
     "text": "#商务差旅",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 3},
    {"id": "tag-商务差旅-02", "kind": "tag",
     "text": "#出差装备",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 2},
    {"id": "tag-商务差旅-03", "kind": "tag",
     "text": "#高铁办公",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-商务差旅-04", "kind": "tag",
     "text": "#登机箱装得下",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-商务差旅-05", "kind": "tag",
     "text": "#移动办公",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 2},
    {"id": "tag-商务差旅-06", "kind": "tag",
     "text": "#会议现场",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-商务差旅-07", "kind": "tag",
     "text": "#差旅轻装",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-商务差旅-08", "kind": "tag",
     "text": "#出差党的电脑",
     "slots": (), "audiences": ("商务差旅",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-内容创作-01", "kind": "tag",
     "text": "#内容创作",
     "slots": (), "audiences": ("内容创作",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-内容创作-02", "kind": "tag",
     "text": "#修图剪片",
     "slots": (), "audiences": ("内容创作",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-管理者-01", "kind": "tag",
     "text": "#团队配机",
     "slots": (), "audiences": ("管理者",), "platforms": (), "weight": 1},
    {"id": "tag-管理者-02", "kind": "tag",
     "text": "#部门换新",
     "slots": (), "audiences": ("管理者",), "platforms": (), "weight": 1},
    {"id": "tag-企业采购-01", "kind": "tag",
     "text": "#企业采购",
     "slots": (), "audiences": ("企业采购",), "platforms": (), "weight": 1},
    {"id": "tag-企业采购-02", "kind": "tag",
     "text": "#批量部署",
     "slots": (), "audiences": ("企业采购",), "platforms": (), "weight": 1},
    {"id": "tag-旧机换新-01", "kind": "tag",
     "text": "#旧机换新",
     "slots": (), "audiences": ("旧机换新",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-旧机换新-02", "kind": "tag",
     "text": "#资料迁移",
     "slots": (), "audiences": ("旧机换新",), "platforms": ("小红书",), "weight": 1},
    {"id": "tag-通用-01", "kind": "tag",
     "text": "#华为笔记本",
     "slots": (), "audiences": (), "platforms": (), "weight": 3},
    {"id": "tag-通用-02", "kind": "tag",
     "text": "#门店实拍",
     "slots": (), "audiences": (), "platforms": (), "weight": 2},
    {"id": "tag-通用-03", "kind": "tag",
     "text": "#到店试机",
     "slots": (), "audiences": (), "platforms": (), "weight": 2},
)


def fragments(kind: str, audience: str = "", platform: str = "") -> list[dict]:
    """按类型筛选片段：人群或平台为空表示不限；通用片段永远可用。

    返回的是句库里的片段本身（dict 只读，组合器不要改写）；weight 由组合器做加权随机。
    """
    if kind not in KINDS:
        raise ValueError(f"未知的片段类型：{kind!r}；可用类型：{'、'.join(KINDS)}。")
    audience = audience if isinstance(audience, str) else ""
    platform = platform if isinstance(platform, str) else ""
    result = []
    for item in FRAGMENTS:
        if not isinstance(item, dict) or item.get("kind") != kind:
            continue
        if audience and item.get("audiences") and audience not in item["audiences"]:
            continue
        if platform and item.get("platforms") and platform not in item["platforms"]:
            continue
        result.append(item)
    return result


def _plain(text: str) -> str:
    """去掉槽位与标点，只留下用来比对措辞的正文。"""
    plain = SLOT_PATTERN.sub("", unicodedata.normalize("NFKC", str(text)))
    return re.sub(r"[\s，。、；：！？,.;:!?#「」【】（）()\-—…]", "", plain)


def _bigrams(text: str) -> set[str]:
    plain = _plain(text)
    return {plain[i:i + 2] for i in range(len(plain) - 1)} or {plain}


def _overlap(first: str, second: str) -> float:
    """两句话的二元字组重合度，用于发现只换了几个字的重复片段。"""
    left, right = _bigrams(first), _bigrams(second)
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _count(kind: str, audience: str = "") -> int:
    total = 0
    for item in FRAGMENTS:
        if not isinstance(item, dict) or item.get("kind") != kind:
            continue
        if audience:
            tags = item.get("audiences") or ()
            if audience == "通用":
                if tags:
                    continue
            elif audience not in tags:
                continue
        total += 1
    return total


def _tuple_problem(label: str, field: str, value, allowed: tuple[str, ...]) -> str:
    return f"{label} 的 {field} 必须是 {allowed[0]} 等取值组成的元组，实际是 {value!r}。"


def validate() -> list[str]:
    """自检句库，返回问题列表（空列表表示通过）。"""
    problems: list[str] = []
    seen: set[str] = set()

    for position, item in enumerate(FRAGMENTS, 1):
        if not isinstance(item, dict):
            problems.append(f"第 {position} 条片段不是 dict。")
            continue
        fid = item.get("id")
        label = fid if isinstance(fid, str) and fid else f"第 {position} 条片段"
        if not isinstance(fid, str) or not fid:
            problems.append(f"第 {position} 条片段缺少 id。")
        elif fid in seen:
            problems.append(f"id 重复：{fid}。")
        else:
            seen.add(fid)

        missing = FRAGMENT_KEYS - set(item)
        if missing:
            problems.append(f"{label} 缺少键：{'、'.join(sorted(missing))}。")
        extra = set(item) - FRAGMENT_KEYS
        if extra:
            problems.append(f"{label} 有多余的键：{'、'.join(sorted(map(str, extra)))}。")

        kind = item.get("kind")
        if kind not in KINDS:
            problems.append(f"{label} 的 kind 不合法：{kind!r}。")
            continue
        if isinstance(fid, str) and fid and not fid.startswith(kind + "-"):
            problems.append(f"{label} 的 id 应以 {kind}- 开头。")

        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            problems.append(f"{label} 的 text 为空。")
            continue
        if text != text.strip():
            problems.append(f"{label} 的 text 首尾带空白。")
        normalized = unicodedata.normalize("NFKC", text)

        placeholders = SLOT_PATTERN.findall(normalized)
        leftover = SLOT_PATTERN.sub("", normalized)
        if "{" in leftover or "}" in leftover:
            problems.append(f"{label} 的花括号不成对。")

        slots = item.get("slots")
        if not isinstance(slots, tuple) or not all(isinstance(s, str) for s in slots):
            problems.append(f"{label} 的 slots 必须是字符串元组，实际是 {slots!r}。")
            slots = ()
        else:
            if len(set(slots)) != len(slots):
                problems.append(f"{label} 的 slots 有重复项。")
            unknown = [s for s in slots if s not in SLOT_ALIASES]
            if unknown:
                problems.append(f"{label} 用了 facts 里没有的槽位：{'、'.join(unknown)}。")
            undeclared = [s for s in placeholders if s not in slots]
            if undeclared:
                problems.append(f"{label} 的模板用到未声明的槽位：{'、'.join(undeclared)}。")
            unused = [s for s in slots if s not in placeholders]
            if unused:
                problems.append(f"{label} 声明了模板里没有的槽位：{'、'.join(unused)}。")
            if len(set(placeholders)) != len(placeholders):
                problems.append(f"{label} 的同一个槽位在模板里出现了两次。")
        if kind in ("benefit", "evidence") and not slots:
            problems.append(f"{label} 的 {kind} 片段必须带事实槽位。")

        if re.search(r"\d", normalized):
            problems.append(f"{label} 的正文含阿拉伯数字，数字只能由槽位带入。")
        for pattern in BANNED:
            hit = re.search(pattern, normalized, re.I)
            if hit:
                problems.append(f"{label} 命中 policy.BANNED：{hit.group(0)}。")
        dynamic = DYNAMIC.search(normalized)
        if dynamic:
            problems.append(f"{label} 命中 policy.DYNAMIC：{dynamic.group(0)}。")
        for phrase in BANNED_PHRASES:
            if phrase.casefold() in normalized.casefold():
                problems.append(f"{label} 命中禁用套话：{phrase}。")

        limit = LENGTH_LIMITS[kind]
        if len(text) > limit:
            problems.append(f"{label} 共 {len(text)} 字，超过 {kind} 的 {limit} 字上限。")

        if kind == "tag":
            if not text.startswith("#") or len(text) < 2:
                problems.append(f"{label} 的话题标签要写成 #话题 的形式。")
            elif any(ch.isspace() for ch in text):
                problems.append(f"{label} 的话题标签不能含空格。")
        elif text.startswith("#"):
            problems.append(f"{label} 只有 tag 片段可以用 # 开头。")

        audiences = item.get("audiences")
        if not isinstance(audiences, tuple) or not all(isinstance(a, str) for a in audiences):
            problems.append(_tuple_problem(label, "audiences", audiences, AUDIENCES))
        else:
            unknown = [a for a in audiences if a not in AUDIENCES]
            if unknown:
                problems.append(f"{label} 的 audiences 里有未知人群：{'、'.join(unknown)}。")

        platforms = item.get("platforms")
        if not isinstance(platforms, tuple) or not all(isinstance(p, str) for p in platforms):
            problems.append(_tuple_problem(label, "platforms", platforms, PLATFORMS))
        else:
            unknown = [p for p in platforms if p not in PLATFORMS]
            if unknown:
                problems.append(f"{label} 的 platforms 里有未知平台：{'、'.join(unknown)}。")

        weight = item.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, int) or weight not in (1, 2, 3):
            problems.append(f"{label} 的 weight 必须是 1-3 的整数，实际是 {weight!r}。")

    for kind in KINDS:
        if not _count(kind):
            problems.append(f"{kind} 类片段为空。")
    for (kind, audience), minimum in MINIMUMS.items():
        actual = _count(kind, "" if audience == "总计" else audience)
        if actual < minimum:
            problems.append(f"{kind} / {audience} 只有 {actual} 条，少于要求的 {minimum} 条。")

    tagged_store = sum(1 for item in FRAGMENTS
                       if isinstance(item, dict) and item.get("kind") == "store" and item.get("audiences"))
    if tagged_store > 2:
        problems.append(f"store 片段带人群标签的有 {tagged_store} 条，最多允许 2 条。")

    for kind in KINDS:
        for audience in AUDIENCES + ("通用",):
            group = [item for item in FRAGMENTS
                     if isinstance(item, dict) and item.get("kind") == kind
                     and ((audience == "通用" and not item.get("audiences"))
                          or audience in (item.get("audiences") or ()))]
            for index, first in enumerate(group):
                for second in group[index + 1:]:
                    score = _overlap(str(first.get("text", "")), str(second.get("text", "")))
                    if score >= 0.72:
                        problems.append(f"{first.get('id')} 与 {second.get('id')} 措辞过于相似"
                                        f"（{score:.2f}），同一人群内要换说法。")
    return problems
