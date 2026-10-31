#!/usr/bin/env python3
"""Read-only Codex account + local task observer. No model requests or credential reads."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import selectors
import signal
import shutil
import sqlite3
import subprocess
import sys
import threading
import time

HOME = Path.home()
CODEX_HOME = Path(os.environ.get('CODEX_HOME', str(HOME / '.codex')))
STATE = HOME / 'Library/Application Support/Codex Meter'


class SyncError(RuntimeError):
    """Safe user-facing failure; never persist raw server errors or credentials."""


def retry_delay(failures):
    return (5, 15, 30, 60)[min(max(failures - 1, 0), 3)] if failures else 60


def stamp(value):
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError, AttributeError):
        return 0


def normalize_limits(result, now=None):
    now = now or time.time()
    buckets = result.get('rateLimitsByLimitId')
    bucket = buckets.get('codex', {}) if isinstance(buckets, dict) else result.get('rateLimits') or {}
    windows = []
    for key in ('primary', 'secondary'):
        w = bucket.get(key)
        if not isinstance(w, dict):
            continue
        used, minutes, reset = w.get('usedPercent'), w.get('windowDurationMins'), w.get('resetsAt')
        if not isinstance(used, (int, float)):
            continue
        name = '每周额度' if minutes == 10080 else '5 小时额度' if minutes == 300 else f'{minutes} 分钟额度' if minutes else '账户额度'
        windows.append({'id': key, 'known': True, 'idle': False, 'label': name,
                        'percentUsed': min(100, max(0, used)), 'minutes': minutes,
                        'startsAt': (reset - minutes * 60) * 1000 if reset and minutes else None,
                        'resetsAt': reset * 1000 if reset else None})
    windows.sort(key=lambda w: w['minutes'] or 0)
    return {'windows': windows, 'plan': bucket.get('planType'), 'liveAt': now * 1000,
            'resetCredits': (result.get('rateLimitResetCredits') or {}).get('availableCount'),
            'creditBalance': (bucket.get('credits') or {}).get('balance')}


class RPC:
    def __init__(self, binary):
        self.process = subprocess.Popen([binary, 'app-server', '--stdio'], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b''
        self.counter = 0

    def send(self, message):
        self.process.stdin.write((json.dumps(message) + '\n').encode())
        self.process.stdin.flush()

    def call(self, method, params=None):
        self.counter += 1
        message = {'id': self.counter, 'method': method}
        if params is not None:
            message['params'] = params
        self.send(message)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                value = json.loads(line)
                if value.get('id') == self.counter:
                    if 'error' in value:
                        message = str((value.get('error') or {}).get('message', '')).lower()
                        if any(word in message for word in ('auth', 'login', 'sign in', 'unauthorized')):
                            raise SyncError('Codex 登录已失效，请重新登录')
                        raise SyncError('Codex 额度接口暂不可用，将自动重试')
                    return value['result']
            if self.selector.select(0.5):
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise SyncError('Codex 接口已断开，将自动重连')
                self.buffer += chunk
        raise TimeoutError('Codex interface timed out')

    def close(self):
        self.selector.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()


class Task:
    def __init__(self, row, notify_initial=False):
        self.row = row
        self.notify_initial = notify_initial
        self.offset = 0
        self.state = 'unknown'
        self.turn = ''
        self.started = 0
        self.at = 0
        self.tokens = None
        self.context = None
        self.plan = None
        self.pending_input = None
        self.questions = {}
        self.events = []

    def attention_event(self, call_id, at, notify):
        if notify and at > time.time() - 120:
            self.events.append({'key': f'{self.row["id"]}:{call_id}:reply', 'state': 'waiting',
                                'label': self.row['title'][:70], 'threadId': self.row['id']})

    def resolve_questions(self, content):
        for part in content if isinstance(content, list) else []:
            text = part.get('text', '') if isinstance(part, dict) else ''
            for match in re.finditer(r'<send_user_message_question_reply>\s*(.*?)\s*</send_user_message_question_reply>', text, re.S):
                try:
                    replies = json.loads(match.group(1))
                    for reply in replies:
                        key = json.loads(reply.get('questionItemId', 'null'))
                        if isinstance(key, list) and len(key) == 3 and key[0] == 'request_user_input_async':
                            question = self.questions.get(key[1])
                            if question:
                                question['pending'].discard(key[2])
                                if not question['pending']:
                                    del self.questions[key[1]]
                except (ValueError, TypeError, AttributeError):
                    pass

    def parse(self, obj, notify):
        payload = obj.get('payload') or {}
        at = stamp(obj.get('timestamp'))
        self.at = max(self.at, at)
        kind = payload.get('type')
        if obj.get('type') == 'event_msg':
            if kind == 'task_started':
                self.state, self.turn = 'working', payload.get('turn_id', '')
                self.started = payload.get('started_at') or at
                self.plan, self.pending_input = None, None
                self.questions.clear()
            elif kind in ('task_complete', 'turn_aborted', 'task_failed'):
                if payload.get('turn_id') and self.turn and payload['turn_id'] != self.turn:
                    return
                self.state = {'task_complete': 'done', 'turn_aborted': 'interrupted', 'task_failed': 'error'}[kind]
                self.pending_input = None
                self.questions.clear()
                if notify and at > time.time() - 120:
                    self.events.append({'key': f'{self.row["id"]}:{self.turn}:{self.state}',
                                        'state': self.state, 'label': self.row['title'][:70],
                                        'threadId': self.row['id']})
            elif kind == 'item_completed' and (payload.get('item') or {}).get('type') == 'UserMessage':
                self.resolve_questions(payload['item'].get('content'))
            elif kind == 'token_count':
                info = payload.get('info') or {}
                self.tokens = (info.get('total_token_usage') or {}).get('total_tokens', self.tokens)
                limit = info.get('model_context_window')
                last = (info.get('last_token_usage') or {}).get('total_tokens')
                if limit and last is not None:
                    self.context = min(100, round(last / limit * 100))
        elif obj.get('type') == 'response_item':
            name = payload.get('name', '').split('.')[-1]
            if kind in ('function_call', 'custom_tool_call') and name == 'update_plan':
                try:
                    args = json.loads(payload.get('arguments') or payload.get('input') or '{}')
                    plan = args.get('plan')
                    if isinstance(plan, list) and plan:
                        self.plan = {'done': sum(p.get('status') == 'completed' for p in plan), 'total': len(plan)}
                except (ValueError, TypeError):
                    pass
            elif kind == 'function_call' and name == 'request_user_input':
                self.state, self.pending_input = 'waiting', payload.get('call_id')
                self.attention_event(self.pending_input, at, notify)
            elif kind == 'function_call' and name == 'request_user_input_async':
                try:
                    args = json.loads(payload.get('arguments') or '{}')
                    questions = args.get('questions')
                    if isinstance(questions, list) and questions:
                        self.questions[payload['call_id']] = {'pending': set(range(len(questions))), 'accepted': False}
                except (ValueError, TypeError, KeyError):
                    pass
            elif kind in ('function_call_output', 'custom_tool_call_output') and self.pending_input and payload.get('call_id') == self.pending_input:
                self.pending_input, self.state = None, 'working'
            elif kind in ('function_call_output', 'custom_tool_call_output') and payload.get('call_id') in self.questions:
                call_id = payload['call_id']
                try:
                    output = json.loads(payload.get('output') or '{}')
                    accepted = isinstance(output, dict) and output.get('accepted') is True
                except (ValueError, TypeError):
                    accepted = False
                if accepted:
                    if not self.questions[call_id]['accepted']:
                        self.attention_event(call_id, at, notify)
                    self.questions[call_id]['accepted'] = True
                else:
                    del self.questions[call_id]
            elif kind == 'message' and payload.get('role') == 'user':
                self.resolve_questions(payload.get('content'))

    def scan(self):
        path = Path(self.row['rollout_path'])
        initial = self.offset == 0
        try:
            size = path.stat().st_size
            if size < self.offset:
                self.offset = 0
                self.state, self.turn, self.tokens, self.plan = 'unknown', '', None, None
                self.pending_input = None
                self.questions.clear()
                initial = True
            with path.open('rb') as file:
                file.seek(self.offset)
                for line in file:
                    if not line.endswith(b'\n'):
                        break
                    self.offset += len(line)
                    # Ignore conversation messages and tool output unless it resolves a known input request.
                    if b'"event_msg"' not in line and b'"function_call"' not in line and not self.pending_input and not self.questions:
                        continue
                    try:
                        self.parse(json.loads(line), not initial or self.notify_initial)
                    except (ValueError, TypeError, AttributeError):
                        continue
        except OSError:
            self.state = 'unknown'

    def snapshot(self, now):
        state = self.state
        if state in ('working', 'waiting') and now - self.at > 1800:
            state = 'unknown'
        return {'id': self.row['id'], 'title': self.row['title'][:90], 'state': state,
                'startedAt': self.started * 1000, 'updatedAt': self.at * 1000,
                'tokens': self.tokens, 'contextPercent': self.context, 'plan': self.plan,
                'attention': 'reply' if state in ('working', 'waiting') and (self.pending_input or any(q['accepted'] for q in self.questions.values())) else None}


class Observer:
    def __init__(self, codex_home=CODEX_HOME):
        self.home = codex_home
        self.tasks = {}
        self.problem = ''
        self.primed = False

    def scan(self):
        try:
            candidates = sorted(self.home.glob('state_*.sqlite'), key=lambda p: int(p.stem.split('_')[-1]), reverse=True)
            if not candidates:
                raise OSError('No Codex task index')
            db = sqlite3.connect(candidates[0].as_uri() + '?mode=ro', uri=True, timeout=1)
            db.row_factory = sqlite3.Row
            try:
                rows = db.execute("SELECT id, rollout_path, COALESCE(NULLIF(name,''), substr(title,1,90),'Codex task') AS title FROM threads WHERE archived=0 AND source NOT LIKE '%subagent%' ORDER BY updated_at_ms DESC LIMIT 60").fetchall()
            finally:
                db.close()
            self.problem = ''
            ids = {row['id'] for row in rows}
            self.tasks = {k: v for k, v in self.tasks.items() if k in ids}
            for row in rows:
                task = self.tasks.setdefault(row['id'], Task(dict(row), notify_initial=self.primed))
                task.row = dict(row)
                task.scan()
            self.primed = True
        except (sqlite3.Error, OSError, ValueError):
            self.problem = '任务数据暂不可用'
        now = time.time()
        tasks = [t.snapshot(now) for t in self.tasks.values()]
        tasks.sort(key=lambda t: (t['state'] not in ('working', 'waiting'), -t['updatedAt']))
        events = [event for t in self.tasks.values() for event in t.events]
        for t in self.tasks.values():
            t.events.clear()
        return tasks, events


def find_binary(app_roots=None):
    # Re-discover on every attempt: desktop updates can move/replace the CLI.
    roots = app_roots if app_roots is not None else [Path('/Applications'), HOME / 'Applications']
    candidates = []
    for root in roots:
        for name in ('ChatGPT.app', 'Codex.app'):
            resources = Path(root) / name / 'Contents/Resources'
            candidates.extend(resources / suffix for suffix in (
                'codex-cli/bin/codex', 'codex-cli/CodexCLI.app/Contents/MacOS/codex', 'codex'))
    candidates.extend(Path(p) for p in ('/opt/homebrew/bin/codex', '/usr/local/bin/codex'))
    on_path = shutil.which('codex')
    if on_path:
        candidates.append(Path(on_path))
    return next((str(p) for p in candidates if p.is_file() and os.access(p, os.X_OK)), None)


def main():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    stop, refresh = threading.Event(), threading.Event()
    lock = threading.Lock()
    current = {'windows': [], 'liveAt': None, 'live': False, 'liveProblem': '正在连接 Codex'}
    try:
        cached = json.loads((STATE / 'usage.json').read_text())
        current.update(cached)
        current['live'] = False
    except (OSError, ValueError):
        pass
    active_rpc = [None]

    def poll_account():
        failures = 0
        while not stop.is_set():
            rpc = None
            try:
                binary = find_binary()
                if not binary:
                    raise SyncError('找不到 Codex 接口，请安装或更新 ChatGPT / Codex')
                rpc = RPC(binary)
                active_rpc[0] = rpc
                rpc.call('initialize', {'clientInfo': {'name': 'codex_meter', 'title': 'Codex Meter', 'version': '1.0.0'}})
                rpc.send({'method': 'initialized', 'params': {}})
                # This method only reads account limits. Never start/resume/modify a task.
                data = normalize_limits(rpc.call('account/rateLimits/read'))
                if not data['windows']:
                    raise SyncError('账户暂未返回额度，将自动重试')
                data.update(live=True, liveProblem='')
                with lock:
                    current.clear()
                    current.update(data)
                tmp = STATE / 'usage.tmp'
                tmp.write_text(json.dumps(data))
                os.chmod(tmp, 0o600)
                tmp.replace(STATE / 'usage.json')
                failures = 0
            except Exception as error:
                failures += 1
                problem = str(error) if isinstance(error, SyncError) else (
                    '额度查询超时，将自动重试' if isinstance(error, TimeoutError)
                    else '额度连接失败，将自动重试')
                with lock:
                    current.update(live=False, liveProblem=problem)
            finally:
                if rpc:
                    rpc.close()
                active_rpc[0] = None
            refresh.wait(retry_delay(failures))
            refresh.clear()

    def input_loop():
        for line in sys.stdin:
            if line.strip() == 'refresh':
                refresh.set()
        stop.set()
        refresh.set()

    def shutdown(*_):
        stop.set()
        refresh.set()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    threading.Thread(target=poll_account, daemon=True).start()
    threading.Thread(target=input_loop, daemon=True).start()
    observer = Observer()
    try:
        while not stop.is_set():
            tasks, events = observer.scan()
            with lock:
                payload = dict(current)
            payload.update(now=time.time() * 1000, tasks=tasks, events=events, taskProblem=observer.problem)
            print(json.dumps(payload, ensure_ascii=False), flush=True)
            stop.wait(2)
    except BrokenPipeError:
        pass
    finally:
        stop.set()
        rpc = active_rpc[0]
        if rpc and rpc.process.poll() is None:
            rpc.process.terminate()


if __name__ == '__main__':
    main()
