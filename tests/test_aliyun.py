"""Offline transport/configuration tests. No real account or API requests."""
from pathlib import Path
from unittest.mock import patch, MagicMock
import io
import json
import sys
import tempfile
import unittest
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from verifact_research.inference.aliyun import Config, load_config, AliyunClient, chat_body, call_once


class AliyunTests(unittest.TestCase):
    def setUp(self):
        self.config = Config('synthetic-secret-for-offline-tests')
        self.body = chat_body(self.config, [{'role': 'user', 'content': 'Synthetic only.'}], max_tokens=32)

    def opener(self, status=200, raw=None):
        opener = MagicMock()
        response = opener.open.return_value.__enter__.return_value
        response.status = status
        response.headers = {'x-request-id': 'fake-request-id', 'set-cookie': 'not-saved'}
        response.read.return_value = raw or json.dumps(dict(model=self.config.model, choices=[{'finish_reason': 'stop'}],
            usage={'prompt_tokens': 10, 'completion_tokens': 2})).encode()
        return opener

    def test_config_quotes_empty_key_and_endpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp)/'config'
            file.write_text('# local only\nDASHSCOPE_API_KEY="synthetic-key"\n', encoding='utf-8')
            config = load_config(file)
            self.assertEqual(config.api_key, 'synthetic-key')
            self.assertNotIn(config.api_key, repr(config))
            self.assertTrue(config.endpoint.endswith('/compatible-mode/v1/chat/completions'))
            file.write_text('DASHSCOPE_API_KEY=\n', encoding='utf-8')
            with self.assertRaises(ValueError):AliyunClient(load_config(file)).send(self.body)
            file.write_text('DASHSCOPE_API_KEY=a\nDASHSCOPE_API_KEY=b\n', encoding='utf-8')
            with self.assertRaises(ValueError):load_config(file)

    def test_wrong_endpoint_rejected(self):
        for url in ('http://dashscope.aliyuncs.com/compatible-mode/v1',
                    'https://dashscope.aliyuncs.com.evil.example/compatible-mode/v1',
                    'https://dashscope.aliyuncs.com/api/v1',
                    'https://key@dashscope.aliyuncs.com/compatible-mode/v1'):
            with self.assertRaises(ValueError):Config('test', url)

    def test_exact_http_body_authorization_and_usage_receipt(self):
        opener = self.opener()
        with tempfile.TemporaryDirectory() as temp, patch('urllib.request.build_opener', return_value=opener):
            out = Path(temp)/'attempt'
            summary = call_once(self.config, self.body, out, max_cost_cny=.1, task_used_cny=11.81100623)
            request = opener.open.call_args.args[0]
            self.assertEqual(request.full_url, self.config.endpoint)
            self.assertEqual(request.get_header('Authorization'), 'Bearer '+self.config.api_key)
            self.assertEqual(json.loads(request.data), self.body)
            self.assertFalse(json.loads(request.data)['enable_thinking'])
            self.assertEqual(summary['usage']['prompt_tokens'], 10)
            self.assertAlmostEqual(summary['cumulative_reserved_cny'], 11.91100623)
            self.assertEqual(opener.open.call_count, 1)
            self.assertNotIn(self.config.api_key, ''.join(p.read_text() for p in out.iterdir()))
            self.assertNotIn('set-cookie', (out/'receipt.json').read_text())
            with self.assertRaises(FileExistsError):
                call_once(self.config, self.body, out, max_cost_cny=.1, task_used_cny=11.81100623)
            self.assertEqual(opener.open.call_count, 1)

    def test_timeout_unknown_reservation_no_retry(self):
        with tempfile.TemporaryDirectory() as temp, patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = TimeoutError('must not log '+self.config.api_key)
            out = Path(temp)/'attempt'
            result = call_once(self.config, self.body, out, max_cost_cny=.1, task_used_cny=2)
            self.assertTrue(result['outcome_unknown'])
            self.assertEqual(result['http_status'], 0)
            self.assertEqual(result['cumulative_reserved_cny'], 2.1)
            self.assertEqual(build.return_value.open.call_count, 1)

    def test_http_error_redacted_not_retried(self):
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = urllib.error.HTTPError(self.config.endpoint, 401, 'No', {},
                io.BytesIO(json.dumps({'error': self.config.api_key}).encode()))
            result = AliyunClient(self.config).send(self.body)
            self.assertEqual(result['http_status'], 401)
            self.assertNotIn(self.config.api_key, result['body_text'])
            self.assertIn('[REDACTED_API_KEY]', result['body_text'])
            self.assertEqual(build.return_value.open.call_count, 1)

    def test_error_body_timeout_also_unknown(self):
        with patch('urllib.request.build_opener') as build:
            body = MagicMock()
            body.read.side_effect = TimeoutError('response body unavailable')
            build.return_value.open.side_effect = urllib.error.HTTPError(self.config.endpoint, 503, 'No', {}, body)
            result = AliyunClient(self.config).send(self.body)
            self.assertEqual(result['http_status'], 0)
            self.assertTrue(result['outcome_unknown'])
            self.assertEqual(build.return_value.open.call_count, 1)

    def test_budget_rejected_before_network_or_files(self):
        with tempfile.TemporaryDirectory() as temp, patch('urllib.request.build_opener') as build:
            for used, bound, cap in ((39.95,.1,40), (0,.1,41), (0,float('nan'),40), (-1,.1,40)):
                out = Path(temp)/'attempt'
                with self.assertRaises(ValueError):call_once(self.config,self.body,out,max_cost_cny=bound,task_used_cny=used,task_cap_cny=cap)
                self.assertFalse(out.exists())
            build.assert_not_called()

    def test_model_stream_credential_body_rejected(self):
        for change in ({'model': 'Qwen/Qwen3.8-27B'}, {'stream': True}, {'extra_body': {}},
                       {'max_tokens': 0}, {'metadata': self.config.api_key}):
            with patch('urllib.request.build_opener') as build:
                with self.assertRaises(ValueError):AliyunClient(self.config).send(dict(self.body, **change))
                build.assert_not_called()


if __name__ == '__main__':unittest.main()
