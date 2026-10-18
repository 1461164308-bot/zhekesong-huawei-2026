"""Synthetic fixtures only: no shared-knowledge-base material or secrets."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import requests

from ima_client import IMAClient, IMAError, _clean_text, _folder, _public_url


PRODUCT = "HUAWEI MateBook Pro S"
OTHER = "HUAWEI MateBook Pro（鸿蒙版）"


def item(media_id, title, parent, media_type=7):
    return {"media_id": media_id, "title": title, "parent_folder_id": parent, "media_type": media_type}


class Response:
    status_code = 200
    headers = {"Content-Type": "text/plain"}

    def __init__(self, payload=None, content=b"synthetic"):
        self.payload, self.content = payload, content

    def json(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, chunk_size):
        yield self.content


class FixtureClient(IMAClient):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.fail_search = False
        self.tree = {
            "": [item("wrap", "Synthetic root", "", 99)],
            "wrap": [item("p1", "P1-产品参数库", "wrap", 99)],
            "p1": [item("harmony", "01-鸿蒙电脑", "p1", 99), item("cards", "06-型号检索卡", "p1", 99), item("extended", "07-扩展产品目录", "p1", 99)],
            "harmony": [item("model", PRODUCT, "harmony", 99)],
            "cards": [item("modelcards", PRODUCT, "cards", 99)],
            "modelcards": [item("identity", "01-型号身份卡.md", "modelcards")],
            "extended": [item("consumer", "消费级 PC", "extended", 99)],
            "consumer": [item("discovery", "01-" + PRODUCT + ".md", "consumer"), item("other-discovery", "02-" + OTHER + ".md", "consumer")],
            "model": [item("facts", "产品事实.md", "model"), item("marketing", "卖点与限制.md", "model"), item("index", "图片索引.csv", "model", 5), item("pictures", "images", "model", 99)],
            "pictures": [item("image", "synthetic-product.png", "pictures", 9)],
        }
        self.documents = {
            "facts": "# " + PRODUCT + "\nSynthetic screen fact. Version-dependent.\nhttps://consumer.huawei.com/cn/laptops/example/\nhttps://storage.myqcloud.com/asset?sign=synthetic\n![Library caption](images/synthetic-product.png)",
            "identity": "# " + PRODUCT + "\nSynthetic identity only.",
            "marketing": "# " + PRODUCT + "\nSynthetic marketing only.",
            "discovery": "# " + PRODUCT + "\n发现卡：本卡不是完整规格。",
            "other-discovery": "# " + OTHER + "\nUnrelated synthetic model.",
            "index": "文件名,产品型号,原始图片URL,官网图片说明\nsynthetic-product.png," + PRODUCT + ",https://consumer.huawei.com/images/synthetic.png,Library caption from CSV\n",
        }

    def _api(self, endpoint, body):
        self.calls.append((endpoint, body))
        if endpoint == "search_knowledge_base":
            return {"info_list": [{"kb_id": "synthetic-kb", "kb_name": self.kb_name, "role_type": "普通成员", "content_count": "19"}], "is_end": True}
        if endpoint == "get_knowledge_base":
            return {"infos": {"synthetic-kb": {"name": self.kb_name}}}
        if endpoint == "get_knowledge_list":
            return {"knowledge_list": self.tree.get(body.get("folder_id", ""), []), "is_end": True}
        if endpoint == "search_knowledge":
            if self.fail_search:
                raise IMAError("Synthetic search failure")
            return {"info_list": [item("unrelated", "Old marketing.md", "p6"), self.tree["consumer"][1]], "is_end": True}
        if endpoint == "get_media_info":
            media_id = body["media_id"]
            if media_id in self.tree:
                raise AssertionError("Folder must not reach get_media_info")
            return {"media_type": 9 if media_id == "image" else 7, "_fixture_id": media_id}
        raise AssertionError(endpoint)

    def _asset(self, entry):
        if _folder(entry):
            raise IMAError("Synthetic folder cannot be media")
        info = self._api("get_media_info", {"media_id": entry["media_id"]})
        content, content_type = self._download(info)
        return content, {"_content_type": content_type, "_origin": "live_ima"}

    def _download(self, info, **kwargs):
        media_id = info["_fixture_id"]
        if media_id == "image":
            return b"\x89PNG\r\n\x1a\nsynthetic-image", "image/png"
        return self.documents[media_id].encode("utf-8"), "text/plain"


class IMAClientTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"IMA_OPENAPI_CLIENTID": "synthetic-client-1234", "IMA_OPENAPI_APIKEY": "synthetic-api-key", "IMA_KB_NAME": "Synthetic KB"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_missing_credentials_is_display_safe(self):
        with patch.dict(os.environ, {"IMA_OPENAPI_CLIENTID": "", "IMA_OPENAPI_APIKEY": ""}):
            result = IMAClient().connection_status()
        self.assertFalse(result["connected"])
        self.assertEqual(result["content_count"], 0)
        self.assertIn("未配置", result["message"])

    def test_connection_label_is_client_tail_and_role_not_username(self):
        status = FixtureClient().connection_status()
        self.assertTrue(status["connected"])
        self.assertEqual(status["content_count"], 19)
        self.assertIn("1234", status["account_label"])
        self.assertIn("普通成员", status["account_label"])
        self.assertNotIn("synthetic-client", status["account_label"])

    def test_api_credentials_only_on_fixed_ima_endpoint(self):
        with patch("ima_client.requests.post", return_value=Response({"code": 0, "data": {}})) as post:
            IMAClient()._api("get_media_info", {"media_id": "synthetic"})
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://ima.qq.com/openapi/wiki/v1/get_media_info")
        self.assertEqual(kwargs["headers"]["ima-openapi-ctx"], "skill_version=1.1.10")
        self.assertFalse(kwargs["allow_redirects"])

    def test_api_error_hides_credentials_and_resource_urls(self):
        payload = {"code": 3, "msg": "synthetic-api-key https://bucket.myqcloud.com/asset?sign=private"}
        with patch("ima_client.requests.post", return_value=Response(payload)):
            with self.assertRaises(IMAError) as error:
                IMAClient()._api("get_media_info", {})
        self.assertNotIn("synthetic-api-key", str(error.exception))
        self.assertNotIn("sign=", str(error.exception))

    def test_network_errors_do_not_echo_request(self):
        with patch("ima_client.requests.post", side_effect=requests.RequestException("private headers and signed URL")):
            with self.assertRaises(IMAError) as error:
                IMAClient()._api("get_media_info", {})
        self.assertNotIn("private", str(error.exception))

    def test_download_headers_are_scoped_and_no_ima_credentials(self):
        resource = {"url_info": {"url": "https://bucket.myqcloud.com/asset?sign=synthetic", "headers": {"Authorization": "scoped-download-token", "ima-openapi-clientid": "synthetic-client-1234", "ima-openapi-apikey": "synthetic-api-key", "X-Injected": "synthetic-api-key", "Host": "evil.example"}}}
        with patch("ima_client.requests.get", return_value=Response()) as get:
            IMAClient()._download(resource)
        _, kwargs = get.call_args
        self.assertEqual(kwargs["headers"], {"Authorization": "scoped-download-token"})
        self.assertFalse(kwargs["allow_redirects"])

    def test_download_rejects_untrusted_host_without_network(self):
        bad = ["http://bucket.myqcloud.com/a", "https://bucket.myqcloud.com.evil.example/a", "https://consumer.huawei.com/a", "https://user@bucket.myqcloud.com/a", "https://bucket.myqcloud.com:8443/a"]
        with patch("ima_client.requests.get") as get:
            for url in bad:
                with self.subTest(url=url), self.assertRaises(IMAError):
                    IMAClient()._download({"url_info": {"url": url}})
        get.assert_not_called()

    def test_download_rejects_redirect(self):
        response = Response()
        response.status_code = 302
        with patch("ima_client.requests.get", return_value=response):
            with self.assertRaises(IMAError):
                IMAClient()._download({"url_info": {"url": "https://bucket.myqcloud.com/asset"}})

    def test_download_size_cap(self):
        with patch("ima_client.requests.get", return_value=Response(content=b"123456")):
            with self.assertRaises(IMAError):
                IMAClient()._download({"url_info": {"url": "https://bucket.myqcloud.com/asset"}}, limit=5)

    def test_type99_folder_never_read_as_media(self):
        client = FixtureClient()
        self.assertTrue(_folder(item("opaque-id", "folder", "", 99)))
        with self.assertRaises(IMAError):
            client._read_entry(item("opaque-id", "folder", "", 99))
        self.assertEqual(client.calls, [])

    def test_catalog_is_dynamic_and_exact(self):
        client = FixtureClient()
        self.assertEqual(client.catalog(), [PRODUCT, OTHER])
        self.assertEqual(client._canonical("MateBook Pro S"), PRODUCT)
        with self.assertRaises(IMAError):
            client._canonical("MateBook")
        self.assertEqual(client._mentioned("HUAWEI MateBook Pro S"), {PRODUCT})
        self.assertEqual(client._mentioned(PRODUCT + " vs " + OTHER), {PRODUCT, OTHER})

    def test_retrieve_prioritizes_p1_and_filters_fuzzy_search(self):
        client = FixtureClient()
        with tempfile.TemporaryDirectory() as folder:
            client._cache_dir = Path(folder)
            result = client.retrieve(PRODUCT)
            self.assertEqual(result["product"], PRODUCT)
            self.assertEqual(result["sources"][0]["kind"], "facts")
            self.assertIn("产品事实", result["sources"][0]["title"])
            read_ids = {body["media_id"] for endpoint, body in client.calls if endpoint == "get_media_info"}
            self.assertNotIn("unrelated", read_ids)
            self.assertNotIn("other-discovery", read_ids)
            image = result["images"][0]
            self.assertTrue(Path(image["path"]).is_file())
            self.assertEqual(image["model"], PRODUCT)
            self.assertEqual(image["caption"], "Library caption from CSV")
            self.assertEqual(image["source_id"], "S1")
            self.assertTrue(image["url"].startswith("https://consumer.huawei.com/"))
            self.assertNotIn("sign=", str(result))
            self.assertNotIn("url_info", str(result))
            discovery = next(x for x in result["sources"] if x["media_id"] == "discovery")
            self.assertEqual(discovery["kind"], "marketing")

    def test_retrieve_search_failure_uses_browsed_folder(self):
        client = FixtureClient()
        client.fail_search = True
        result = client.retrieve(PRODUCT, max_images=0)
        self.assertTrue(result["sources"])
        self.assertTrue(any("回退" in x for x in result["warnings"]))

    def test_cross_model_text_is_not_a_fact(self):
        client = FixtureClient()
        client.documents["facts"] += "\n" + OTHER + " comparison."
        result = client.retrieve(PRODUCT, max_images=0)
        self.assertFalse(any(x["media_id"] == "facts" for x in result["sources"]))
        self.assertTrue(any("跨型号" in x for x in result["warnings"]))

    def test_competitor_text_is_not_returned_as_facts(self):
        client = FixtureClient()
        client.documents["facts"] += "\nCompare with MacBook."
        result = client.retrieve(PRODUCT, max_images=0)
        self.assertFalse(any(x["media_id"] == "facts" for x in result["sources"]))

    def test_cross_model_image_index_is_rejected(self):
        client = FixtureClient()
        client.documents["index"] = client.documents["index"].replace(PRODUCT, OTHER)
        result = client.retrieve(PRODUCT)
        self.assertEqual(result["images"], [])
        self.assertTrue(any("型号不符" in x for x in result["warnings"]))

    def test_shared_official_url_slug_is_not_a_model_assertion(self):
        client = FixtureClient()
        client._products = ["HUAWEI MateBook 14 酷睿 Ultra", "HUAWEI MateBook 14（鸿蒙版）"]
        mentions = client._mentioned("HUAWEI MateBook 14 酷睿 Ultra https://consumer.huawei.com/cn/laptops/matebook-14/specs/")
        self.assertEqual(mentions, {"HUAWEI MateBook 14 酷睿 Ultra"})

    def test_result_limits(self):
        result = FixtureClient().retrieve(PRODUCT, max_sources=1, max_images=0)
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["images"], [])

    def test_signed_and_unofficial_urls_are_never_public(self):
        self.assertEqual(_public_url("https://consumer.huawei.com/image.png?sign=private"), "")
        self.assertEqual(_public_url("https://consumer.huawei.com.evil.example/a"), "")
        self.assertEqual(_public_url("https://bucket.myqcloud.com/a?sign=x"), "")
        self.assertEqual(_public_url("https://consumer.huawei.com/image.png"), "https://consumer.huawei.com/image.png")
        self.assertNotIn("private", _clean_text("Image https://bucket.myqcloud.com/a?sign=private"))

    def test_different_years_and_operating_systems_are_not_aliases(self):
        self.assertFalse(IMAClient._same_alias("MateBook D 14 2024", "MateBook D 14 2025"))
        self.assertFalse(IMAClient._same_alias("MateBook D 14 2024", "MateBook D 14 2026"))
        self.assertTrue(IMAClient._same_alias("MateBook D 14", "MateBook D 14 2024"))
        self.assertFalse(IMAClient._same_alias("MateBook 14（鸿蒙版）", "MateBook 14（Windows版）"))

    def test_system_temp_cache_reused_across_instances(self):
        with tempfile.TemporaryDirectory() as folder:
            first = IMAClient()
            first._persistent_cache = Path(folder)
            entry = item("cache-test", "Synthetic.md", "model")
            with patch.object(first, "_api", return_value={"media_type": 7}), patch.object(first, "_download", return_value=(b"synthetic fact", "text/plain")):
                data, info = first._asset(entry)
            second = IMAClient()
            second._persistent_cache = Path(folder)
            with patch.object(second, "_api", side_effect=AssertionError("Cache must avoid another media request")):
                cached, cache_info = second._asset(entry)
            self.assertEqual(data, cached)
            self.assertEqual(cache_info["_origin"], "ima_cache")
            self.assertEqual(info["_retrieved_at"], cache_info["_retrieved_at"])
            for metadata in Path(folder).glob("*.json"):
                self.assertNotIn("url_info", metadata.read_text(encoding="utf-8"))
                self.assertNotIn("synthetic-api-key", metadata.read_text(encoding="utf-8"))

    def test_daily_quota_failure_trips_circuit(self):
        with tempfile.TemporaryDirectory() as folder:
            client = IMAClient()
            client._persistent_cache = Path(folder)
            payload = {"code": 42, "msg": "资料获取次数已达上限，请明天再尝试"}
            with patch("ima_client.requests.post", return_value=Response(payload)) as post:
                for _ in range(2):
                    with self.assertRaises(IMAError):
                        client._api("get_media_info", {"media_id": "test"})
            self.assertEqual(post.call_count, 1)

    def test_authorized_archive_mode_is_explicit_and_never_requests_network(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "synthetic.zip"
            root = "Synthetic/P1-产品参数库/"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(root + "01-鸿蒙电脑/" + PRODUCT + "/产品事实.md", "# " + PRODUCT + "\nSynthetic archived fact.")
                bundle.writestr(root + "01-鸿蒙电脑/" + PRODUCT + "/images/test.png", b"\x89PNG\r\n\x1a\nsynthetic")
                bundle.writestr(root + "07-扩展产品目录/消费级 PC/01-" + PRODUCT + ".md", "# " + PRODUCT + "\n发现卡")
            client = IMAClient()
            client._cache_dir = Path(folder)
            with patch("ima_client.requests.post", side_effect=AssertionError("Offline archive must not make network requests")):
                loaded = client.load_archive(archive)
                result = client.retrieve(PRODUCT)
                status = client.connection_status()
            self.assertTrue(loaded["loaded"])
            self.assertEqual(result["retrieval_mode"], "offline_archive")
            self.assertTrue(result["offline_archive"])
            self.assertFalse(status["connected"])
            self.assertTrue(all(x["origin"] == "offline_archive" for x in result["sources"] + result["images"]))
            self.assertTrue(all(x["media_id"].startswith("archive:") for x in result["sources"] + result["images"]))
            self.assertTrue(any("非" in x and "实时" in x for x in result["warnings"]))

    def test_archive_path_traversal_is_rejected_without_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../unsafe.md", "synthetic")
            with self.assertRaises(IMAError):
                IMAClient().load_archive(archive)
            self.assertFalse((Path(folder) / "unsafe.md").exists())

    def test_repeated_pagination_cursor_stops(self):
        client = IMAClient()
        with patch.object(client, "_api", return_value={"info_list": [], "is_end": False, "next_cursor": "same"}):
            with self.assertRaises(IMAError):
                client._pages("search_knowledge", {}, "info_list")


if __name__ == "__main__":
    unittest.main()
