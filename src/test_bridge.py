import datetime
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from bridge import Task, normalize_limits, find_binary, retry_delay


class SyncTests(unittest.TestCase):
    def test_desktop_update_moves_binary_and_next_poll_rediscovers_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            resources = root / 'ChatGPT.app/Contents/Resources'
            resources.mkdir(parents=True)
            old = resources / 'codex'
            old.write_text('#!/bin/sh\n')
            old.chmod(0o755)
            with patch('bridge.shutil.which', return_value=None):
                self.assertEqual(find_binary([root]), str(old))
                old.unlink()
                new = resources / 'codex-cli/bin/codex'
                new.parent.mkdir(parents=True)
                new.write_text('#!/bin/sh\n')
                new.chmod(0o755)
                self.assertEqual(find_binary([root]), str(new))

    def test_user_application_native_cli_without_wrapper(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = root / 'Codex.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'
            executable.parent.mkdir(parents=True)
            executable.write_text('#!/bin/sh\n')
            executable.chmod(0o755)
            self.assertEqual(find_binary([root]), str(executable))

    def test_retries_are_bounded_and_return_to_normal_after_recovery(self):
        self.assertEqual([retry_delay(i) for i in range(7)], [60, 5, 15, 30, 60, 60, 60])


class QuotaTests(unittest.TestCase):
    def test_weekly_in_primary_is_not_five_hour_window(self):
        value = normalize_limits({'rateLimitsByLimitId': {'codex': {'primary': {
            'usedPercent': 24, 'windowDurationMins': 10080, 'resetsAt': 1791981584}, 'secondary': None}}})
        self.assertEqual(len(value['windows']), 1)
        self.assertEqual(value['windows'][0]['label'], '每周额度')
        self.assertEqual(value['windows'][0]['percentUsed'], 24)
        self.assertEqual(value['windows'][0]['resetsAt'] - value['windows'][0]['startsAt'], 7 * 86400 * 1000)

    def test_missing_quota_is_unknown(self):
        self.assertEqual(normalize_limits({'rateLimits': {'primary': None}})['windows'], [])
        self.assertEqual(normalize_limits({'rateLimits': {'primary': {'usedPercent': None}}})['windows'], [])

    def test_prefer_bucket_map_and_preserve_secondary(self):
        result = {'rateLimits': {'primary': {'usedPercent': 99}}, 'rateLimitsByLimitId': {'codex': {
            'primary': {'usedPercent': 12, 'windowDurationMins': 300, 'resetsAt': 100000},
            'secondary': {'usedPercent': 35, 'windowDurationMins': 10080, 'resetsAt': 200000}}}}
        self.assertEqual([w['percentUsed'] for w in normalize_limits(result)['windows']], [12, 35])


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'task.jsonl'
        self.path.touch()
        self.row = {'id': 'test', 'title': 'Example', 'rollout_path': str(self.path)}
        self.task = Task(self.row)

    def line(self, kind, **extra):
        return json.dumps({'type': 'event_msg', 'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           'payload': {'type': kind, **extra}}).encode() + b'\n'

    def append(self, kind, **extra):
        with self.path.open('ab') as f:
            f.write(self.line(kind, **extra))

    def response(self, kind, **extra):
        with self.path.open('ab') as f:
            f.write(json.dumps({'type': 'response_item', 'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                'payload': {'type': kind, **extra}}).encode() + b'\n')

    def ask(self, call_id='question', count=1, accepted=True):
        self.response('function_call', name='request_user_input_async', call_id=call_id,
                      arguments=json.dumps({'questions': [{'title': 'Choice'}] * count}))
        self.response('function_call_output', call_id=call_id, output=json.dumps({'accepted': accepted}))

    def reply(self, call_id, index):
        reply = json.dumps([{'questionItemId': json.dumps(['request_user_input_async', call_id, index]), 'answer': 'Yes'}])
        self.append('item_completed', item={'type': 'UserMessage', 'content': [{'type': 'text', 'text':
                    '<send_user_message_question_reply>' + reply + '</send_user_message_question_reply>'}]})

    def test_async_question_flags_attention_without_pausing_work(self):
        self.append('task_started', turn_id='current'); self.task.scan()
        self.ask(); self.task.scan(); self.task.scan()
        self.assertEqual(self.task.snapshot(time.time())['attention'], 'reply')
        self.assertEqual(self.task.state, 'working')
        self.assertEqual(len(self.task.events), 1)
        self.reply('question', 0); self.task.scan()
        self.assertIsNone(self.task.snapshot(time.time())['attention'])

    def test_partial_and_unrelated_answers_do_not_clear_pending_questions(self):
        self.append('task_started', turn_id='current')
        self.ask(count=2); self.task.scan()
        self.assertEqual(self.task.events, [])  # No historical reply notification on startup.
        self.reply('different-call', 0); self.reply('question', 0); self.task.scan()
        self.assertEqual(self.task.snapshot(time.time())['attention'], 'reply')
        self.reply('question', 1); self.task.scan()
        self.assertIsNone(self.task.snapshot(time.time())['attention'])

    def test_failed_question_and_finished_turn_do_not_keep_attention(self):
        self.append('task_started', turn_id='current')
        self.ask(accepted=False); self.task.scan()
        self.assertIsNone(self.task.snapshot(time.time())['attention'])
        self.ask(call_id='valid'); self.task.scan()
        self.assertEqual(self.task.snapshot(time.time())['attention'], 'reply')
        self.append('task_complete', turn_id='current'); self.task.scan()
        self.assertIsNone(self.task.snapshot(time.time())['attention'])

    def test_blocking_input_returns_to_work_after_matching_result(self):
        self.append('task_started', turn_id='current'); self.task.scan()
        self.response('function_call', name='request_user_input', call_id='blocking', arguments='{}'); self.task.scan()
        self.assertEqual(self.task.state, 'waiting')
        self.assertEqual(self.task.snapshot(time.time())['attention'], 'reply')
        self.response('function_call_output', call_id='unrelated', output='{}'); self.task.scan()
        self.assertEqual(self.task.state, 'waiting')
        self.response('function_call_output', call_id='blocking', output='{}'); self.task.scan()
        self.assertEqual(self.task.state, 'working')
        self.assertIsNone(self.task.snapshot(time.time())['attention'])

    def test_no_historical_completion_alert_and_exactly_once_new_alert(self):
        self.append('task_started', turn_id='old')
        self.append('task_complete', turn_id='old')
        self.task.scan()
        self.assertEqual(self.task.state, 'done')
        self.assertEqual(self.task.events, [])
        self.append('task_started', turn_id='new')
        self.task.scan()
        self.assertEqual(self.task.state, 'working')
        self.append('task_complete', turn_id='new')
        self.task.scan(); self.task.scan()
        self.assertEqual(len(self.task.events), 1)

    def test_partial_line_waits_and_duplicate_token_counts_do_not_sum(self):
        line = self.line('task_started', turn_id='new')
        self.path.write_bytes(line[:-5])
        self.task.scan()
        self.assertEqual(self.task.state, 'unknown')
        with self.path.open('ab') as f: f.write(line[-5:])
        self.task.scan()
        self.assertEqual(self.task.state, 'working')
        for _ in range(2): self.append('token_count', info={'total_token_usage': {'total_tokens': 100}})
        self.task.scan()
        self.assertEqual(self.task.tokens, 100)

    def test_short_new_task_completed_between_polls_not_lost(self):
        self.append('task_started', turn_id='short')
        self.append('task_complete', turn_id='short')
        new = Task(self.row, notify_initial=True)
        new.scan()
        self.assertEqual(len(new.events), 1)

    def test_interruption_and_wrong_turn_completion(self):
        self.append('task_started', turn_id='current')
        self.append('task_complete', turn_id='previous')
        self.task.scan()
        self.assertEqual(self.task.state, 'working')
        self.append('turn_aborted', turn_id='current')
        self.task.scan()
        self.assertEqual(self.task.state, 'interrupted')

    def test_silent_old_task_not_claimed_active_forever(self):
        self.task.state, self.task.at = 'working', time.time() - 3600
        self.assertEqual(self.task.snapshot(time.time())['state'], 'unknown')


if __name__ == '__main__':
    unittest.main()
