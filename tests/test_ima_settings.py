"""Session ima settings and event output wiring; no network, model or server."""
import unittest
from unittest.mock import patch

import agent
from ima_client import IMAError
from studio_ui import build_studio
from app import EXAMPLES, FALLBACK_PRODUCTS
from visual_theme import DESKTOP_HTML

CONFIG = {'client_id': 'synthetic-client-1234', 'api_key': 'synthetic-ima-key-value', 'kb_name': 'Synthetic KB'}


class ResolveImaConfigTests(unittest.TestCase):
    def test_empty_means_default_source(self):
        self.assertIsNone(agent.resolve_ima_config({'client_id': ' ', 'api_key': '', 'kb_name': ''}))
        self.assertIsNone(agent.resolve_ima_config(None))

    def test_partial_or_malformed_config_is_rejected(self):
        for raw in ({**CONFIG, 'kb_name': ''}, {**CONFIG, 'api_key': ''}, {**CONFIG, 'api_key': 'has space'}):
            with self.subTest(raw=raw), self.assertRaises(IMAError):
                agent.resolve_ima_config(raw)

    def test_valid_config_is_trimmed(self):
        self.assertEqual(agent.resolve_ima_config({k: f' {v} ' for k, v in CONFIG.items()}), CONFIG)


class ImaSessionRoutingTests(unittest.TestCase):
    def test_session_config_routes_to_live_client_without_fallback(self):
        with agent.ima_session(CONFIG):
            client = agent._ima()
        self.assertFalse(client._offline_archive)
        self.assertEqual(client.kb_name, 'Synthetic KB')
        self.assertEqual(client._client_id, 'synthetic-client-1234')

    def test_context_is_reset_after_the_block(self):
        with agent.ima_session(CONFIG):
            pass
        self.assertIsNone(agent._SESSION_IMA.get())

    def test_same_config_reuses_one_cached_client(self):
        with agent.ima_session(CONFIG):
            first = agent._ima()
        with agent.ima_session(dict(CONFIG)):
            second = agent._ima()
        self.assertIs(first, second)


class EventWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = build_studio(EXAMPLES, FALLBACK_PRODUCTS, DESKTOP_HTML)
        cls.components = list(cls.app.blocks.values())

    def component(self, elem_id):
        return next(c for c in self.components if getattr(c, 'elem_id', None) == elem_id)

    def callbacks(self, name):
        return [f for f in self.app.fns.values() if f.fn and f.fn.__name__ == name]

    def test_field_edit_invalidators_only_return_declared_outputs(self):
        # An undeclared returned component makes Gradio reject the whole update,
        # which left the old final and its downloads in place after an edit.
        for name in ('invalidate_request', 'invalidate_style', 'invalidate_plan'):
            for fn in self.callbacks(name):
                with self.subTest(name=name, outputs=len(fn.outputs)):
                    result = fn.fn() if name == 'invalidate_request' else fn.fn({})
                    undeclared = [c for c in result if c not in fn.outputs]
                    self.assertEqual(undeclared, [])

    def test_ima_save_and_reset_only_return_declared_outputs(self):
        save, reset = self.callbacks('save_ima')[0], self.callbacks('reset_ima')[0]
        with patch('agent.get_products', return_value=['型号一']), \
                patch('agent.get_connection_status', return_value='synthetic status'):
            results = [save.fn(*CONFIG.values(), None, None), save.fn('', '', '', None, None),
                       save.fn('only-id', '', '', None, None), reset.fn(None, None)]
        for fn, result in zip((save, save, save, reset), results):
            self.assertEqual([c for c in result if c not in fn.outputs], [])

    def test_ima_failure_keeps_default_source_and_never_echoes_key(self):
        save = self.callbacks('save_ima')[0]
        state = save.outputs[0]
        with patch('agent.get_products', return_value=[]), \
                patch('agent.get_connection_status', return_value='synthetic status'):
            result = save.fn(*CONFIG.values(), None, None)
        self.assertEqual(result[state], {})
        self.assertIn('未成功', result[self.component('zh-ima-notice')])
        self.assertEqual(result[self.component('zh-ima-api-key')], '')
        self.assertNotIn(CONFIG['api_key'], repr(result))

    def test_ima_success_applies_config_and_relocks_results(self):
        save = self.callbacks('save_ima')[0]
        with patch('agent.get_products', return_value=['型号一', '型号二']), \
                patch('agent.get_connection_status', return_value='synthetic status'):
            result = save.fn(*CONFIG.values(), None, None)
        self.assertEqual(result[save.outputs[0]], CONFIG)
        self.assertIn('2 个型号', result[self.component('zh-ima-notice')])
        self.assertIn('已失效', result[self.component('zh-preview')])
        self.assertEqual(result[self.component('zh-ima-api-key')], '')

    def test_ima_settings_are_reachable_from_both_modes(self):
        # The settings live in the shared source panel, not inside one professional page.
        panel = self.component('zh-connection-details')
        settings = self.component('zh-ima-settings')
        self.assertIs(settings.parent, panel)


if __name__ == '__main__':
    unittest.main()
