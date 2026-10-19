"""Synthetic authorized workspace fixtures; never call external services."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import agent
import knowledge_store


class LocalKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / '任德耀新建华为PC知识库' / '华为PC全板块深度知识库_v7'
        self.facts = self.source / 'P1-产品参数库' / '01-Windows' / 'MateBook Test 2026' / '产品事实.md'
        self.facts.parent.mkdir(parents=True)
        self.facts.write_text('# HUAWEI MateBook Test 2026\n合成事实甲。', encoding='utf-8')
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {}, clear=True).start()
        patch.object(knowledge_store, 'WORKSPACE_ROOT', self.root, create=True).start()
        patch('requests.sessions.Session.request', side_effect=AssertionError('network forbidden')).start()

    def test_default_discovers_authorized_workspace_without_network(self):
        client = agent._ima()
        self.assertEqual(client.catalog(), ['HUAWEI MateBook Test 2026'])
        result = client.retrieve(client.catalog()[0])
        self.assertEqual(result['retrieval_mode'], 'offline_archive')
        self.assertIn('合成事实甲', result['sources'][0]['text'])
        self.assertEqual(result['sources'][0]['origin'], 'offline_archive')
        self.assertIn('工作区授权知识库', agent.get_connection_status())
        self.assertIn('本地只读', agent.get_connection_status())
        self.assertIn('非实时 ima', agent.get_connection_status())
        caches = list((self.root / '.local' / 'knowledge-cache').glob('*.zip'))
        self.assertEqual(len(caches), 1)
        with zipfile.ZipFile(caches[0]) as bundle:
            self.assertTrue(all(n.startswith('P1-产品参数库/') for n in bundle.namelist()))

    def test_rejects_link_detection_without_os_privileges(self):
        original = Path.is_symlink
        with patch.object(Path, 'is_symlink', lambda p: p == self.facts or original(p)):
            with self.assertRaises(agent.IMAError):
                knowledge_store.get_workspace_archive()

    def test_workspace_status_and_retrieval_name_the_actual_local_source(self):
        client = agent._ima()
        self.assertIn('工作区授权知识库', client.connection_status()['message'])
        self.assertNotIn('ClientID', client.connection_status()['account_label'])
        result = client.retrieve('HUAWEI MateBook Test 2026')
        self.assertTrue(any('工作区授权知识库' in w and '非实时 ima' in w for w in result['warnings']))

    def test_official_product_db_extends_catalog_and_dedupes_same_model(self):
        db = self.root / '华为官方产品库_v1' / 'P1-产品参数库'
        phone = db / '01-手机' / 'HUAWEI Mate 90 Pro'
        phone.mkdir(parents=True)
        (phone / '产品事实.md').write_text('# HUAWEI Mate 90 Pro\n合成手机事实。', encoding='utf-8')
        duplicate = db / '04-笔记本' / 'MateBook Test 2026'
        duplicate.mkdir(parents=True)
        (duplicate / '产品事实.md').write_text('# 重复型号\n不应被收录。', encoding='utf-8')
        client = agent._ima()
        self.assertEqual(sorted(client.catalog()), ['HUAWEI Mate 90 Pro', 'HUAWEI MateBook Test 2026'])
        result = client.retrieve('HUAWEI Mate 90 Pro')
        self.assertIn('合成手机事实', result['sources'][0]['text'])
        self.assertEqual(len(list((self.root / '.local' / 'knowledge-cache').glob('*.zip'))), 1)

    def test_index_folders_never_become_products(self):
        index = self.root / '华为官方产品库_v1' / 'P1-产品参数库' / '16-型号检索卡' / 'HUAWEI Nova 99'
        index.mkdir(parents=True)
        (index / '产品事实.md').write_text('# 索引卡\n不是参数事实。', encoding='utf-8')
        entries = [entry for entry in agent._ima()._products]
        self.assertNotIn('HUAWEI Nova 99', entries)

    def test_explicit_invalid_configuration_is_visible_in_public_status(self):
        with patch.dict(os.environ, {'IMA_SOURCE_MODE': 'bogus'}):
            self.assertIn('IMA_SOURCE_MODE', agent.get_connection_status())

    def test_windows_junction_is_rejected_before_read(self):
        if os.name != 'nt':
            self.skipTest('Windows junction test')
        import _winapi
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'notes.md').write_text('not authorized', encoding='utf-8')
        junction = self.facts.parent / 'junction'
        _winapi.CreateJunction(str(outside), str(junction))
        try:
            with self.assertRaises(agent.IMAError):
                knowledge_store.get_workspace_archive()
        finally:
            junction.rmdir()

    def test_too_many_entries_are_rejected(self):
        with patch.object(knowledge_store.os, 'walk', return_value=[(str(self.facts.parent), [], ['x.md'] * 12001)]):
            with self.assertRaises(agent.IMAError):
                knowledge_store.get_workspace_archive()

    def test_explicit_valid_archive_overrides_workspace(self):
        authorized = self.root / 'explicit.zip'
        with zipfile.ZipFile(authorized, 'w') as bundle:
            bundle.writestr('P1-产品参数库/01-Windows/MateBook Explicit 2026/产品事实.md',
                            '# HUAWEI MateBook Explicit 2026\n合成显式资料。')
        with patch.dict(os.environ, {'IMA_ARCHIVE_PATH': str(authorized)}):
            self.assertEqual(agent._ima().catalog(), ['HUAWEI MateBook Explicit 2026'])

    def test_rejects_secret_named_markdown_and_internal_folders(self):
        (self.facts.parent / 'credentials.md').write_text('private', encoding='utf-8')
        (self.facts.parent / '.env.md').write_text('private', encoding='utf-8')
        internal = self.facts.parent / '内部机密'
        internal.mkdir()
        (internal / 'notes.md').write_text('private', encoding='utf-8')
        path = knowledge_store.get_workspace_archive()
        with zipfile.ZipFile(path) as bundle:
            self.assertEqual(len(bundle.namelist()), 1)

    def test_rejects_symlinked_source_file(self):
        outside = self.root / 'outside.md'
        outside.write_text('not authorized', encoding='utf-8')
        link = self.facts.parent / 'linked.md'
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest('OS does not permit symlinks')
        with self.assertRaises(agent.IMAError):
            knowledge_store.get_workspace_archive()

    def test_rejects_cached_archive_tampering(self):
        path = Path(knowledge_store.get_workspace_archive())
        path.write_bytes(b'corrupted cache')
        client = agent._ima()
        self.assertTrue(client.catalog())

    def test_refresh_reads_changed_content_even_with_same_size_and_mtime(self):
        first = knowledge_store.get_workspace_archive()
        stamp = self.facts.stat()
        self.facts.write_text('# HUAWEI MateBook Test 2026\n合成事实乙。', encoding='utf-8')
        os.utime(self.facts, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        self.assertNotEqual(first, knowledge_store.get_workspace_archive())
        result = agent._ima().retrieve('HUAWEI MateBook Test 2026')
        self.assertIn('合成事实乙', result['sources'][0]['text'])

    def test_empty_and_invalid_structure_fail_closed(self):
        self.facts.unlink()
        with self.assertRaises(agent.IMAError):
            agent._ima()
        self.source.rename(self.source.with_name('other'))
        self.source.mkdir()
        with self.assertRaises(agent.IMAError):
            agent._ima()

    def test_explicit_configuration_has_priority(self):
        with patch.dict(os.environ, {'IMA_SOURCE_MODE': 'live'}):
            self.assertFalse(agent._ima()._offline_archive)
        for settings in ({'IMA_ARCHIVE_PATH': 'missing.zip'}, {'IMA_ARCHIVE_URL': ''},
                         {'IMA_SOURCE_MODE': 'archive'}, {'IMA_SOURCE_MODE': ''}, {'IMA_SOURCE_MODE': 'bogus'}):
            with self.subTest(settings=settings), patch.dict(os.environ, settings):
                with self.assertRaises(agent.IMAError):
                    agent._ima()

    def test_local_limits_are_checked_before_reading(self):
        with self.facts.open('wb') as stream:
            stream.truncate(25 * 1024 * 1024 + 1)
        with self.assertRaises(agent.IMAError):
            knowledge_store.get_workspace_archive()

