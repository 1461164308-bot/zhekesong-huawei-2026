# -*- coding: utf-8 -*-
"""
浙客松 2026 · 华为产业落地赛道
企业文案与营销 AI 助手（部署占位版）

说明：
    本文件是赛题正式发布前的"可运行占位版本"，用于提前打通
    GitHub 仓库 + 魔搭创空间（ModelScope Studio）的部署链路，
    保证提交表单里两个链接从 13:00 起即可直接访问。

    赛题发布后，团队会在此骨架上实现正式作品，链接保持不变。
"""

from __future__ import annotations

import random

import gradio as gr

APP_TITLE = "企业文案与营销 AI 助手"
APP_SUBTITLE = "浙客松 2026 · 华为产业落地赛道 · 可运行占位版本"

CHANNEL_RULES = {
    "小红书": {
        "tone": "口语化、有情绪、多用 emoji",
        "structure": "钩子标题 → 场景痛点 → 产品卖点 → 使用体验 → 话题标签",
        "tags": ["#好物分享", "#打工人必备", "#效率工具", "#职场干货"],
    },
    "微信公众号": {
        "tone": "专业、克制、有信息量",
        "structure": "标题 → 引言 → 分点论证 → 案例 → 行动号召",
        "tags": [],
    },
    "电商详情页": {
        "tone": "利益点前置、短句、强调转化",
        "structure": "核心卖点 → 功能分点 → 信任背书 → 促销信息 → 立即购买",
        "tags": [],
    },
    "朋友圈": {
        "tone": "生活化、第一人称、轻营销",
        "structure": "一句话场景 → 一句产品利益 → 轻号召",
        "tags": [],
    },
    "B 端邮件": {
        "tone": "正式、简洁、聚焦业务价值",
        "structure": "称呼 → 背景一句话 → 方案价值三点 → 下一步 → 署名",
        "tags": [],
    },
}

STYLE_HINTS = {
    "专业可信": "使用行业通用术语，量化收益，避免夸张形容词。",
    "活泼种草": "使用短句与感叹句，突出体验感与情绪价值。",
    "高端克制": "减少感叹号，用名词与事实说话，留白制造质感。",
}


def _bullet_points(features: str) -> list[str]:
    """把用户填写的卖点按行/分号拆成要点列表。"""
    raw = (features or "").replace("；", "\n").replace(";", "\n")
    items = [line.strip(" -•\t") for line in raw.splitlines() if line.strip(" -•\t")]
    return items[:6]


def generate_copy(
    product: str,
    audience: str,
    features: str,
    channel: str,
    style: str,
    promo: str,
) -> str:
    """生成结构化的营销文案（占位实现：规则模板 + 可解释结构）。"""
    product = (product or "待填写产品").strip()
    audience = (audience or "目标用户").strip()
    channel = channel if channel in CHANNEL_RULES else "小红书"
    style = style if style in STYLE_HINTS else "专业可信"
    rule = CHANNEL_RULES[channel]
    points = _bullet_points(features) or ["核心卖点待补充"]
    promo = (promo or "").strip()

    if channel == "小红书":
        title = f"{product}｜{audience}看完直接抄作业"
        body_lines = [
            f"说真的，做{audience}最怕的就是{random.choice(['时间不够用', '效率上不去', '反复返工'])}。",
            f"最近用了【{product}】，最大的感受是：{points[0]}。",
            "",
            "亮点我整理成这几点：",
        ]
    elif channel == "微信公众号":
        title = f"{product}：为{audience}重新设计的工作方式"
        body_lines = [
            f"面向{audience}，{product}希望解决的不是「有没有工具」，而是「工具是否真正进入业务流程」。",
            "",
            "核心能力：",
        ]
    elif channel == "电商详情页":
        title = f"{product} {promo or '限时上新'}"
        body_lines = [
            f"专为{audience}设计。",
            "",
            "为什么选它：",
        ]
    elif channel == "朋友圈":
        title = ""
        body_lines = [
            f"最近{random.choice(['试了个新东西', '被安利了一个工具'])}：{product}。",
            f"对{audience}真的友好，{points[0]}。",
        ]
    else:  # B 端邮件
        title = f"关于 {product} 的业务合作建议"
        body_lines = [
            "您好，",
            "",
            f"我们注意到{audience}在相关场景中的效率诉求，{product}可以提供一套可落地的方案。",
            "",
            "方案价值：",
        ]

    for idx, point in enumerate(points, start=1):
        body_lines.append(f"{idx}. {point}")

    if channel in ("小红书", "微信公众号", "电商详情页") and promo:
        body_lines += ["", f"活动信息：{promo}"]

    if channel == "小红书":
        body_lines += ["", "收藏起来慢慢看，评论区聊聊你的用法～"]
    elif channel == "微信公众号":
        body_lines += ["", "如果你也在思考同样的问题，欢迎留言交流，或点击「阅读原文」了解方案细节。"]
    elif channel == "电商详情页":
        body_lines += ["", "现在下单，锁定优惠。"]
    elif channel == "朋友圈":
        body_lines += ["", "需要的话可以找我要链接。"]
    else:
        body_lines += ["", "期待与您进一步沟通，谢谢！", "", "此致", "敬礼"]

    tags = " ".join(rule["tags"]) if rule["tags"] else ""

    parts = []
    if title:
        parts.append(f"【{channel} · 标题】{title}")
    parts.append(f"【{channel} · 正文】")
    parts.extend(body_lines)
    if tags:
        parts.append("")
        parts.append(f"【话题标签】{tags}")
    parts.append("")
    parts.append("———")
    parts.append("**写作策略**")
    parts.append(f"- 渠道：{channel}（{rule['tone']}）")
    parts.append(f"- 结构：{rule['structure']}")
    parts.append(f"- 语气：{style} — {STYLE_HINTS[style]}")
    parts.append(f"- 目标人群：{audience}")
    return "\n".join(parts)


