"""Seal the future protocol and inventory published evidence separately from local caches."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


EP = Path(__file__).resolve().parents[1]
OUT = EP / 'outputs'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, record):
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')


def main():
    reg_path = OUT / 'preregistration.json'
    reg = json.loads(reg_path.read_text())
    assert all(digest(EP / k) == v for k, v in reg['files'].items())
    validation = json.loads((OUT / 'validation.json').read_text())
    assert validation['status'] == 'PASS'
    assert '22 passed' in (OUT / 'pytest.txt').read_text()
    prior = json.loads((OUT / 'prior_preservation.json').read_text())
    assert all(digest(EP.parent / k) == v for k, v in prior.items())
    now = datetime.now(timezone.utc).isoformat()
    names = ['validation_protocol.md', 'src/forward.py', 'tests/test_forward_protocol.py']
    protocol = dict(registration_sha256=digest(reg_path),
                    files={name: digest(EP / name) for name in names},
                    scope='future protocol only; not retrospectively preregistered historical analysis',
                    first_eligible_origin='2026-10-30', independent_confirmation=False)
    lock_path = OUT / 'prospective_protocol_lock.json'
    if lock_path.exists():
        sealed = json.loads(lock_path.read_text())
        assert {k: v for k, v in sealed.items() if k != 'created_utc'} == protocol
    else:
        assert not (OUT / 'local_cache' / 'prospective').exists()
        write(lock_path, dict(created_utc=now, **protocol))
    support = {}
    for folder in ['src', 'tests']:
        for p in sorted((EP / folder).glob('*.py')):
            key = p.relative_to(EP).as_posix()
            if key not in reg['files']:
                support[key] = digest(p)
    write(OUT / 'supporting_code_manifest.json', dict(
        created_utc=now, historical_registration_sha256=digest(reg_path),
        status='added after historical preregistration; no additional model candidates',
        files=support))
    published, local = {}, {}
    destination = OUT / 'delivery_manifest.json'
    for p in sorted(EP.rglob('*')):
        if not p.is_file() or any(part in ['__pycache__', '.pytest_cache'] for part in p.parts):
            continue
        assert not p.is_symlink(), p
        if p == destination:
            continue
        key = p.relative_to(EP).as_posix()
        record = dict(sha256=digest(p), bytes=p.stat().st_size)
        if key.startswith('outputs/local_cache/'):
            local[key] = record
        else:
            assert p.stat().st_size < 25 * 1024 * 1024, key
            assert p.suffix not in ['.tmp', '.log', '.pyc'], key
            published[key] = record
    write(destination, dict(
        created_utc=now, historical_registration_sha256=digest(reg_path),
        prospective_protocol_lock_sha256=digest(lock_path),
        publication_status='reviewable delivery inventory; remote Git commit is separately verified',
        self_excluded='outputs/delivery_manifest.json',
        source_dependency='original inputs remain external; exact source receipts are published',
        publishable=published, local_only=local,
        publishable_count=len(published), local_only_count=len(local),
        publishable_bytes=sum(v['bytes'] for v in published.values()),
        local_only_bytes=sum(v['bytes'] for v in local.values())))
    assert all(digest(EP / k) == v['sha256'] for k, v in published.items())
    print(json.dumps(dict(status='PASS', published_files=len(published) + 1,
                          local_only_files=len(local), prior_files_unchanged=len(prior),
                          prospective_protocol_sealed=True)))


if __name__ == '__main__':
    main()
