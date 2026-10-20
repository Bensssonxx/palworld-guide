"""Optional evidence audit against a supplied Codex CLI JSONL tool trace.

Use one trace per public question. This verifies logged operations, not source
truth, excerpt fidelity, timestamps, or the authenticity of the supplied log.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


class TraceAuditError(ValueError):
    pass


def page_key(url):
    parsed = urlsplit(url)
    return parsed._replace(path=parsed.path.rstrip('/'), fragment='').geturl()


def audit(packet, pending, path):
    path = Path(path)
    if path.stat().st_size > 50_000_000:
        raise TraceAuditError('host-trace-too-large')
    body = path.read_bytes()
    searches, reads = [], []
    lines = body.splitlines(keepends=True)
    for index, line in enumerate(lines):
        try:
            event = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            # A running host may be in the middle of writing its final event.
            if index == len(lines)-1 and not line.endswith(b'\n'):
                break
            raise TraceAuditError('host-trace-invalid-json')
        item = event.get('item', {})
        if event.get('type') != 'item.completed' or item.get('type') != 'web_search':
            continue
        action = item.get('action', {})
        results = item.get('results', [])
        urls = {r['url'] for r in results if r.get('type') == 'text_result' and isinstance(r.get('url'), str)}
        if action.get('type') == 'search':
            queries = action.get('queries', [action.get('query')])
            for query in queries:
                if isinstance(query, str) and query:
                    searches.append((query, urls))
        elif action.get('type') in ('open_page', 'other'):
            # CLI records a successful full-page read as "Total lines: N".
            # Snippets, failed fetches, find-only results and terminal text are
            # deliberately not promoted to page reads by this adapter.
            read_urls = {page_key(r['url']) for r in results if r.get('type') == 'text_result'
                         and r.get('snippet', '').startswith('Total lines:') and r.get('url')}
            if action.get('type') == 'open_page' or read_urls:
                # A batch can be labelled "open_page" with only its first URL,
                # or "other". Count every result, including failed opens.
                for result in results:
                    reads.append({page_key(result['url'])} if result.get('url') and
                                 result.get('snippet', '').startswith('Total lines:') else set())
                if not results:
                    reads.append(set())
    if len(searches) > pending['budget']['searches'] or len(reads) > pending['budget']['reads']:
        raise TraceAuditError('host-trace-budget-exceeded')
    recorded = packet.get('searches', [])
    if Counter(q for q, _ in searches) != Counter(e.get('query') for e in recorded):
        raise TraceAuditError('host-trace-query-mismatch')
    for event in recorded:
        observed = set().union(*(urls for query, urls in searches if query == event['query']))
        if not set(event['result_urls']) <= observed:
            raise TraceAuditError('host-trace-result-url-mismatch')
    opened = set().union(*reads) if reads else set()
    if any(page_key(source['url']) not in opened for source in packet.get('sources', [])):
        raise TraceAuditError('host-trace-page-not-opened')
    return {'status': 'matched', 'adapter': 'codex-cli-jsonl',
            'trace_sha256': hashlib.sha256(body).hexdigest(),
            'search_queries': len(searches), 'page_reads': len(reads),
            'scope': 'Recorded queries, returned URLs, page-open events and budgets only; not source truth, excerpt/timestamp fidelity or log authentication'}
