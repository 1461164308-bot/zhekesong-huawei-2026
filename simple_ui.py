"""Minimal conversation workspace; the professional approval flow stays separate."""
from __future__ import annotations

import gradio as gr

from policy import PLATFORM_RULES


def build_simple(api_state, fallback_products, ima_state=None):
    from contextlib import nullcontext
    import agent

    def source(ima):
        # Route catalog and retrieval to the session's live ima settings, if any.
        return agent.ima_session(ima or None) if ima_state is not None else nullcontext()

    ima_input = [ima_state] if ima_state is not None else []
    state = gr.State({})
    delivery = gr.State({})
    with gr.Row(elem_id='zh-simple-layout'):
        with gr.Column(scale=2, min_width=280, elem_id='zh-simple-brief'):
            gr.Markdown('### 先告诉我三件事\n可以先聊细节，也可以直接生成。产品泛称可用于交流，生成前需要明确具体型号。')
            product = gr.Dropdown(fallback_products, value=None, allow_custom_value=True,
                                  label='产品类型', info='选择具体型号，或先输入你想了解的产品类型。',
                                  elem_id='zh-simple-product')
            product_hint = gr.Markdown(
                '可以直接手输型号（如「matebook d14 2024」），离开输入框会自动匹配目录里的准确型号；'
                '匹配不到会列出候选，不会替你猜。',
                elem_id='zh-simple-product-hint')
            audience = gr.Textbox(label='用户类型', placeholder='例如：大学新生、办公人群', max_length=300,
                                 elem_id='zh-simple-audience')
            platform = gr.Dropdown(list(PLATFORM_RULES), value='小红书', label='发布平台',
                                   elem_id='zh-simple-platform')
            with gr.Accordion('模型连接设置（与专业模式共用）', open=False, elem_id='zh-simple-api-settings') as api_settings:
                gr.Markdown('未内置密钥。首次使用需配置；设置只保存在本次会话。')
                api_base = gr.Textbox(label='极简服务地址', placeholder='https://api.deepseek.com/v1', max_length=300)
                api_key = gr.Textbox(label='极简 API 密钥', type='password', max_length=400)
                api_model = gr.Textbox(label='极简模型名称', placeholder='deepseek-chat', max_length=120)
                api_save = gr.Button('应用模型设置', elem_id='zh-simple-api-save')
                api_reset = gr.Button('清空模型设置', elem_id='zh-simple-api-reset')
                api_notice = gr.Markdown('可使用本次会话在任一模式应用的配置，或服务端模型配置。')
            with gr.Accordion('当前信息摘要', open=False):
                summary = gr.Markdown('填写三项基本信息后，即可开始对话或生成。', elem_id='zh-simple-summary')
        with gr.Column(scale=4, min_width=320, elem_id='zh-simple-conversation'):
            notice = gr.Markdown('### 你决定什么时候开始写\nAI 会根据你的回答继续询问。没有更多要求时，直接点「按当前信息生成」。',
                                 elem_id='zh-simple-status')
            chat = gr.Chatbot(value=[], label='创作需求对话', height=320, render_markdown=False,
                              allow_tags=False, allow_file_downloads=False, elem_id='zh-simple-chat')
            message = gr.Textbox(label='补充文案要求', placeholder='语气、使用场景、篇幅、重点、行动引导……',
                                 lines=2, max_length=400, info='每轮最多400字，可分轮补充。', elem_id='zh-simple-message')
            with gr.Row():
                start = gr.Button('让 AI 引导我', elem_id='zh-simple-start')
                send = gr.Button('发送并继续', elem_id='zh-simple-send')
            generate = gr.Button('按当前信息生成', variant='primary', interactive=True, elem_id='zh-simple-generate')
            gr.Markdown('尚未发送的补充文字也会纳入生成。未提供的偏好会明确按默认处理，不要求答完所有问题。')
    with gr.Column(visible=False, elem_id='zh-simple-result') as result_panel:
        with gr.Tabs():
            with gr.Tab('图文预览'):
                preview = gr.HTML('<p>生成后在此审阅图文，不会自动发布。</p>', elem_id='zh-simple-preview')
            with gr.Tab('文字与配图'):
                copy_text = gr.Textbox(label='极简平台文案', lines=10, interactive=False, buttons=['copy'])
                gallery = gr.Gallery(label='极简同型号配图', columns=3, height=230)
            with gr.Tab('来源与核验'):
                report = gr.Markdown('生成后提供来源与审核报告。')
                checks = gr.JSON(label='极简核验结果', value={})
        confirm = gr.Button('确认当前文案，解锁下载', interactive=False, elem_id='zh-simple-confirm')
        with gr.Row():
            html_file = gr.File(label='极简排版 HTML', interactive=False)
            bundle_file = gr.File(label='极简素材 ZIP', interactive=False)
        with gr.Row():
            md_file = gr.File(label='极简核验 Markdown', interactive=False)
            json_file = gr.File(label='极简核验 JSON', interactive=False)
    downloads = [html_file, bundle_file, md_file, json_file]
    outputs = [state, delivery, notice, summary, chat, message, confirm, preview, copy_text, gallery, report, checks, result_panel, api_settings, *downloads]

    def clear_result():
        return {result_panel: gr.update(visible=False), delivery: {}, confirm: gr.update(interactive=False), preview: '<p>当前信息已变化，请重新生成并审阅。</p>',
                copy_text: '', gallery: [], report: '等待当前版本的核验结果。', checks: {},
                **{component: None for component in downloads}}

    def safe_error(exc):
        from llm_client import ModelError
        from public_payload import sanitize_public
        text = str(exc) if isinstance(exc, ModelError) or type(exc).__name__ == 'SimpleModeError' else '本次操作未完成，请稍后重试。'
        updates = {notice: '### 请检查后继续\n' + sanitize_public(text), **clear_result()}
        if 'API' in text:
            updates[api_settings] = gr.update(open=True)
        return updates

    def conversation_updates(payload):
        from public_payload import sanitize_public
        return {state: payload['state'], chat: sanitize_public(payload.get('history', [])),
                summary: sanitize_public(payload.get('summary', '')), message: '', **clear_result()}

    def simple_generate(current, selected_product, selected_audience, selected_platform, pending, api, ima=None):
        import simple_flow
        from creation_flow import digest
        try:
            with source(ima):
                payload = simple_flow.generate_now(current or {}, selected_product, selected_audience, selected_platform,
                                                   pending_message=pending or '', api_config=api or None)
            updates = conversation_updates(payload)
            result = payload.get('result') or {}
            if result.get('status') != 'ready':
                return {**updates, notice: result.get('report', '当前信息不足或资料未通过核验，请补充后重试。')}
            signature = digest([selected_product, selected_audience, selected_platform, payload['state'], ''])
            draft = result.get('checks', {}).get('platform_ready') is False
            updates.update({result_panel: gr.update(visible=True), delivery: {'signature': signature, 'result': result}, confirm: gr.update(interactive=True),
                            notice: '### 草稿已生成，等待审阅\n平台格式尚未全部达标，确认后可下载带草稿标记的材料。' if draft else '### 文案已生成，等待审阅\n核对文字、配图和来源后，点击确认解锁下载。',
                            preview: result.get('preview_html', ''), copy_text: result.get('publish_copy', result.get('copy_text', '')),
                            gallery: [(i['path'], i.get('caption', '')) for i in result.get('images', [])],
                            report: result.get('report', ''), checks: result.get('checks', {})})
            return updates
        except Exception as exc:
            return safe_error(exc)

    def simple_start(selected_product, selected_audience, selected_platform, api, pending='', ima=None):
        import simple_flow
        try:
            with source(ima):
                if pending and pending.strip():
                    payload = simple_flow.continue_conversation({}, selected_product, selected_audience, selected_platform,
                                                                pending, api_config=api or None)
                else:
                    payload = simple_flow.start_conversation(selected_product, selected_audience, selected_platform, api_config=api or None)
            return {**conversation_updates(payload), notice: '### AI 正在了解你的需求\n按你的节奏补充，也可以随时生成。'}
        except Exception as exc:
            return safe_error(exc)

    def simple_send(current, selected_product, selected_audience, selected_platform, reply, api, ima=None):
        import simple_flow
        try:
            with source(ima):
                payload = simple_flow.continue_conversation(current or {}, selected_product, selected_audience, selected_platform,
                                                            reply or '', api_config=api or None)
            return {**conversation_updates(payload), notice: '### 已记录你的补充\n继续回答，或直接按当前信息生成。'}
        except Exception as exc:
            return safe_error(exc)

    def simple_confirm(record, current, selected_product, selected_audience, selected_platform, pending):
        from creation_flow import digest
        from os.path import isfile
        signature = digest([selected_product, selected_audience, selected_platform, current or {}, pending or ''])
        result = (record or {}).get('result') or {}
        if (record or {}).get('signature') != signature or result.get('status') != 'ready' or not result.get('copy_text'):
            return {notice: '### 当前信息尚未审阅或已变化\n请按当前信息重新生成，再确认下载。', **clear_result()}
        paths = [result.get(key) for key in ('export_html','export_bundle','export_markdown','export_json')]
        available = [path for path in paths if path]
        if not available or not all(isinstance(path, str) and isfile(path) for path in available):
            return {notice: '### 下载文件缺失\n请重新生成并确认；本次未解锁下载。', **clear_result()}
        draft = result.get('checks', {}).get('platform_ready') is False
        return {notice: '### 已确认草稿，可下载\n材料保留未达平台格式的草稿标记，对外发布前请修改。' if draft else '### 已确认，可下载\n请核对具体型号、图片和使用条件后发布。',
                **dict(zip(downloads, paths))}

    def simple_invalidate_basics():
        return {state: {}, chat: [], summary: '三项基础信息已变化，请重新开始引导或直接生成。',
                notice: '### 基础信息已更新\n旧对话已重置，填写中的补充文字仍保留。', **clear_result()}

    def simple_invalidate_draft():
        return {notice: '### 已补充新要求\n发送继续交流，或按当前信息重新生成。', **clear_result()}

    def simple_save_api(base, key, model):
        from llm_client import resolve_api_config, ModelError
        try:
            config = resolve_api_config({'base_url':base, 'api_key':key, 'model':model})
            text = '已应用模型配置，仅本次会话有效。' if config else '尚未配置，请填写服务地址和密钥。'
            return {**clear_result(), api_state:config or {}, api_notice:text, api_key:'', notice:text}
        except ModelError as exc:
            return {**safe_error(exc), api_state:{}, api_notice:'模型配置未生效，请检查后重试。'}

    def simple_reset_api():
        text = '会话模型配置已清空，生成前请重新配置。'
        return {**clear_result(), api_state:{}, api_base:'', api_key:'', api_model:'', api_notice:text, notice:text}

    def simple_match_product(text, ima=None):
        """手输型号自动匹配目录：命中就回填准确型号，命中不了给出候选提示。"""
        import agent
        from policy import resolve_product
        try:
            with source(ima):
                products = agent.get_products()
        except Exception:
            products = []
        result = resolve_product(text, products or fallback_products)
        if result['status'] == 'matched':
            return gr.update(value=result['product']), '✓ ' + result['message']
        return gr.update(), result['message']

    event = dict(outputs=outputs, api_visibility='private', concurrency_limit=1,
                 concurrency_id='zhiheng_creation', trigger_mode='once')
    start.click(simple_start, inputs=[product, audience, platform, api_state, message, *ima_input], **event)
    send.click(simple_send, inputs=[state, product, audience, platform, message, api_state, *ima_input], **event)
    message.submit(simple_send, inputs=[state, product, audience, platform, message, api_state, *ima_input], **event)
    generate.click(simple_generate, inputs=[state, product, audience, platform, message, api_state, *ima_input], **event)
    confirm.click(simple_confirm, inputs=[delivery, state, product, audience, platform, message], **event)
    for component in (product, audience, platform):
        component.input(simple_invalidate_basics, inputs=[], **{**event, 'trigger_mode':'always_last'})
    product.blur(simple_match_product, inputs=[product, *ima_input], outputs=[product, product_hint],
                 api_visibility='private', queue=False)
    message.input(simple_invalidate_draft, inputs=[], **{**event, 'trigger_mode':'always_last'})
    api_outputs = [api_state, api_base, api_key, api_model, api_notice, *outputs]
    api_events = [api_save.click(simple_save_api, inputs=[api_base,api_key,api_model],
                                **{**event,'outputs':api_outputs}),
                  api_reset.click(simple_reset_api, inputs=[], **{**event,'outputs':api_outputs})]
    return locals()
