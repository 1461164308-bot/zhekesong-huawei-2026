"""Real Gradio component/event tests; never call a model or start a server."""
import unittest
from unittest.mock import patch

from studio_ui import build_studio
from app import EXAMPLES, FALLBACK_PRODUCTS
from visual_theme import DESKTOP_HTML


class StepPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = build_studio(EXAMPLES, FALLBACK_PRODUCTS, DESKTOP_HTML)
        cls.components = list(cls.app.blocks.values())

    def component(self, elem_id):
        return next(c for c in self.components if getattr(c, 'elem_id', None) == elem_id)

    def callback(self, name):
        return next(f for f in self.app.fns.values() if f.fn and f.fn.__name__ == name)

    def test_sidebar_visits_every_page_without_touching_inputs_or_approvals(self):
        pages = [self.component('zh-page-' + name) for name in ('api', 'brief', 'style', 'plan', 'final', 'download')]
        with patch('agent.run_task', side_effect=AssertionError('navigation must not call models')):
            for index in range(6):
                fn = self.callback('navigate_' + str(index))
                result = fn.fn()
                self.assertEqual([p for p in pages if result[p]['visible']], [pages[index]])
                self.assertEqual(result[self.component('zh-nav-' + str(index))]['variant'], 'primary')
                self.assertTrue(all(c in pages or (getattr(c, 'elem_id', '') or '').startswith('zh-nav-')
                                    or getattr(c, 'elem_id', None) == 'zh-current-page' for c in result))
                self.assertEqual(fn.inputs, [])

    def test_brief_confirmation_advances_only_on_success(self):
        fn = self.callback('confirm_brief')
        values = [EXAMPLES[0][key] for key in ('product', 'audience', 'scenario', 'platform', 'goal', 'requirements')]
        result = fn.fn(*values)
        self.assertTrue(result.get(self.component('zh-page-style'), {}).get('visible', False))
        failed = fn.fn('', *values[1:])
        self.assertNotIn(self.component('zh-page-style'), failed)
        self.assertIn('请检查', failed[self.component('zh-status')])

    def test_api_application_advances_but_invalid_and_reset_stay(self):
        fn = self.callback('save_api')
        result = fn.fn('https://api.example.com/v1', 'synthetic-key-value', 'custom-model')
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get(self.component('zh-page-brief'), {}).get('visible', False))
        self.assertTrue(set(result).issubset(set(fn.outputs)))
        for values in [('', '', ''), ('http://api.example.com', 'synthetic-key-value', '')]:
            failed = fn.fn(*values)
            self.assertNotIn(self.component('zh-page-brief'), failed)
        reset = self.callback('reset_api').fn()
        self.assertNotIn(self.component('zh-page-brief'), reset)

    def flow_values(self):
        import creation_flow as flow
        from style_cards import get_preset, style_values
        request = {key: EXAMPLES[0][key] for key in flow.REQUEST_FIELDS}
        card = get_preset('专业可信')
        values = [request[k] for k in flow.REQUEST_FIELDS] + ['', ''] + list(style_values(card)) + ['切入点', '段落', '图片位置', '到店', '条件']
        return flow.confirm_brief(request), values

    def test_style_confirmation_advances_only_when_current_brief_is_confirmed(self):
        import creation_flow as flow
        current, values = self.flow_values()
        fn = self.callback('approve_style')
        result = fn.fn(current, *values, flow.style_source_key())
        self.assertTrue(result.get(self.component('zh-page-plan'), {}).get('visible', False))
        failed = fn.fn({}, *values, flow.style_source_key())
        self.assertNotIn(self.component('zh-page-plan'), failed)

    def prepared_values(self):
        import time
        import creation_flow as flow
        current, values = self.flow_values()
        style_result = self.callback('approve_style').fn(current, *values, flow.style_source_key())
        current = style_result[self.callback('approve_style').inputs[0]]
        current['prepared'] = {'input_key': current['request_key'], 'style_key': current['style_key'], 'created_at': time.time()}
        return current, values

    def test_plan_confirmation_advances_only_with_valid_evidence(self):
        current, values = self.prepared_values()
        fn = self.callback('approve_plan')
        result = fn.fn(current, *values)
        self.assertTrue(result.get(self.component('zh-page-final'), {}).get('visible', False))
        current['prepared']['created_at'] = 0
        failed = fn.fn(current, *values)
        self.assertNotIn(self.component('zh-page-final'), failed)
        self.assertIn('一小时', failed[self.component('zh-status')])

    def final_values(self, export_path=None):
        current, values = self.prepared_values()
        fn = self.callback('approve_plan')
        current = fn.fn(current, *values)[fn.inputs[0]]
        current['final_result'] = {'status': 'ready', 'copy_text': '合成测试文案', 'checks': {'platform_ready': True},
                                   'export_html': export_path}
        return current, values

    def test_final_confirmation_advances_only_with_existing_files(self):
        import tempfile
        from pathlib import Path
        fn = self.callback('approve_final')
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'preview.html'
            file.write_text('<p>synthetic test</p>', encoding='utf-8')
            current, values = self.final_values(str(file))
            result = fn.fn(current, *values)
            self.assertTrue(result.get(self.component('zh-page-download'), {}).get('visible', False))
            self.assertTrue(set(result).issubset(set(fn.outputs)))
            file.unlink()
            failed = fn.fn(current, *values)
            self.assertNotIn(self.component('zh-page-download'), failed)
            for output in fn.outputs:
                if output.__class__.__name__ == 'File':
                    self.assertIsNone(failed.get(output))
            self.assertIn('文件缺失', failed[self.component('zh-status')])

    def test_navigation_is_not_queued_behind_generation(self):
        for index in range(6):
            fn = self.callback('navigate_' + str(index))
            self.assertFalse(fn.queue)
            self.assertNotEqual(fn.concurrency_id, 'zhiheng_creation')

    def test_previous_next_controls_browse_without_confirming(self):
        for index in range(6):
            for direction, target in [('prev', index - 1), ('next', index + 1)]:
                if not 0 <= target < 6:
                    continue
                button = next((c for c in self.components if getattr(c, 'elem_id', None) == f'zh-{direction}-{index}'), None)
                self.assertIsNotNone(button, f'missing {direction} button for page {index}')
                fn = next(f for f in self.app.fns.values() if (button._id, 'click') in f.targets)
                self.assertEqual(fn.inputs, [])
                self.assertFalse(fn.queue)
                result = fn.fn()
                pages = [c for c in self.components if (getattr(c, 'elem_id', None) or '').startswith('zh-page-')]
                self.assertEqual([p for p in pages if result[p]['visible']], [pages[target]])

    def test_topbar_is_compact_without_decorative_hero(self):
        from visual_theme import DESKTOP_CSS
        self.assertNotIn('zh-liquid-hero', DESKTOP_HTML)
        self.assertNotIn('<h1>', DESKTOP_HTML)
        self.assertIn('#zh-sidebar', DESKTOP_CSS)
        self.assertIn('position:sticky', DESKTOP_CSS)

    def test_upstream_edits_remove_stale_previews_and_lock_downloads(self):
        current, values = self.final_values()
        for name in ['invalidate_request', 'invalidate_style', 'invalidate_plan']:
            fn = self.callback(name)
            result = fn.fn() if name == 'invalidate_request' else fn.fn(current)
            self.assertIn('已失效', result.get(self.component('zh-preview'), ''))
            self.assertNotIn('final_result', result[fn.outputs[0]])
            self.assertNotIn('final_key', result[fn.outputs[0]])
            self.assertNotIn(self.component('zh-page-download'), result)
            for output in fn.outputs:
                if output.__class__.__name__ == 'File':
                    self.assertIn(output, result)
                    self.assertIsNone(result[output])
            for label in ['平台文案', '内容和平台格式核验']:
                component = next(c for c in self.components if getattr(c, 'label', None) == label)
                self.assertFalse(result.get(component, 'not-cleared'))

    def test_api_changes_and_reset_relock_existing_deliveries(self):
        callbacks = [self.callback('reset_api'), self.callback('save_api')]
        for fn in callbacks:
            result = fn.fn() if fn.fn.__name__ == 'reset_api' else fn.fn('https://api.example.com/v1', 'synthetic-key-value', 'model')
            state_component = self.callback('approve_final').inputs[0]
            self.assertEqual(result.get(state_component, 'not-invalidated'), {})
            self.assertIn('已失效', result.get(self.component('zh-preview'), ''))
            for component in self.callback('approve_final').outputs:
                if component.__class__.__name__ == 'File':
                    self.assertIn(component, result)
                    self.assertIsNone(result[component])
            self.assertTrue(set(result).issubset(set(fn.outputs)))
        reset = callbacks[0].fn()
        for label in ['服务地址（Base URL）', 'API 密钥', '模型名称（选填）']:
            component = next(c for c in self.components if getattr(c, 'label', None) == label)
            self.assertEqual(reset.get(component), '')

    def test_connection_details_start_collapsed_and_no_duplicate_title(self):
        accordion = next((c for c in self.components if getattr(c, 'elem_id', None) == 'zh-connection-details'), None)
        self.assertIsNotNone(accordion)
        self.assertFalse(accordion.open)
        self.assertFalse(any(getattr(c, 'elem_id', None) == 'zh-app-title' and c.visible for c in self.components))
        self.assertIsNotNone(self.component('zh-nav-buttons'))

    def test_reconfirmation_clears_old_final_content(self):
        import creation_flow as flow
        current, values = self.final_values()
        calls = [('confirm_brief', values[:6]),
                 ('approve_style', [current, *values, flow.style_source_key()]),
                 ('approve_plan', [current, *values])]
        for name, args in calls:
            result = self.callback(name).fn(*args)
            self.assertIn('已失效', result.get(self.component('zh-preview'), ''), name)

    def test_sticky_sidebar_is_not_trapped_by_gradio_overflow(self):
        import re
        from visual_theme import DESKTOP_CSS
        rules = re.findall(r'([^{}]+)\{([^{}]+)\}', DESKTOP_CSS)
        self.assertTrue(any(selector.strip() == '.gradio-container' and 'overflow:visible !important' in declarations
                            for selector, declarations in rules),
                        'Gradio overflow:hidden traps sticky navigation outside the viewport')

    def test_regenerating_idea_does_not_leave_a_previous_final_preview(self):
        import creation_flow as flow
        current, values = self.final_values()
        result = {'status': 'plan_ready', 'prepared': current['prepared'],
                  'plan': dict(zip((key for key, _ in flow.PLAN_FIELDS), values[-5:])), 'facts': [], 'images': []}
        fn = self.callback('create_idea')
        with patch('agent.run_task', return_value=result):
            updates = fn.fn(current, *values, {'synthetic': True})
        self.assertIn('已失效', updates.get(self.component('zh-preview'), ''))
        self.assertNotIn('final_result', updates[fn.inputs[0]])

    def test_page_transitions_scroll_back_to_the_step_header(self):
        dependencies = self.app.get_config_file()['dependencies']
        names = {'confirm_brief', 'approve_style', 'approve_plan', 'approve_final', 'save_api'}
        targets = [index for index, fn in self.app.fns.items() if fn.fn and
                   (fn.fn.__name__ in names or fn.fn.__name__.startswith('navigate_'))]
        for index in targets:
            self.assertTrue(any(dep.get('trigger_after') == index and 'scrollTo' in (dep.get('js') or '')
                                and not dep.get('queue') for dep in dependencies),
                            f'callback {index} needs a frontend-only scroll after rendering')

    def test_initially_only_api_page_is_visible(self):
        pages = [c for c in self.components if (getattr(c, 'elem_id', None) or '').startswith('zh-page-')]
        self.assertEqual(len(pages), 6)
        self.assertEqual([c.elem_id for c in pages if c.visible], ['zh-page-api'])
        self.assertTrue(self.component('zh-sidebar').visible)
        self.assertTrue(self.component('zh-status').visible)


if __name__ == '__main__':
    unittest.main()