EXAMPLE = [
    ["「智写」企业营销助手", "中小企业市场运营人员", "一键生成多渠道文案\n自动适配品牌语气\n支持营销活动复盘", "小红书", "活泼种草", "新用户首月 5 折"],
]


def build_demo() -> gr.Blocks:
    with gr.Blocks(title=APP_TITLE, theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            f"# {APP_TITLE}\n"
            f"{APP_SUBTITLE}\n\n"
            "> 当前为赛题发布前的**可运行占位版本**，用于提前打通 GitHub 与魔搭创空间的部署链路；"
            "正式作品将在 2026-10-18 13:00 赛题发布后于同一链接更新。"
        )
        with gr.Row():
            with gr.Column(scale=3):
                product = gr.Textbox(label="产品 / 服务名称", placeholder="例如：「智写」企业营销助手")
                audience = gr.Textbox(label="目标人群", placeholder="例如：中小企业市场运营人员")
                features = gr.Textbox(
                    label="核心卖点（每行一条）",
                    lines=4,
                    placeholder="一键生成多渠道文案\n自动适配品牌语气\n支持营销活动复盘",
                )
                with gr.Row():
                    channel = gr.Dropdown(
                        label="投放渠道",
                        choices=list(CHANNEL_RULES.keys()),
                        value="小红书",
                    )
                    style = gr.Dropdown(
                        label="文案语气",
                        choices=list(STYLE_HINTS.keys()),
                        value="专业可信",
                    )
                promo = gr.Textbox(label="活动 / 促销信息（选填）", placeholder="例如：新用户首月 5 折")
                run_btn = gr.Button("生成营销文案", variant="primary")
            with gr.Column(scale=4):
                output = gr.Markdown(label="生成结果", value="填写左侧信息后点击「生成营销文案」。")

        run_btn.click(
            generate_copy,
            inputs=[product, audience, features, channel, style, promo],
            outputs=output,
        )
        gr.Examples(
            examples=EXAMPLE,
            inputs=[product, audience, features, channel, style, promo],
        )
        gr.Markdown(
            "---\n"
            "**项目链接**\n\n"
            "- GitHub：https://github.com/xiaoma-iqoo/zhekesong-huawei-2026\n"
            "- 魔搭创空间：https://www.modelscope.cn/studios/xiaoma2008/zhekesong-huawei-2026\n"
            "\n赛事：浙客松 2026 · AI+X 破界黑客松 · 华为产业落地赛道"
        )
    return demo


demo = build_demo()

if __name__ == "__main__":
    demo.launch()
