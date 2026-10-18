"""VMall parser/network regressions: all pages and product IDs are synthetic."""
import json
import unittest
from unittest.mock import patch

import requests

from vmall_client import VmallError, fetch_vmall_sources


PRODUCT = "HUAWEI MateBook Pro S"
URL = "https://www.vmall.com/product/123456.html"
DESCRIPTION = "屏幕尺寸为14.2英寸，刷新率最高120 Hz。配置和软件条件请按具体版本核对。"


def page(name=PRODUCT, **extra):
    product = {"@type": "Product", "name": name, "url": URL, "description": DESCRIPTION,
               "additionalProperty": [{"name": "屏幕", "value": "14.2英寸"}], **extra}
    return '<html><script type="application/ld+json">' + json.dumps(product, ensure_ascii=False) + '</script></html>'


class Response:
    def __init__(self, body=None, *, status=200, headers=None, url=URL):
        self.body = (body if body is not None else page()).encode("utf-8")
        self.status_code = status
        self.headers = headers if headers is not None else {"Content-Type": "text/html; charset=utf-8"}
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, size):
        yield self.body


class VmallTests(unittest.TestCase):
    def setUp(self):
        self.network = patch("requests.sessions.Session.request", side_effect=AssertionError("Unexpected network"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def fetch(self, body=None, **kwargs):
        response = Response(body, **kwargs)
        with patch("vmall_client.requests.Session.get", return_value=response):
            return fetch_vmall_sources(PRODUCT, URL)

    def test_no_explicit_mall_link_never_searches_or_guesses(self):
        self.assertEqual(fetch_vmall_sources(PRODUCT, "请补充官方商城参数。"), [])
        self.assertEqual(fetch_vmall_sources(PRODUCT, "https://consumer.huawei.com/"), [])

    def test_root_requires_specific_product_link_without_network(self):
        with self.assertRaisesRegex(VmallError, "具体商品"):
            fetch_vmall_sources(PRODUCT, "https://www.vmall.com/")

    def test_unsafe_hosts_schemes_queries_credentials_and_paths_are_rejected(self):
        urls = ["https://www.vmall.com.evil.example/product/123456.html", "https://evilvmall.com/product/123456.html",
                "http://www.vmall.com/product/123456.html", URL + "?sign=private", URL + "?sku=123",
                URL + "#details", "https://name:secret@www.vmall.com/product/123456.html",
                "https://www.vmall.com:443/product/123456.html", "https://www.vmall.com/search?q=MateBook",
                "https://www.vmall.com/product/../123456.html"]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(VmallError):
                fetch_vmall_sources(PRODUCT, url)

    def test_structured_product_is_read_with_origin_and_no_price_or_images(self):
        result = self.fetch(page(offers={"price": "5999", "priceCurrency": "CNY"}, image="https://image.example/a.jpg"))
        self.assertEqual(len(result), 1)
        source = result[0]
        self.assertEqual(source["origin"], "official_vmall")
        self.assertEqual(source["kind"], "facts")
        self.assertEqual(source["official_url"], URL)
        self.assertIn(DESCRIPTION, source["text"])
        self.assertNotIn("5999", source["text"])
        self.assertNotIn("image.example", source["text"])
        self.assertTrue(source["retrieved_at"])
        self.assertNotIn("id", source)

    def test_primary_html_ignores_recommendations_nav_scripts_and_hidden_text(self):
        html = ('<nav>导航干扰</nav><main><h1>' + PRODUCT + '</h1><p>' + DESCRIPTION + '</p>'
                '<section class="recommend"><h2>推荐</h2><p>HUAWEI MateBook Pro 推荐干扰</p></section>'
                '<p hidden>隐藏干扰</p><script>脚本干扰</script></main><footer>页脚干扰</footer>')
        result = self.fetch(html)
        self.assertIn(DESCRIPTION, result[0]["text"])
        for word in ("导航干扰", "推荐干扰", "隐藏干扰", "脚本干扰", "页脚干扰"):
            self.assertNotIn(word, result[0]["text"])

    def test_recommendation_title_cannot_verify_wrong_main_product(self):
        html = '<main><h1>HUAWEI MateBook Pro</h1><p>' + DESCRIPTION + '</p><aside><h1>' + PRODUCT + '</h1></aside></main>'
        with self.assertRaises(VmallError):
            self.fetch(html)

    def test_year_and_operating_system_and_variant_are_exact(self):
        cases = [(PRODUCT, "HUAWEI MateBook Pro"), (PRODUCT, "HUAWEI MateBook Pro S 2025"),
                 ("HUAWEI MateBook D 14 2024", "HUAWEI MateBook D 14 2025"),
                 ("HUAWEI MateBook D 14 2024", "HUAWEI MateBook D 14"),
                 ("HUAWEI MateBook 14（鸿蒙版）", "HUAWEI MateBook 14（Windows版）"),
                 ("HUAWEI MateBook 14（鸿蒙版）", "HUAWEI MateBook 14")]
        for requested, actual in cases:
            with self.subTest(requested=requested, actual=actual):
                with patch("vmall_client.requests.Session.get", return_value=Response(page(actual))):
                    with self.assertRaises(VmallError):
                        fetch_vmall_sources(requested, URL)

    def test_exact_year_and_os_product_passes(self):
        for product in ("HUAWEI MateBook D 14 2024", "HUAWEI MateBook 14（鸿蒙版）"):
            with self.subTest(product=product), patch("vmall_client.requests.Session.get", return_value=Response(page(product))):
                self.assertEqual(fetch_vmall_sources(product, URL)[0]["title"], product)

    def test_unrelated_jsonld_products_do_not_verify_current_page(self):
        with self.assertRaises(VmallError):
            self.fetch(page(url="https://www.vmall.com/product/999999.html"))
        with self.assertRaises(VmallError):
            self.fetch(page() + '<main><h1>HUAWEI MateBook Pro</h1><p>' + DESCRIPTION + '</p></main>')

    def test_multiple_products_need_current_page_link(self):
        products = [{"@type": "Product", "name": PRODUCT, "description": DESCRIPTION},
                    {"@type": "Product", "name": "HUAWEI MateBook Pro", "description": DESCRIPTION}]
        html = '<script type="application/ld+json">' + json.dumps(products) + '</script>'
        with self.assertRaises(VmallError):
            self.fetch(html)

    def test_jsonld_recommendation_itemlist_is_not_primary_product(self):
        data = {"@type": "ItemList", "itemListElement": [{"@type": "Product", "name": PRODUCT, "description": DESCRIPTION}]}
        html = '<script type="application/ld+json">' + json.dumps(data) + '</script>'
        with self.assertRaises(VmallError):
            self.fetch(html)

    def test_js_only_or_title_only_page_fails_safely(self):
        for html in ('<html><title>' + PRODUCT + '</title><div id="app"></div><script>loadProduct()</script></html>',
                     '<main><h1>' + PRODUCT + '</h1></main>', '<html>安全验证，请启用JavaScript</html>'):
            with self.subTest(html=html), self.assertRaises(VmallError):
                self.fetch(html)

    def test_external_redirect_is_rejected_before_second_request(self):
        response = Response(status=302, headers={"Location": "https://evil.example/product/123456.html"})
        with patch("vmall_client.requests.Session.get", return_value=response) as get:
            with self.assertRaises(VmallError):
                fetch_vmall_sources(PRODUCT, URL)
        self.assertEqual(get.call_count, 1)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])

    def test_content_type_status_and_size_limits_fail_safely(self):
        for response in (Response(headers={"Content-Type": "application/json"}), Response(status=403),
                         Response(headers={"Content-Type": "text/html", "Content-Length": str(3 * 1024 * 1024)}),
                         Response("x" * (2 * 1024 * 1024 + 1))):
            with self.subTest(response=response), patch("vmall_client.requests.Session.get", return_value=response):
                with self.assertRaises(VmallError):
                    fetch_vmall_sources(PRODUCT, URL)

    def test_request_does_not_forward_credentials_or_environment_netrc(self):
        observed = []
        def fake_get(session, url, **kwargs):
            observed.append((session.trust_env, session.auth, kwargs))
            return Response()
        with patch.dict("os.environ", {"IMA_OPENAPI_APIKEY": "synthetic-secret", "LLM_API_KEY": "other-secret"}):
            with patch("vmall_client.requests.Session.get", autospec=True, side_effect=fake_get):
                fetch_vmall_sources(PRODUCT, URL)
        self.assertFalse(observed[0][0])
        self.assertIsNone(observed[0][1])
        headers = str(observed[0][2]["headers"])
        self.assertNotIn("secret", headers)
        self.assertNotIn("Authorization", headers)
        self.assertNotIn("Cookie", headers)

    def test_network_error_never_echoes_request_url_or_credentials(self):
        with patch("vmall_client.requests.Session.get", side_effect=requests.Timeout("password=secret sign=private")):
            with self.assertRaises(VmallError) as caught:
                fetch_vmall_sources(PRODUCT, URL)
        self.assertNotIn("secret", str(caught.exception))
        self.assertNotIn("private", str(caught.exception))

    def test_explicit_links_are_deduplicated_and_bounded(self):
        other = "https://www.vmall.com/product/654321.html"
        with patch("vmall_client.requests.Session.get", return_value=Response()) as get:
            result = fetch_vmall_sources(PRODUCT, URL + " " + URL + " " + other, max_sources=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(get.call_count, 1)
        with patch("vmall_client.requests.Session.get") as get:
            self.assertEqual(fetch_vmall_sources(PRODUCT, URL, max_sources=0), [])
            get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
