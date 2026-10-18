"""Interactive approvals and platform delivery for the local marketing studio."""
from __future__ import annotations

from copy import deepcopy
import os

import gradio as gr

import creation_flow as flow
from llm_client import ModelError, resolve_api_config
from style_cards import (STYLE_FIELDS, PRESET_NAMES, StyleError, get_preset, style_values,
                         style_from_values, infer_style, saved_choices, save_style, delete_style)


def build_studio(examples, fallback_products, desktop_html):
    import agent

    with gr.Blocks(title="知衡 · 华为PC图文营销智能体", analytics_enabled=False) as app:
        state = gr.State({})
        api_state = gr.State({})
        draft_source = gr.State(flow.style_source_key())
        favourites = gr.BrowserState({}, storage_key="zhiheng-style-cards-v1",
                                     secret=os.environ.get("STYLE_STORAGE_SECRET", "zhiheng-browser-style-cards-v1"))
        gr.HTML(desktop_html, elem_id="zh-liquid-header")
        gr.Markdown("## 知衡 · 华为PC图文营销智能体\n确认需求 → 确认风格卡 → 修改并确认思路 → 审阅终稿 → 确认下载。", elem_id="zh-app-title")
        gr.Markdown("每一步都可修改。修改后需要重新确认相应步骤；终稿按所选平台提供文字、图片和排版。", elem_id="zh-guide")
        with gr.Row(elem_id="zh-connection"):
            connection = gr.Markdown("正在读取资料状态…", elem_id="zh-connection-body")
            refresh = gr.Button("刷新资料状态", size="sm")
        with gr.Row(elem_id="zh-workspace"):
            with gr.Column(scale=4, min_width=310, elem_id="zh-inputs"):
                with gr.Accordion("00 / 模型 API 设置（首次使用必填）", open=True):
                    gr.Markdown(
                        "本应用不内置任何 API 密钥。请填写你自己的 OpenAI 兼容服务地址、密钥与模型名后，"
                        "点「应用自定义 API」再开始创作。设置仅保存在本次会话：不写磁盘、不回显密钥、不进入报告与导出；"
                        "接口必须为 HTTPS。"
                    )
                    api_base = gr.Textbox(label="服务地址（Base URL）", placeholder="https://api.deepseek.com/v1",
                                          lines=1, max_length=300)
                    api_key = gr.Textbox(label="API 密钥", type="password", placeholder="仅本次会话使用",
                                         lines=1, max_length=400)
                    api_model = gr.Textbox(label="模型名称（选填）", placeholder="例如 deepseek-chat",
                                           lines=1, max_length=120)
                    with gr.Row():
                        api_save = gr.Button("应用自定义 API", size="sm", variant="primary")
                        api_reset = gr.Button("清空当前设置", size="sm")
                    api_notice = gr.Markdown("当前：尚未配置。填写后点「应用自定义 API」。")
                gr.Markdown("### 01 / 确认营销需求")
                product = gr.Dropdown(fallback_products, label="产品型号", allow_custom_value=True, interactive=True)
                audience = gr.Textbox(label="目标人群", placeholder="例如：经常处理文档和表格的职场人", lines=2)
                with gr.Row():
                    scenario = gr.Dropdown(list(agent.SCENARIOS), value="开学季", label="营销场景")
                    platform = gr.Dropdown(agent.PLATFORMS, value="小红书", label="发布平台")
                goal = gr.Dropdown(["种草了解", "选购决策", "到店体验", "企业咨询"], value="种草了解", label="营销目标")
                requirements = gr.Textbox(label="补充要求 / 华为官方商城商品链接", lines=3,
                                          placeholder="门店信息、内容要求，或 https://www.vmall.com/product/商品编号.html")
                with gr.Row(elem_id="zh-examples"):
                    example_buttons = [gr.Button(label, size="sm") for label in ["校园 · 小红书", "办公 · 公众号", "到店 · 朋友圈"]]
                brief_button = gr.Button("确认需求，进入风格选择", variant="primary")
                gr.Markdown("### 02 / 选择或定义风格", elem_id="zh-style-title")
                preset = gr.Dropdown(PRESET_NAMES, value="专业可信", label="内置风格", interactive=True)
                with gr.Row():
                    saved = gr.Dropdown([], value=None, label="我的常用风格", interactive=True)
                    delete_button = gr.Button("删除常用", size="sm")
                gr.Markdown("可直接编辑下面的风格卡；也可输入描述、粘贴参考文案，或同时提供两者来提炼个人风格。")
                description = gr.Textbox(label="期望风格描述（选填）", placeholder="专业可信、口语化、少用感叹号", lines=2, max_length=1500)
                reference = gr.Textbox(label="参考案例 / 以往营销软文（选填）", placeholder="粘贴你的以往文案，只提炼表达方式。", lines=4, max_lines=8, max_length=8000)
                infer_button = gr.Button("提炼为可编辑风格卡")
                with gr.Accordion("风格卡 · 可逐项修改", open=True):
                    defaults = get_preset("专业可信")
                    card_inputs = [gr.Textbox(label=label, value=defaults[key], lines=1 if key == "name" else 2,
                                              max_lines=4, max_length=60 if key == "name" else 600)
                                   for key, label in STYLE_FIELDS]
                with gr.Row():
                    save_button = gr.Button("保存为常用风格")
                    style_button = gr.Button("确认当前风格卡", variant="primary")
                style_notice = gr.Markdown("常用风格只保存在当前浏览器；保存的卡片不含参考文案。")
                gr.Markdown("提示：完成需求、风格与思路后才会调用模型；未配置 API 时点击生成会提示先配置。",
                            elem_id="zh-api-hint")
            with gr.Column(scale=7, min_width=360, elem_id="zh-results"):
                status = gr.Markdown("### 请先确认需求\n可先点击一个示例，再依次确认风格与思路。", elem_id="zh-status")
                gr.Markdown("### 03 / 先看思路，再出终稿\n思路使用已核验事实和同型号配图；可修改每项内容后确认。", elem_id="zh-plan-title")
                idea_button = gr.Button("生成创作思路", interactive=False, variant="primary")
                plan_inputs = [gr.Textbox(label=label, lines=4 if key in {"outline", "images"} else 2,
                                         max_lines=8, max_length=2400) for key, label in flow.PLAN_FIELDS]
                with gr.Accordion("思路阶段的事实依据与配图", open=False):
                    idea_facts = gr.JSON(label="已核验事实", value=[])
                    idea_gallery = gr.Gallery(label="可用同型号配图", columns=3, height=240, object_fit="contain")
                with gr.Row():
                    plan_button = gr.Button("确认当前创作思路", interactive=False)
                    final_button = gr.Button("生成图文终稿", interactive=False, variant="primary", elem_id="zh-generate")
                gr.Markdown("### 04 / 审阅并确认图文终稿\n修改上方思路即可重新确认、生成；下载前需要确认终稿。")
                with gr.Tabs(elem_id="zh-tabs"):
                    with gr.Tab("平台图文预览"):
                        preview = gr.HTML("<p>确认思路并生成后，显示当前平台的图文排版。</p>", elem_id="zh-preview")
                    with gr.Tab("可复制文案与配图"):
                        copy_text = gr.Textbox(label="平台文案", lines=14, max_lines=30, interactive=False, buttons=["copy"])
                        gallery = gr.Gallery(label="按排版顺序使用的同型号配图", columns=2, height=330, object_fit="contain")
                        delivery_notes = gr.Markdown("公众号交付导语、分节标题、图文穿插排版；素材包内附图片和使用步骤。")
                    with gr.Tab("报告与核验"):
                        report = gr.Markdown("生成后在此显示事实依据、图文方案与核验结果。", elem_id="zh-report")
                        checks = gr.JSON(label="内容和平台格式核验", value={})
                final_confirm = gr.Button("确认终稿，提供下载", interactive=False, variant="primary")
                with gr.Row():
                    html_file = gr.File(label="平台排版 HTML", file_types=[".html"], interactive=False)
                    bundle_file = gr.File(label="图文素材包 ZIP", file_types=[".zip"], interactive=False)
                with gr.Row():
                    md_file = gr.File(label="完整核验报告 Markdown", file_types=[".md"], interactive=False)
                    json_file = gr.File(label="结构化核验 JSON", file_types=[".json"], interactive=False)
        gr.Markdown("知衡 · 团队独立开发，非华为官方产品。当前为本地测试版；确认终稿只提供本地下载。", elem_id="zh-footer")

        request_inputs = [product, audience, scenario, platform, goal, requirements]
        source_inputs = [description, reference]
        all_inputs = [state, *request_inputs, *source_inputs, *card_inputs, *plan_inputs]
        downloads = [html_file, bundle_file, md_file, json_file]
        stage_buttons = [idea_button, plan_button, final_button, final_confirm]
        shared_outputs = [state, status, *stage_buttons, *downloads, *plan_inputs, idea_facts, idea_gallery,
                          preview, copy_text, gallery, report, checks, delivery_notes, draft_source,
                          *card_inputs, description, reference, style_notice, saved, favourites]

        def lock_files():
            return {component: None for component in downloads}

        def stages(*enabled):
            return {button: gr.update(interactive=index in enabled) for index, button in enumerate(stage_buttons)}

        def parts(args):
            current = args[0] or {}
            request = flow.request_from_values(*args[1:7])
            desc, ref = args[7:9]
            card = style_from_values(*args[9:16])
            plan = {key: value for (key, _), value in zip(flow.PLAN_FIELDS, args[16:21])}
            return current, request, card, plan, desc, ref

        def error(exc):
            message = str(exc) if isinstance(exc, (flow.FlowError, StyleError)) else "本次操作暂未完成，请稍后重试。"
            return {status: "### 请检查后继续\n" + message, **lock_files()}

        def confirm_brief(*args):
            try:
                request = flow.request_from_values(*args)
                new = flow.confirm_brief(request)
                return {state: new, status: "### ✓ 需求已确认\n请选择或提炼风格卡，编辑后点击「确认当前风格卡」。", **stages(), **lock_files()}
            except Exception as exc:
                return error(exc)

        def invalidate_request():
            return {state: {}, status: "### 需求已修改\n请重新确认需求，后续风格与思路确认也需更新。", **stages(), **lock_files()}

        def invalidate_style(current):
            new = {k: deepcopy(v) for k, v in (current or {}).items() if k in {"request_key", "request"}}
            return {state: new, status: "### 风格已修改\n请确认当前风格卡，再重新生成思路。", **stages(), **lock_files()}

        def invalidate_plan(current):
            new = {k: deepcopy(v) for k, v in (current or {}).items() if k not in {"plan_key", "final_key", "final_result"}}
            return {state: new, status: "### 思路已修改\n请重新确认当前思路，再生成终稿。", **(stages(0, 1) if new.get("prepared") else stages()), **lock_files()}

        def load_style(name, current, stored=None):
            try:
                if stored is not None:
                    card = (stored or {}).get(name)
                    if not card:
                        raise StyleError("请选择已保存的风格。")
                else:
                    card = get_preset(name)
                updates = invalidate_style(current)
                updates.update({component: value for component, value in zip(card_inputs, style_values(card))})
                updates.update({description: "", reference: "", draft_source: flow.style_source_key()})
                return updates
            except Exception as exc:
                return error(exc)

        def save_api(base, key, model):
            try:
                config = resolve_api_config({"base_url": base, "api_key": key, "model": model})
            except ModelError as exc:
                return {}, "### 设置未生效\n" + str(exc)
            if not config:
                return {}, "当前：尚未配置。填写服务地址与密钥后再点击「应用自定义 API」。"
            host = config["base_url"].split("://", 1)[-1].split("/", 1)[0]
            return config, f"✓ 已就绪：模型 {config['model']} · 地址 {host}。密钥仅保存在本次会话，不回显。"

        def reset_api():
            return {}, "已清空当前设置；继续创作前需要重新填写 API。"

        def extract_style(desc, ref, base, current, api):
            try:
                if not api:
                    return {status: ("### 请先配置模型 API\n提炼风格同样需要模型服务。请先在左上「00 / 模型 API 设置」"
                                     "填写并应用你自己的 API。")}
                card = infer_style(desc or "", ref or "", base, api_config=api)
                updates = invalidate_style(current)
                updates.update({component: value for component, value in zip(card_inputs, style_values(card))})
                updates.update({draft_source: flow.style_source_key(desc, ref), status: "### 风格卡已提炼\n请检查并编辑七项表达规则，然后确认使用。"})
                return updates
            except Exception as exc:
                return error(exc)

        def approve_style(*args):
            try:
                current, request, card, _, desc, ref = parts(args[:-1])
                new = flow.confirm_style(current, request, card, desc, ref, args[-1])
                return {state: new, status: "### ✓ 风格卡已确认\n点击「生成创作思路」，先核对事实和内容安排。", **stages(0), **lock_files()}
            except Exception as exc:
                return error(exc)

        NEED_API = ("### 请先配置模型 API\n"
                    "本应用不内置密钥。请在左上「00 / 模型 API 设置」填写服务地址、密钥（和模型名），"
                    "点「应用自定义 API」后再生成。")

        def create_idea(*args):
            try:
                api = args[21] if len(args) > 21 else None
                if not api:
                    return {status: NEED_API}
                current, request, card, _, desc, ref = parts(args)
                flow.check_style(current, request, card, desc, ref)
                result = agent.run_task(**request, phase="plan", style_card=card, api_config=api)
                new = flow.attach_idea(current, result)
                if result.get("status") != "plan_ready":
                    return {state: new, status: result.get("report", "资料暂不可用，请重试。"), **stages(0), **lock_files()}
                plan = result["plan"]
                return {state: new, status: "### 创作思路已准备好\n请修改下方切入点、大纲与配图安排，然后点击「确认当前创作思路」。",
                        **{component: plan[key] for component, (key, _) in zip(plan_inputs, flow.PLAN_FIELDS)},
                        idea_facts: result["facts"], idea_gallery: [(i["path"], i.get("caption", "")) for i in result["images"]],
                        **stages(0, 1), **lock_files()}
            except Exception as exc:
                return error(exc)

        def approve_plan(*args):
            try:
                current, request, card, plan, desc, ref = parts(args)
                new = flow.confirm_plan(current, request, card, plan, desc, ref)
                return {state: new, status: "### ✓ 创作思路已确认\n点击「生成图文终稿」，按当前平台要求写作、编排并独立审核。", **stages(0, 1, 2), **lock_files()}
            except Exception as exc:
                return error(exc)

        def create_final(*args):
            try:
                api = args[21] if len(args) > 21 else None
                if not api:
                    return {status: NEED_API}
                current, request, card, plan, desc, ref = parts(args)
                kwargs = flow.generation_args(current, request, card, plan, desc, ref)
                result = agent.run_task(**request, api_config=api, **kwargs)
                new = flow.attach_final(current, result)
                if result.get("status") != "ready":
                    return {state: new, status: result.get("report", "本次暂未完成，请重试。"), **stages(0, 1, 2), **lock_files()}
                platform_ready = result.get("checks", {}).get("platform_ready", False)
                notice = ("### 图文终稿已生成，等待你确认\n请审阅平台预览、文字和配图。确认终稿后提供下载。" if platform_ready else
                          "### 当前为待修改草稿（仍可确认下载，材料带草稿标记）\n"
                          "平台格式尚未全部达标，未达标项见「报告与核验」。"
                          "你可以先确认并下载留存：HTML 顶部与 ZIP 内「草稿说明.txt」都会标明“草稿 · 未达标”，"
                          "对外发布前请按提示修改。")
                return {state: new, status: notice, preview: result["preview_html"],
                        copy_text: result.get("publish_copy", result["copy_text"]),
                        gallery: [(i["path"], i.get("placement", "") + " · " + i.get("caption", "")) for i in result["images"]],
                        report: result["report"], checks: result["checks"], delivery_notes: result.get("delivery_notes", ""),
                        **stages(0, 1, 2, 3), **lock_files()}
            except Exception as exc:
                return error(exc)

        def approve_final(*args):
            try:
                current, request, card, plan, desc, ref = parts(args)
                new = flow.confirm_final(current, request, card, plan, desc, ref)
                result = new["final_result"]
                files = {"html_file": result.get("export_html"), "bundle_file": result.get("export_bundle"),
                         "md_file": result.get("export_markdown"), "json_file": result.get("export_json")}
                if not any(files.values()):
                    return {status: "### 暂未生成下载文件\n终稿已确认，但导出文件缺失。请重新生成终稿后再确认；本次没有可下载材料。"}
                if new.get("final_draft"):
                    status_text = ("### ✓ 终稿已确认（草稿）\n平台格式未全部达标，已按草稿下载："
                                   "HTML 顶部有“草稿 · 未达标”横幅，ZIP 内含「草稿说明.txt」。对外发布前请先按核验提示修改。")
                else:
                    status_text = ("### ✓ 终稿已确认\n可下载平台排版、文字及图片素材包。"
                                   "公众号请按素材包说明在后台上传图片并排版。")
                return {state: new, status: status_text,
                        html_file: files["html_file"], bundle_file: files["bundle_file"],
                        md_file: files["md_file"], json_file: files["json_file"], **stages(0, 1, 2, 3)}
            except Exception as exc:
                return error(exc)

        def store_style(stored, *values):
            try:
                card = style_from_values(*values)
                updated = save_style(stored, card)
                return {favourites: updated, saved: gr.update(choices=saved_choices(updated), value=card["name"]),
                        style_notice: f"已将「{card['name']}」保存在当前浏览器。保存不代替确认使用。"}
            except Exception as exc:
                return {style_notice: str(exc) if isinstance(exc, StyleError) else "暂未保存，请重试。"}

        def remove_style(stored, name):
            try:
                updated = delete_style(stored, name)
                return {favourites: updated, saved: gr.update(choices=saved_choices(updated), value=None),
                        style_notice: "已删除常用风格；正在编辑的风格卡可继续使用。"}
            except Exception as exc:
                return {style_notice: str(exc) if isinstance(exc, StyleError) else "暂未删除，请重试。"}

        event = dict(outputs=shared_outputs, api_visibility="private", concurrency_limit=1,
                     concurrency_id="zhiheng_creation", trigger_mode="once")
        brief_button.click(confirm_brief, inputs=request_inputs, **event)
        style_button.click(approve_style, inputs=[*all_inputs, draft_source], **event)
        infer_button.click(extract_style, inputs=[description, reference, preset, state, api_state], **event)
        api_save.click(save_api, inputs=[api_base, api_key, api_model], outputs=[api_state, api_notice],
                       api_visibility="private", queue=False)
        api_reset.click(reset_api, inputs=[], outputs=[api_state, api_notice],
                        api_visibility="private", queue=False)
        preset.input(lambda name, current: load_style(name, current), inputs=[preset, state], **event)
        saved.input(lambda name, current, stored: load_style(name, current, stored), inputs=[saved, state, favourites], **event)
        save_button.click(store_style, inputs=[favourites, *card_inputs], **event)
        delete_button.click(remove_style, inputs=[favourites, saved], **event)
        favourites.change(lambda stored: gr.update(choices=saved_choices(stored), value=None), inputs=[favourites], outputs=[saved],
                          api_visibility="private", queue=False)
        idea_button.click(create_idea, inputs=[*all_inputs, api_state], **event)
        plan_button.click(approve_plan, inputs=all_inputs, **event)
        final_button.click(create_final, inputs=[*all_inputs, api_state], **event)
        final_confirm.click(approve_final, inputs=all_inputs, **event)
        for component in request_inputs:
            component.input(invalidate_request, inputs=[], **{**event, "trigger_mode": "always_last"})
        for component in [*source_inputs, *card_inputs]:
            component.input(invalidate_style, inputs=[state], **{**event, "trigger_mode": "always_last"})
        for component in plan_inputs:
            component.input(invalidate_plan, inputs=[state], **{**event, "trigger_mode": "always_last"})
        for index, button in enumerate(example_buttons):
            def use_example(index=index):
                entry = examples[index]
                return tuple(entry[key] for key in flow.REQUEST_FIELDS)
            button.click(use_example, inputs=[], outputs=request_inputs, api_visibility="private", queue=False).then(
                invalidate_request, inputs=[], **event)

        def refresh_connection(current):
            products = agent.get_products() or fallback_products
            return agent.get_connection_status(), gr.update(choices=products, value=current or None)
        refresh.click(refresh_connection, inputs=[product], outputs=[connection, product], api_visibility="private",
                      concurrency_limit=1, concurrency_id="zhiheng_creation")
        app.load(refresh_connection, inputs=[product], outputs=[connection, product], api_visibility="private",
                 concurrency_limit=1, concurrency_id="zhiheng_creation")
    return app
