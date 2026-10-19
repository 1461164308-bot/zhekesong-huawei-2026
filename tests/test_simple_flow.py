"""Simple-mode tests: no external network, synthetic catalog and model replies."""
import copy
import importlib
import json
import unittest
from unittest.mock import patch, Mock

PRODUCT = 'HUAWEI MateBook Pro S'
API = {'base_url': 'https://synthetic.example/v1', 'api_key': 'synthetic-session-key', 'model': 'mock'}


class SimpleFlowTests(unittest.TestCase):
    def setUp(self):
        self.flow = importlib.import_module('simple_flow')
        self.model = Mock()
        self.model.json.return_value = {'reply': '先了解你的需求。', 'question': '用于什么场景？希望实现什么目标？'}
        for target, kwargs in [
            ('requests.sessions.Session.request', {'side_effect': AssertionError('No network')}),
            ('simple_flow.agent.get_products', {'return_value': [PRODUCT]}),
            ('simple_flow.server_api_configured', {'return_value': True}),
            ('simple_flow.LLMClient', {'return_value': self.model}),
        ]:
            p = patch(target, **kwargs)
            p.start()
            self.addCleanup(p.stop)

    def test_missing_api_and_model_errors_are_safe(self):
        with patch('simple_flow.server_api_configured', return_value=False):
            with self.assertRaisesRegex(self.flow.SimpleModeError, 'API'):
                self.flow.start_conversation(PRODUCT, '上班族', '门店朋友圈')
        self.model.json.side_effect = RuntimeError('raw private response synthetic-session-key')
        with self.assertRaises(self.flow.SimpleModeError) as caught:
            self.flow.start_conversation(PRODUCT, '上班族', '门店朋友圈', API)
        self.assertNotIn('raw private', str(caught.exception))
        self.assertNotIn(API['api_key'], str(caught.exception))

    def test_continue_uses_user_answer_for_next_question_without_mutating_state(self):
        first = self.flow.start_conversation('轻薄本', '上班族', '门店朋友圈', API)
        snapshot = copy.deepcopy(first)
        self.model.json.return_value = {'reply': '已记下职场办公。', 'question': '希望什么语气？有哪些禁忌？'}
        out = self.flow.continue_conversation(first['state'], '轻薄本', '上班族', '门店朋友圈', '职场办公，目标选购决策', API)
        self.assertEqual(first, snapshot)
        payload = self.model.json.call_args.args[1]
        self.assertEqual(payload['history'][-1], {'role': 'user', 'content': '职场办公，目标选购决策'})
        self.assertIn('什么语气', out['history'][-1]['content'])
        self.assertIn('选购决策', out['summary'])
        self.assertIsNone(out['result'])

    def test_immediate_generation_bypasses_guidance_and_passes_pipeline_result(self):
        for status in ('ready', 'blocked', 'needs_clarification'):
            result = {'status': status, 'copy_text': '', 'checks': {'publication': '审核结果'}}
            with patch('simple_flow.agent.run_task', return_value=result) as run:
                out = self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈', api_config=API)
            self.assertIs(out['result'], result)
            task = run.call_args.kwargs
            self.assertEqual(task['phase'], 'final')
            self.assertEqual(task['product'], PRODUCT)
            self.assertEqual(task['scenario'], '职场办公')
            self.assertEqual(task['goal'], '种草了解')
            self.assertEqual(task['api_config'], API)
            self.assertEqual(task['style_card']['name'], '亲切自然')
            self.assertIn('默认场景：职场办公', out['summary'])
            self.assertIn('未提供额外偏好', out['summary'])
            self.assertIn('不虚构', task['requirements'])
            self.assertIn('门店', task['requirements'])
        self.model.json.assert_not_called()

    def test_pending_and_only_user_messages_become_generation_requirements(self):
        first = self.flow.start_conversation(PRODUCT, '上班族', '门店朋友圈', API)
        current = self.flow.continue_conversation(first['state'], PRODUCT, '上班族', '门店朋友圈', '语气简洁，不写优惠', API)['state']
        with patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            out = self.flow.generate_now(current, PRODUCT, '上班族', '门店朋友圈', '场景内容创作，目标选购决策，重点软件适配', API)
        task = run.call_args.kwargs
        self.assertIn('语气简洁，不写优惠', task['requirements'])
        self.assertIn('重点软件适配', task['requirements'])
        self.assertNotIn('用于什么场景', task['requirements'])
        self.assertNotIn('先了解你的需求', task['requirements'])
        self.assertEqual(task['scenario'], '内容创作')
        self.assertEqual(task['goal'], '选购决策')
        self.assertEqual(out['history'][-1]['role'], 'user')
        self.assertIn('内容创作', out['summary'])
        self.assertNotIn('未提供额外偏好', out['summary'])
        self.assertEqual(self.model.json.call_count, 2)

    def test_ambiguous_product_never_uses_assistant_suggestion_as_confirmation(self):
        self.model.json.return_value = {'reply': '建议选择' + PRODUCT, 'question': '是否使用这个型号？'}
        current = self.flow.start_conversation('轻薄本', '上班族', '门店朋友圈', API)['state']
        with patch('simple_flow.agent.run_task') as run:
            for pending in ('', '好的', 'MateBook'):
                with self.assertRaisesRegex(self.flow.SimpleModeError, '型号'):
                    self.flow.generate_now(current, '轻薄本', '上班族', '门店朋友圈', pending, API)
            run.assert_not_called()
        with patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            out = self.flow.generate_now(current, '轻薄本', '上班族', '门店朋友圈', '明确选择 ' + PRODUCT, API)
        self.assertEqual(run.call_args.kwargs['product'], PRODUCT)
        self.assertIn(PRODUCT, out['summary'])

    def test_neutral_mention_cannot_resurrect_a_withdrawn_model(self):
        other = 'HUAWEI MateBook Pro（鸿蒙版）'
        with patch('simple_flow.agent.get_products', return_value=[PRODUCT, other]), patch(
                'simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            current = self.flow.start_conversation('轻薄本', '上班族', '门店朋友圈', API)['state']
            current = self.flow.continue_conversation(current, '轻薄本', '上班族', '门店朋友圈',
                                                      '明确选择 ' + PRODUCT, API)['state']
            current = self.flow.continue_conversation(current, '轻薄本', '上班族', '门店朋友圈',
                                                      '不要' + PRODUCT, API)['state']
            # A generic product plus only a neutral mention can never resolve a model.
            with self.assertRaisesRegex(self.flow.SimpleModeError, '型号'):
                self.flow.generate_now(current, '轻薄本', '上班族', '门店朋友圈',
                                       '不要夸大' + PRODUCT + '的性能', API)
            # An exact product is authoritative; a neutral mention is not a withdrawal.
            exact = self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈',
                                           '不要夸大' + PRODUCT + '的性能', API)
            self.assertEqual(exact['result']['status'], 'blocked')
            self.assertEqual(run.call_args.kwargs['product'], PRODUCT)
            with self.assertRaisesRegex(self.flow.SimpleModeError, '型号'):
                self.flow.generate_now({}, '轻薄本', '上班族', '门店朋友圈',
                                       '不要夸大' + PRODUCT + '的性能', API)
        # A neutral mention must not erase an explicit earlier choice either.
        with patch('simple_flow.agent.get_products', return_value=[PRODUCT, other]), patch(
                'simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            current = self.flow.start_conversation('轻薄本', '上班族', '门店朋友圈', API)['state']
            current = self.flow.continue_conversation(current, '轻薄本', '上班族', '门店朋友圈',
                                                      '明确选择 ' + PRODUCT, API)['state']
            self.flow.generate_now(current, '轻薄本', '上班族', '门店朋友圈',
                                   '不要夸大' + PRODUCT + '的性能', API)
        self.assertEqual(run.call_args.kwargs['product'], PRODUCT)

    def test_quoted_or_verb_prefixed_model_withdrawals_cannot_generate_old_product(self):
        with patch('simple_flow.agent.run_task') as run:
            for pending in ('不要“' + PRODUCT + '”', '不要使用' + PRODUCT, '不再用' + PRODUCT,
                            '「' + PRODUCT + '」不要了'):
                with self.subTest(pending=pending), self.assertRaisesRegex(self.flow.SimpleModeError, '型号'):
                    self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈', pending, API)
            run.assert_not_called()

    def test_generic_product_cannot_reuse_withdrawn_historical_choice(self):
        current = self.flow.start_conversation('轻薄本', '上班族', '门店朋友圈', API)['state']
        current = self.flow.continue_conversation(current, '轻薄本', '上班族', '门店朋友圈', '明确选择 ' + PRODUCT, API)['state']
        with patch('simple_flow.agent.run_task') as run:
            with self.assertRaisesRegex(self.flow.SimpleModeError, '型号'):
                self.flow.generate_now(current, '轻薄本', '上班族', '门店朋友圈', '刚才型号选错了，不要' + PRODUCT, API)
            run.assert_not_called()

    def test_exact_basic_rejects_dialogue_withdrawal_or_different_model(self):
        other = 'HUAWEI MateBook 14（鸿蒙版）'
        with patch('simple_flow.agent.get_products', return_value=[PRODUCT, other]), patch('simple_flow.agent.run_task') as run:
            for pending in ('不要' + PRODUCT + '，改选' + other, '明确选择' + other, '不要' + PRODUCT,
                            PRODUCT + '和' + other + '比较一下'):
                with self.subTest(pending=pending):
                    with self.assertRaisesRegex(self.flow.SimpleModeError, '三项基础.*冲突.*产品字段'):
                        self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈', pending, API)
            run.assert_not_called()
        self.model.json.assert_not_called()

    def test_generic_product_uses_replacement_after_suffix_withdrawal(self):
        other = 'HUAWEI MateBook 14（鸿蒙版）'
        current = self.flow.start_conversation('轻薄本', '上班族', '门店朋友圈', API)['state']
        current = self.flow.continue_conversation(current, '轻薄本', '上班族', '门店朋友圈', '明确选择 ' + PRODUCT, API)['state']
        with patch('simple_flow.agent.get_products', return_value=[PRODUCT, other]), patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            for suffix in ('不要了', '选错了'):
                with self.subTest(suffix=suffix):
                    self.flow.generate_now(current, '轻薄本', '上班族', '门店朋友圈', PRODUCT + suffix + '，明确选择' + other, API)
                    self.assertEqual(run.call_args.kwargs['product'], other)

    def test_product_performance_prohibition_is_not_model_withdrawal(self):
        with patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈', '不要夸大' + PRODUCT + '的性能', API)
            self.assertEqual(run.call_args.kwargs['product'], PRODUCT)
        # A generic product still needs an explicit model choice.
        with patch('simple_flow.agent.run_task') as run, self.assertRaisesRegex(self.flow.SimpleModeError, '型号'):
            self.flow.generate_now({}, '轻薄本', '上班族', '门店朋友圈', '不要夸大' + PRODUCT + '的性能', API)
        run.assert_not_called()
        self.model.json.assert_not_called()

    def test_last_reconfirmation_restores_previously_withdrawn_model(self):
        for basic in ('轻薄本', PRODUCT):
            with self.subTest(basic=basic):
                current = self.flow.start_conversation(basic, '上班族', '门店朋友圈', API)['state']
                for message in ('明确选择 ' + PRODUCT, '再次确认 ' + PRODUCT, '不要' + PRODUCT):
                    current = self.flow.continue_conversation(current, basic, '上班族', '门店朋友圈', message, API)['state']
                with patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
                    self.flow.generate_now(current, basic, '上班族', '门店朋友圈', '最终明确重新选择 ' + PRODUCT, API)
                    self.assertEqual(run.call_args.kwargs['product'], PRODUCT)

    def test_each_direct_model_withdrawal_blocks_historical_selection(self):
        for basic in ('轻薄本', PRODUCT):
            current = self.flow.start_conversation(basic, '上班族', '门店朋友圈', API)['state']
            current = self.flow.continue_conversation(current, basic, '上班族', '门店朋友圈', '明确选择 ' + PRODUCT, API)['state']
            messages = [prefix + PRODUCT for prefix in ('不要', '不选', '排除', '不是', '不考虑', '别用', '不用')]
            messages += [PRODUCT + suffix for suffix in ('不要了', '选错了')]
            with patch('simple_flow.agent.run_task') as run:
                for pending in messages:
                    with self.subTest(basic=basic, pending=pending):
                        with self.assertRaisesRegex(self.flow.SimpleModeError, '型号'):
                            self.flow.generate_now(current, basic, '上班族', '门店朋友圈', pending, API)
                run.assert_not_called()

    def test_assistant_different_model_does_not_create_candidate_or_basic_conflict(self):
        other = 'HUAWEI MateBook 14（鸿蒙版）'
        self.model.json.return_value = {'reply': '建议选择' + other, 'question': '是否需要？'}
        with patch('simple_flow.agent.get_products', return_value=[PRODUCT, other]):
            for basic in ('轻薄本', PRODUCT):
                current = self.flow.start_conversation(basic, '上班族', '门店朋友圈', API)['state']
                with patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
                    self.flow.generate_now(current, basic, '上班族', '门店朋友圈', '明确选择' + PRODUCT, API)
                    self.assertEqual(run.call_args.kwargs['product'], PRODUCT)
                    self.assertNotIn(other, run.call_args.kwargs['requirements'])

    def test_changed_basic_rejects_old_context_in_both_entrypoints(self):
        current = self.flow.start_conversation(PRODUCT, '上班族', '门店朋友圈', API)['state']
        for basic in [('轻薄本', '上班族', '门店朋友圈'), (PRODUCT, '大学生', '门店朋友圈'), (PRODUCT, '上班族', '小红书')]:
            for entry in (self.flow.continue_conversation, self.flow.generate_now):
                with self.assertRaisesRegex(self.flow.SimpleModeError, '重新开始'):
                    entry(current, *basic, '旧信息不能用', API)
        self.assertIn('basic_key', current)

    def test_inputs_are_validated_before_model_or_generation(self):
        for basic in [('', '上班族', '门店朋友圈'), (PRODUCT, ' ', '门店朋友圈'), (PRODUCT, '上班族', ''), (PRODUCT, '上班族', '微博')]:
            for entry in (self.flow.start_conversation, lambda *a: self.flow.generate_now({}, *a)):
                with self.assertRaises(self.flow.SimpleModeError):
                    entry(*basic)
        self.model.json.assert_not_called()

    def test_secrets_are_removed_from_state_guidance_and_generation(self):
        secret = 'plain-session-secret-without-sk-prefix'
        config = {**API, 'api_key': secret}
        pasted = '重点软件适配 api_key=private-marker ' + secret + ' https://example.test/a?sign=private-sign'
        self.model.json.return_value = {'reply': '已记下 ' + secret, 'question': ''}
        first = self.flow.start_conversation(PRODUCT, '人群 ' + secret, '门店朋友圈', config)
        out = self.flow.continue_conversation(first['state'], PRODUCT, '人群 ' + secret, '门店朋友圈', pasted, config)
        surfaces = json.dumps([first, out, self.model.json.call_args.args], ensure_ascii=False)
        for marker in (secret, 'private-marker', 'private-sign'):
            self.assertNotIn(marker, surfaces)
        with patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            generated = self.flow.generate_now(out['state'], PRODUCT, '人群 ' + secret, '门店朋友圈', pasted, config)
        task = run.call_args.kwargs.copy()
        task.pop('api_config')
        for marker in (secret, 'private-marker', 'private-sign'):
            self.assertNotIn(marker, json.dumps([generated, task], ensure_ascii=False))
        self.assertIn('已隐藏', task['requirements'])

    def test_input_and_history_limits_reject_without_truncating_preferences(self):
        with self.assertRaisesRegex(self.flow.SimpleModeError, '过长'):
            self.flow.start_conversation('型' * 181, '上班族', '门店朋友圈', API)
        current = self.flow.start_conversation(PRODUCT, '上班族', '门店朋友圈', API)['state']
        for entry in (self.flow.continue_conversation, self.flow.generate_now):
            with self.assertRaisesRegex(self.flow.SimpleModeError, '过长'):
                entry(current, PRODUCT, '上班族', '门店朋友圈', '长' * 401, API)
        for _ in range(6):
            current = self.flow.continue_conversation(current, PRODUCT, '上班族', '门店朋友圈', '补充偏好', API)['state']
        calls = self.model.json.call_count
        with self.assertRaisesRegex(self.flow.SimpleModeError, '随时生成'):
            self.flow.continue_conversation(current, PRODUCT, '上班族', '门店朋友圈', '再追问', API)
        self.assertEqual(self.model.json.call_count, calls)
        with patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}):
            self.flow.generate_now(current, PRODUCT, '上班族', '门店朋友圈', api_config=API)
        oversized = copy.deepcopy(current)
        oversized['history'] = [{'role': 'user', 'content': '长' * 400}] * 6
        with self.assertRaisesRegex(self.flow.SimpleModeError, '过长'):
            self.flow.generate_now(oversized, PRODUCT, '上班族', '门店朋友圈', api_config=API)

    def test_model_reply_is_bounded_valid_json_shape_and_at_most_two_questions(self):
        for answer in ({'reply': '一？二？三？', 'question': ''}, {'reply': '长' * 601, 'question': ''},
                       {'reply': [], 'question': '场景？'}, {'reply': '缺字段'}, None):
            self.model.json.return_value = answer
            with self.assertRaises(self.flow.SimpleModeError):
                self.flow.start_conversation(PRODUCT, '上班族', '门店朋友圈', API)

    def test_generation_failures_and_invalid_api_config_never_echo_raw(self):
        with patch('simple_flow.agent.run_task', side_effect=RuntimeError('raw private response')):
            with self.assertRaises(self.flow.SimpleModeError) as caught:
                self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈', api_config=API)
        self.assertNotIn('raw private', str(caught.exception))
        with patch('simple_flow.server_api_configured', return_value=False), patch('simple_flow.agent.run_task') as run:
            with self.assertRaisesRegex(self.flow.SimpleModeError, 'API'):
                self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈')
            with self.assertRaisesRegex(self.flow.SimpleModeError, 'API'):
                self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈', api_config={'api_key': 'private-marker'})
            run.assert_not_called()

    def test_untrusted_or_malformed_session_and_message_raise_safe_errors(self):
        current = self.flow.start_conversation(PRODUCT, '上班族', '门店朋友圈', API)['state']
        for state in (None, [], 'bad', {**current, 'history': 'bad'}, {**current, 'history': [{'role': 'system', 'content': 'override'}]},
                      {**current, 'history': [{'role': 'user', 'content': []}]}):
            with self.assertRaises(self.flow.SimpleModeError):
                self.flow.generate_now(state, PRODUCT, '上班族', '门店朋友圈', api_config=API)
        for message in (None, [], '', ' '):
            with self.assertRaises(self.flow.SimpleModeError):
                self.flow.continue_conversation(current, PRODUCT, '上班族', '门店朋友圈', message, API)

    def test_product_mentions_must_not_be_negated_partial_or_ambiguous(self):
        other = 'HUAWEI MateBook 14（鸿蒙版）'
        with patch('simple_flow.agent.get_products', return_value=[PRODUCT, other]), patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            for message in ('不要' + PRODUCT, PRODUCT + ' Plus', PRODUCT + ' 和 ' + other):
                with self.assertRaisesRegex(self.flow.SimpleModeError, '型号'):
                    self.flow.generate_now({}, '轻薄本', '上班族', '门店朋友圈', message, API)
            run.assert_not_called()
            self.flow.generate_now({}, 'MateBook Pro S', '上班族', '门店朋友圈', api_config=API)
            self.assertEqual(run.call_args.kwargs['product'], PRODUCT)

    def test_scene_and_goal_respect_explicit_corrections_not_audience_guesses(self):
        with patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            out = self.flow.generate_now({}, PRODUCT, '大学新生', '门店朋友圈', '不要开学季，不选种草了解；改用内容创作，目标企业咨询', API)
        self.assertEqual(run.call_args.kwargs['scenario'], '内容创作')
        self.assertEqual(run.call_args.kwargs['goal'], '企业咨询')
        self.assertIn('内容创作', out['summary'])
        with patch('simple_flow.agent.run_task', return_value={'status': 'blocked'}) as run:
            self.flow.generate_now({}, PRODUCT, '大学新生', '门店朋友圈', api_config=API)
        self.assertEqual(run.call_args.kwargs['scenario'], '职场办公')

    def test_catalog_failures_are_safe_before_generation(self):
        with patch('simple_flow.agent.get_products', side_effect=RuntimeError('private-catalog-error')):
            with self.assertRaises(self.flow.SimpleModeError) as caught:
                self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈', api_config=API)
        self.assertNotIn('private-catalog-error', str(caught.exception))

    def test_existing_mock_backend_runs_all_four_audit_phases_and_keeps_image_gate(self):
        import sys
        from pathlib import Path
        tests_dir = str(Path(__file__).resolve().parent)
        if tests_dir not in sys.path:
            sys.path.insert(0, tests_dir)
        import test_agent as fixtures
        harness = fixtures.AgentRegressionTests('test_valid_pipeline_invokes_separate_fact_review_before_compose')
        harness.setUp()
        try:
            with patch('agent.fetch_vmall_sources', return_value=[]):
                out = self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈', api_config=API)
            self.assertEqual(out['result']['status'], 'ready', out['result'].get('report'))
            self.assertEqual(harness.phases(), ['extract', 'fact_review', 'compose', 'audit'])
            self.assertEqual(len(out['result']['images']), 1)
            self.model.json.assert_not_called()
            harness.model.calls.clear()
            harness.ima.result['images'] = []
            with patch('agent.fetch_vmall_sources', return_value=[]):
                blocked = self.flow.generate_now({}, PRODUCT, '上班族', '门店朋友圈', api_config=API)
            self.assertEqual(blocked['result']['status'], 'needs_clarification')
            self.assertEqual(harness.phases(), [])
        finally:
            harness.doCleanups()

    def test_start_calls_real_guidance_interface_with_only_public_brief(self):
        out = self.flow.start_conversation('轻薄本', '上班族', '门店朋友圈', API)
        self.assertIsNone(out['result'])
        self.assertIsInstance(out['state'], dict)
        self.assertEqual(out['history'][-1]['role'], 'assistant')
        self.assertIn('用于什么场景', out['history'][-1]['content'])
        system, payload = self.model.json.call_args.args
        self.assertEqual(set(payload), {'basic', 'history', 'catalog'})
        self.assertEqual(payload['catalog'], [PRODUCT])
        self.assertEqual(payload['basic']['product'], '轻薄本')
        self.assertIn('不用模型记忆', system)
        self.assertIn('API', system)
        self.assertNotIn(API['api_key'], json.dumps(out))
        self.assertIn('轻薄本', out['summary'])
