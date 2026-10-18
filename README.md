# 企业文案与营销 AI 助手

> 浙客松 2026 · AI+X 破界黑客松 · **华为产业落地赛道**
> 赛题：围绕**企业文案与营销场景**开发应用（正式企业命题于 2026-10-18 13:00 发布）

- GitHub 仓库：https://github.com/xiaoma-iqoo/zhekesong-huawei-2026
- 魔搭创空间：https://www.modelscope.cn/studios/xiaoma2008/zhekesong-huawei-2026
- 团队：能工智人队

---

## 当前状态

当前仓库为**可运行占位版本**（2026-10-18 13:00 赛题发布前）：
提前打通「GitHub 仓库 → 魔搭创空间（ModelScope Studio）」部署链路，
保证初赛提交表单中的两个链接从赛题发布起即可直接访问。

正式作品将在赛题发布后于**同一仓库、同一创空间链接**上更新，链接保持不变。

## 功能（占位版）

输入产品名称、目标人群、核心卖点、投放渠道、文案语气与活动信息，
输出结构化营销文案，并附带写作策略说明：

- 内置 5 类渠道文案结构：小红书 / 微信公众号 / 电商详情页 / 朋友圈 / B 端邮件
- 3 种文案语气：专业可信 / 活泼种草 / 高端克制
- 输出包含标题、正文、话题标签、行动号召与写作策略

> 占位版为纯规则模板实现，不依赖外部模型服务；正式版将接入大模型完成
> 需求理解、品牌语气适配与多渠道改写。

## 目录结构

```
.
├── app.py             # Gradio 应用（魔搭创空间入口）
├── requirements.txt   # 依赖
├── README.md
└── .gitignore
```

## 本地运行

```bash
pip install -r requirements.txt
python app.py
```

## 部署

- 魔搭创空间（Studio）类型：Gradio，代码通过 git 推送后部署：

```bash
git remote add modelscope https://oauth2:<MODELSCOPE_TOKEN>@www.modelscope.cn/studios/xiaoma2008/zhekesong-huawei-2026.git
git push modelscope main:master
```

## 赛事信息

| 项 | 内容 |
| --- | --- |
| 赛道 | 华为产业落地赛道（企业命题，线下初赛） |
| 初赛 | 2026-10-18 13:00–17:00，浙江大学紫金港校区 北2-227 |
| 复赛 | 2026-10-19 00:00 – 2026-10-24 00:00（线上） |
| 决赛 | 2026-10-25 09:15–11:30，三墩元空间 |

## 提交材料

初赛（industry / initial）必填：项目名称、GitHub 仓库链接、魔搭部署链接、作品说明书。
