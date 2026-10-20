"""Mode entry and visibility tests; building components never calls services."""
import unittest
from unittest.mock import patch
from studio_ui import build_studio
from app import EXAMPLES, FALLBACK_PRODUCTS
from visual_theme import DESKTOP_HTML


class ModeEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = build_studio(EXAMPLES, FALLBACK_PRODUCTS, DESKTOP_HTML)

    def component(self, name):
        return next((c for c in self.app.blocks.values() if getattr(c, 'elem_id', None) == name), None)

    def callback(self, name):
        result = next((f for f in self.app.fns.values() if f.fn and f.fn.__name__ == name), None)
        self.assertIsNotNone(result, 'missing mode callback: ' + name)
        return result

    def test_mode_switch_only_changes_visibility_not_user_inputs_or_models(self):
        targets = {'enter_quick': 'zh-quick-workspace', 'enter_simple': 'zh-simple-workspace',
                   'enter_professional': 'zh-workspace', 'return_to_modes': 'zh-mode-home'}
        allowed = {'zh-mode-home','zh-quick-workspace','zh-simple-workspace','zh-workspace','zh-guide',
                   'zh-mode-bar','zh-mode-label','zh-connection-details'}
        with patch('agent.run_task', side_effect=AssertionError('mode switching must not generate')):
            for callback, visible_id in targets.items():
                fn = self.callback(callback)
                self.assertEqual(fn.inputs, [])
                self.assertFalse(fn.queue)
                result = fn.fn()
                for component in result:
                    self.assertIn(component.elem_id, allowed)
                for panel in ('zh-mode-home','zh-quick-workspace','zh-simple-workspace','zh-workspace'):
                    self.assertEqual(result[self.component(panel)]['visible'], panel == visible_id)

    def test_free_text_product_matching_hint_is_present(self):
        """两种模式都提供手输型号的自动匹配提示。"""
        self.assertIsNotNone(self.component('zh-product-hint'), '专业模式缺少型号匹配提示')
        self.assertIsNotNone(self.component('zh-simple-product-hint'), '极简模式缺少型号匹配提示')

    def test_quick_mode_offers_visit_presets(self):
        """没灵感时可以直接点场景，不必自己想一句见闻。"""
        presets = [component for component in self.app.blocks.values()
                   if str(getattr(component, 'elem_id', '') or '').startswith('zh-quick-preset-')]
        self.assertGreaterEqual(len(presets), 8, '快发模式应给出门店场景预选卡')
        self.assertIsNotNone(self.component('zh-quick-visit'), '见闻输入框应在')
        self.assertIsNotNone(self.component('zh-quick-presets-hint'), '预选卡上方要有一句引导')

    def test_quick_mode_has_gallery_and_bundle(self):
        for name in ('zh-quick-gallery-0', 'zh-quick-images-0', 'zh-quick-pack', 'zh-quick-bundle'):
            self.assertIsNotNone(self.component(name), f'快发模式缺少 {name}')

    def test_simple_mode_has_three_basic_fields_and_generation_is_always_available(self):
        for name in ('zh-simple-product', 'zh-simple-audience', 'zh-simple-platform', 'zh-simple-chat'):
            self.assertIsNotNone(self.component(name), name)
        button = self.component('zh-simple-generate')
        self.assertIsNotNone(button)
        self.assertTrue(button.interactive, 'generation cannot require answering all follow-up questions')
        self.assertIsNotNone(self.component('zh-simple-api-settings'))
        self.assertFalse(self.component('zh-simple-result').visible, 'empty result and download controls should not crowd the initial form')

    def test_generate_uses_pending_input_without_requiring_a_conversation(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        backend = Mock(return_value={'state': {'turns': []}, 'history': [], 'summary': '当前信息',
                                     'result': {'status':'ready', 'copy_text':'合成文案', 'preview_html':'<p>合成预览</p>',
                                                'images':[], 'report':'核验', 'checks':{'platform_ready':True}}})
        fake = SimpleNamespace(generate_now=backend, SimpleModeError=ValueError)
        fn = self.callback('simple_generate')
        with patch.dict(sys.modules, {'simple_flow': fake}):
            result = fn.fn({}, 'HUAWEI MateBook Pro S', '大学生', '门店朋友圈', '尚未发送的要求', {'synthetic':True})
        backend.assert_called_once_with({}, 'HUAWEI MateBook Pro S', '大学生', '门店朋友圈',
                                        pending_message='尚未发送的要求', api_config={'synthetic':True})
        self.assertTrue(result[self.component('zh-simple-confirm')]['interactive'])
        for output in fn.outputs:
            if output.__class__.__name__ == 'File':
                self.assertIsNone(result[output], 'generation must not bypass final review')

    def test_chat_start_and_reply_use_the_model_service_and_display_its_question(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        history = [{'role':'assistant', 'content':'这篇文案主要用于哪个使用场景？'}]
        payload = {'state': {'history':history}, 'history':history, 'summary':'需求摘要', 'result':None}
        begin, follow = Mock(return_value=payload), Mock(return_value=payload)
        fake = SimpleNamespace(start_conversation=begin, continue_conversation=follow, SimpleModeError=ValueError)
        with patch.dict(sys.modules, {'simple_flow':fake}):
            started = self.callback('simple_start').fn('产品', '学生', '小红书', {'synthetic':True})
            answered = self.callback('simple_send').fn(payload['state'], '产品', '学生', '小红书', '开学季，自然语气', {'synthetic':True})
        self.assertEqual(started[self.component('zh-simple-chat')], history)
        self.assertEqual(answered[self.component('zh-simple-chat')], history)
        begin.assert_called_once()
        follow.assert_called_once_with(payload['state'], '产品', '学生', '小红书', '开学季，自然语气', api_config={'synthetic':True})

    def test_simple_downloads_require_current_reviewed_result_and_real_files(self):
        import tempfile
        from pathlib import Path
        from creation_flow import digest
        fn = self.callback('simple_confirm')
        current = {'history':[]}
        basic = ['产品', '学生', '门店朋友圈']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'review.html'
            path.write_text('<p>synthetic</p>', encoding='utf-8')
            record = {'signature':digest([*basic,current,'']),
                      'result':{'status':'ready','copy_text':'合成文案','export_html':str(path)}}
            approved = fn.fn(record,current,*basic,'')
            files = [c for c in fn.outputs if c.__class__.__name__ == 'File']
            self.assertIn(str(path), [approved.get(c) for c in files])
            for pending in ['新要求']:
                stale = fn.fn(record,current,*basic,pending)
                self.assertTrue(all(stale.get(c) is None for c in files))
            path.unlink()
            missing = fn.fn(record,current,*basic,'')
            self.assertTrue(all(missing.get(c) is None for c in files))

    def test_simple_edits_invalidate_output_without_silently_reusing_chat(self):
        changed = self.callback('simple_invalidate_basics').fn()
        self.assertEqual(changed[self.component('zh-simple-chat')], [])
        self.assertFalse(changed[self.component('zh-simple-confirm')]['interactive'])
        draft = self.callback('simple_invalidate_draft').fn()
        self.assertNotIn(self.component('zh-simple-chat'), draft)
        self.assertFalse(draft[self.component('zh-simple-confirm')]['interactive'])
        for output in self.callback('simple_generate').outputs:
            if output.__class__.__name__ == 'File':
                self.assertIsNone(changed[output])
                self.assertIsNone(draft[output])

    def test_simple_model_settings_share_session_api_and_relock_downloads(self):
        fn = self.callback('simple_save_api')
        result = fn.fn('https://api.example.com/v1','synthetic-mode-key','custom-model')
        shared_api_state = self.callback('save_api').outputs[0]
        self.assertEqual(result[shared_api_state]['model'],'custom-model')
        self.assertFalse(result[self.component('zh-simple-confirm')]['interactive'])
        bad = fn.fn('http://api.example.com','synthetic-mode-key','model')
        self.assertEqual(bad[shared_api_state],{})
        reset = self.callback('simple_reset_api').fn()
        self.assertEqual(reset[shared_api_state],{})
        self.assertTrue(set(result).issubset(set(fn.outputs)))

    def test_starting_guidance_does_not_discard_an_unsent_first_requirement(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        payload = {'state':{},'history':[],'summary':'需求','result':None}
        follow = Mock(return_value=payload)
        fake = SimpleNamespace(continue_conversation=follow, SimpleModeError=ValueError)
        with patch.dict(sys.modules, {'simple_flow':fake}):
            self.callback('simple_start').fn('产品','学生','小红书',{'synthetic':True},'开学季，不要夸张')
        follow.assert_called_once_with({},'产品','学生','小红书','开学季，不要夸张',api_config={'synthetic':True})

    def test_api_changes_in_either_mode_invalidate_both_deliveries(self):
        dependencies = self.app.get_config_file()['dependencies']
        for name in ('simple_save_api','simple_reset_api','save_api','reset_api'):
            fn = self.callback(name)
            if name.startswith('simple_'):
                self.assertTrue(any(dep.get('trigger_after') == fn._id for dep in dependencies), name)
            else:
                values = () if name == 'reset_api' else ('https://api.example.com/v1','synthetic-mode-key','model')
                result = fn.fn(*values)
                self.assertFalse(result[self.component('zh-simple-confirm')]['interactive'])

    def test_mode_descriptions_support_hover_focus_and_touch(self):
        from visual_theme import DESKTOP_CSS
        for rule in ('.zh-mode-card:hover', '.zh-mode-card:focus-within', '@media(hover:none)'):
            self.assertIn(rule, DESKTOP_CSS)

    def test_refresh_loads_the_same_catalog_into_both_modes_and_keeps_typed_values(self):
        fn = self.callback('refresh_connection')
        with patch('agent.get_products', return_value=['型号一','型号二']), patch('agent.get_connection_status', return_value='本地只读'):
            result = fn.fn('专业已填值','极简已填值')
        self.assertEqual(result[1]['choices'], ['型号一','型号二'])
        self.assertEqual(result[2]['choices'], ['型号一','型号二'])
        self.assertEqual(result[1]['value'],'专业已填值')
        self.assertEqual(result[2]['value'],'极简已填值')

    def test_missing_model_configuration_reveals_settings_and_preserves_draft(self):
        import os
        with patch.dict(os.environ, {}, clear=True):
            result = self.callback('simple_start').fn('HUAWEI MateBook Pro S','大学生','小红书',None,'请自然表达')
        self.assertTrue(result.get(self.component('zh-simple-api-settings'), {}).get('open',False))
        self.assertNotIn(self.component('zh-simple-message'), result)

    def test_first_visit_shows_mode_picker_instead_of_either_workspace(self):
        home = self.component('zh-mode-home')
        self.assertIsNotNone(home, 'first visit must ask for a mode')
        self.assertTrue(home.visible)
        self.assertFalse(self.component('zh-workspace').visible)
        self.assertFalse(self.component('zh-simple-workspace').visible)


if __name__ == '__main__':
    unittest.main()
