"""Read-only verification of the local runtime snapshot; no model/API access."""
from importlib import metadata
from pathlib import Path
import hashlib
import json
import platform
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    snapshot = HERE / 'snapshot.json'
    if sha(snapshot) != '54abbf989ce0b8ceb3c075fa0e5b2364a4b47159f7fce1ae31fa88cf23f8457a':
        raise ValueError('Runtime snapshot changed')
    record = json.loads(snapshot.read_text())
    failures = []
    expected_python = record['python']
    if (sys.version != expected_python['version']
            or platform.machine() != expected_python['machine']
            or sys.platform != expected_python['platform']
            or sha(Path(sys.executable)) != expected_python['binary_sha256']):
        failures.append('Python/platform fingerprint')
    checked = 0
    for name, package in record['critical_distributions'].items():
        try:
            installed = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            failures.append(name + ': missing distribution')
            continue
        if installed.version != package['version']:
            failures.append(name + ': version')
        for filename, expected in package['files_sha256'].items():
            path = Path(installed.locate_file(filename))
            if not path.is_file() or sha(path) != expected:
                failures.append(name + ': ' + filename)
            checked += 1
    for filename, expected in record['repository_environment_files_sha256'].items():
        path = ROOT / filename
        if not path.is_file() or sha(path) != expected:
            failures.append(filename)
    print(json.dumps({'passed': not failures, 'critical_package_files_checked': checked,
                      'failures': failures, 'paid_calls': 0, 'model_outputs_read': False}))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
