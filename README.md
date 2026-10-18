---
title: 知衡 · 华为PC图文营销智能体
emoji: 🧭
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.29.1
app_file: app.py
pinned: false
license: apache-2.0
---

# 知衡 · 华为PC图文营销智能体

浙客松 2026 · AI+X · 华为产业进阶赛道｜赛题：**AI+华为PC营销软文智能体**  
团队：**能工智人队**。团队独立开发，非华为官方产品。

- [GitHub 源码](https://github.com/xiaoma-iqoo/zhekesong-huawei-2026)
- [ModelScope 创空间](https://www.modelscope.cn/studios/xiaoma2008/zhekesong-huawei-2026)
- [直接打开应用](https://xiaoma2008-zhekesong-huawei-2026.ms.show)

本地新版按 **确认需求 → 确认风格卡 → 修改并确认创作思路 → 审阅终稿 → 确认下载** 分步创作。支持专业可信、亲切自然、简洁直接、场景共情、理性分析、活泼轻快六种内置风格；也可输入风格描述、粘贴以往软文，或同时提供两者，提炼为七项可编辑风格卡。常用风格只保存在当前浏览器（最多12张），不保存原参考文案；清理浏览器存储后需重新保存。

产品事实仍来自授权知识库或明确提供的华为官方商城商品页，参考文案只提供表达特征。思路阶段先完成事实和图源核验，不提前写终稿；用户确认思路后复用该次证据生成并审核终稿。修改需求、风格或思路后，对应确认失效；证据超过一小时需重新读取。当前本地改动未经用户测试批准，不上传或部署。

**新增来源规则：** 允许 [华为官方商城](https://www.vmall.com/) 的具体商品页。可在补充要求中提供 `https://www.vmall.com/product/商品编号.html`；仅读取可获取的主商品正文，核对精确型号、年份、系统及SKU，记录官方链接、读取时间和 `official_vmall` 来源。与知识库同时使用时标为混合来源，获授权归档仍明确非实时 ima；图片继续使用同型号授权知识库素材。商城首页、搜索摘要、推荐商品、第三方页面和模型记忆不作为产品证据。动态价格、补贴、库存、赠品仍不进入成稿；同一配置出现无法解释的矛盾时停止。需要登录、脚本渲染或风控而不能获取正文时会要求确认，不绕过网站限制。

## 当前演示的数据模式

2026-10-18 已完成真实 ima OpenAPI 连通、目录、原文与配图调用。随后 ima 原文获取接口返回“资料获取次数已达上限，请明天再尝试”。经资料提供者确认，当前本地预审使用**主办方提供的同一知识库 ZIP 归档缓存**，并在界面顶部、报告、来源记录和导出中明确标为 `offline_archive`，不冒充实时调用。

原 ZIP 仅存于账号自己的**私有 ModelScope 数据仓库**，Studio 使用服务端 Secret 读取；匿名访问原包返回 404。公开 GitHub 和 Studio 代码仓库均不包含知识库原文、原包、图片原件或密钥。归档 SHA256 在服务端校验。缓存读取时间不代表资料发布日期；型号参数与条件以资料本身为准。获得新的 ima 配额后，部署者可将 `IMA_SOURCE_MODE=live` 并重启，恢复实时检索。

当前归档支持 10 个精确消费级型号。不同型号的可用图数不同；小红书需要至少 3 张，素材不足时会追问补图或建议更换平台，不用其他型号图片补足数量。

## 自研 Agent 流程

1. **澄清与策略**：缺少产品、人群、场景或平台时先追问。严格匹配目录中的具体型号、年份和系统版本，拒绝猜测泛称。
2. **知识库读取**：按 P1 型号目录优先检索事实、限制和图片索引；排除跨型号、竞品、历史价格和发现卡冒充规格等情况。ima 只承担资料和图源角色。
3. **事实提取**：模型输出事实、连续原文引文、来源编号、适用条件及待确认事项。规则核对引文确实存在、数值可定位，只接受产品事实类来源。
4. **独立证据复核**：单独调用模型逐条核对“事实陈述是否被它自己的引文支持”。遗漏审核或不能确认的事实在写作前删除，避免“引用存在但推论失真”。
5. **平台写作与编排**：依据人群问题、平台结构、语气、卖点顺序、图数及行动引导生成草稿。仅使用已通过核验的事实和同型号图片。超长或语言异常时最多进行一次写作修订。
6. **独立成稿审核**：再次调用模型逐单元核验标题、导语、正文、CTA 和标签；规则继续拦截无依据数值、价格补贴、绝对化与伪造亲测。漏审单元直接删除，正文无可交付内容时停止。
7. **先审思路，再审终稿**：已核验事实形成可编辑切入点、段落大纲、配图安排、行动引导和适用条件。用户逐步确认后生成终稿；改思路后可复用一小时内已核验的证据，无需重复检索和事实提取，写作仍重新独立审核。
8. **平台排版与确认下载**：小红书提供短段落、话题和有序配图；朋友圈提供短文与图库；公众号提供677px正文宽度、导语、分节标题、穿插配图及图注；海报提供一张主视觉、主副标题和最多三条短卖点。检查标题、字数、图数、小标题及行动引导，未达格式要求的稿件先修改。确认终稿后可下载排版HTML、图文素材ZIP、Markdown与JSON。素材包包含清洁发布文字、去元数据JPG及平台操作说明；公众号需要在后台上传图片并按参考稿排版，应用不连接发布账号。

各模型节点使用独立请求，不复用写作节点的聊天历史。完整系统提示词见 [prompts.py](prompts.py)，业务规则与确定性门控见 [policy.py](policy.py)，编排见 [agent.py](agent.py)。

## 平台和场景规则

| 平台 | 内容结构 | 目标篇幅 | 配图 |
| --- | --- | --- | --- |
| 小红书 | 选购问题、场景短段落、标签、评论或咨询 | 350–650 字 | 3–6 张 |
| 微信公众号 | 标题、导语、小标题论证、适用条件、选购建议 | 650–1000 字 | 2–4 张 |
| 门店朋友圈 | 一句场景、一个核心卖点、到店或私信 | 80–180 字 | 1–3 张 |
| 门店海报 | 主副标题、不超过 3 条短卖点、咨询引导 | 40–120 字 | 1 张 |

场景包括开学季、职场办公、内容创作、家庭换新、企业采购、门店到访、新品首发、节日营销。每个场景有不同的用户问题、卖点顺序和建议现场验证的任务；不是只改变字数。

## 输出与事实边界

完整报告包含赛题要求的四部分：**场景判断 / 知识库依据 / 图文软文 / 核验结果**。事实保留 F 编号、S 来源、短引文与条件；图片保留原注、准确型号、来源模式和建议位置。JSON 导出不含凭证、请求头、签名 URL、内部 media ID、完整原文或服务器本地图片路径。

- 本应用不接入当天价格、补贴、库存、交期或赠品核验，相关内容不进入文案。
- 不虚构实测续航、性能测试、用户评价、销量、奖项或个人体验。
- 不把鸿蒙解释为全部软件兼容；具体软件、账号、网络、配件和版本条件需要逐项确认。
- 不把同一产品不同屏幕、内存或包装版本的特性叠加在一个 SKU 上；未选定版本时按版本分别表述。
- 资料出现无法解释的冲突时停止生成并请人工确认。型号匹配和来源检查不等于人工逐像素验图；上线发布前仍需核对具体款式与视觉内容。
- 模型审核有不确定性；系统提供多层限制及可追溯依据，不保证法律审查或所有语义错误均被发现。

## 本地运行

Python 3.11+，建议使用虚拟环境。依赖见 [requirements.txt](requirements.txt)。

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

通过操作系统环境变量提供服务端配置；不要把真实值写进源码或提交历史。参考 [环境变量示例](.env.example)。应用不会自动读取本地 .env。

```bash
export IMA_OPENAPI_CLIENTID="YOUR_CLIENT_ID"
export IMA_OPENAPI_APIKEY="YOUR_API_KEY"
export IMA_KB_NAME="YOUR_SHARED_KB_NAME"
export LLM_BASE_URL="https://YOUR_OPENAI_COMPATIBLE_SERVICE/v1"
export LLM_API_KEY="YOUR_MODEL_KEY"
export LLM_MODEL="YOUR_JSON_CAPABLE_MODEL"
export IMA_SOURCE_MODE="live"
python app.py
```

Windows PowerShell 对应写法为 `$env:变量名='值'`。默认只从服务端环境读取凭证，界面不要求评委填写密钥。

需要获得授权的本地资料包模式时，设置 `IMA_SOURCE_MODE=archive` 与 `IMA_ARCHIVE_PATH=/absolute/path/to/authorized.zip`。未配置资料或模型、网络失败、权限不足和配额耗尽会明确报错，不输出固定答案。

## ModelScope 部署

SDK 选择 **Gradio 6.29.1**，Python 3.11，入口为 [app.py](app.py)，CPU 2 核 / 8 GB 即可。通过 Git 将本仓库的 `main` 推送至现有 Studio 的 `master` 后部署。请使用安全凭证助手或临时认证环境，不把 Token 写入 remote URL。

在 Studio 的 Secrets 配置 `IMA_OPENAPI_CLIENTID`、`IMA_OPENAPI_APIKEY`、`LLM_API_KEY`；Variables 配置 `IMA_KB_NAME`、`LLM_BASE_URL`、`LLM_MODEL`、`IMA_SOURCE_MODE`。可选 `LLM_MAX_DAILY_CALLS` 为进程级调用预算（当前演示 240），公开队列同一时间只执行一个生成任务、最多等待 8 个。

归档由私有 ModelScope 仓库提供时，再配置 Variables：`IMA_ARCHIVE_URL`、`IMA_ARCHIVE_SHA256`，以及 Secret：`IMA_ARCHIVE_TOKEN`。加载器只允许指定 HTTPS 官方域、校验 SHA256、限制大小，跳转存储域时不转发认证。不要将知识库原包公开上传。公开 Gradio 生成接口无用户身份认证，进程预算不是跨副本的计费额度控制，长时间开放需另加网关配额。

## 安装与验证

```bash
python -m py_compile app.py agent.py ima_client.py llm_client.py policy.py prompts.py preview.py knowledge_store.py
python -m unittest discover -s tests -v
```

当前离线回归 149 项通过（新增风格卡、逐步确认、证据复用、四平台排版与素材包检查），使用合成资料、合成图片和 mock，并阻断外部请求；覆盖引用与数值单位/范围/限定语、年份/系统、价格补贴、审核遗漏、冲突停止、图片健康与数量门槛、来源模式一致性、洞察审核，以及用户误粘贴或模型带入的密钥和签名 URL 不进入导出。它们证明编排及门控行为，不能代替真实模型质量评估。另已执行真实 ima 调用及真实模型任务；成功案例、被拦截记录与限制分别保留在本地预审材料中，等待用户测试与明确批准后再更新远端和提交。

## 代码位置

| 文件 | 职责 |
| --- | --- |
| [app.py](app.py) | Gradio 界面、队列、输入示例、修改和结果展示 |
| [agent.py](agent.py) | 场景策略、四模型节点、门控、可追溯报告与导出 |
| [ima_client.py](ima_client.py) | ima OpenAPI、精确目录检索、图片索引、配额熔断、显式归档模式 |
| [vmall_client.py](vmall_client.py) | 显式官方商城商品页只读读取、精确型号核对、来源与读取时间 |
| [knowledge_store.py](knowledge_store.py) | 服务端私有归档加载与哈希校验 |
| [llm_client.py](llm_client.py) | OpenAI 兼容 JSON 调用、超时、重试和进程预算 |
| [prompts.py](prompts.py) / [policy.py](policy.py) | 完整系统提示词与业务规则 |
| [preview.py](preview.py) | 转义文本、按原比例内嵌图片的成稿预览 |
| [public_payload.py](public_payload.py) | 公开输出边界的敏感字段与签名 URL 脱敏 |
| [tests](tests) | 无外网回归测试 |

初赛提交：项目名称、GitHub 仓库链接、ModelScope 链接、含真实运行结果和完整提示词的作品说明书。演示视频属于复赛材料，初赛不以占位文案或伪造日志代替运行证据。
