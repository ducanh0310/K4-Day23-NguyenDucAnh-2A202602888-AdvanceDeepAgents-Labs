"""check_citations.py - STUDENT IMPLEMENTS `check`.   Runs INSIDE the sandbox (standard library only).

research.py uploads this file to the sandbox and the lead agent runs it with the `execute` tool:
    python3 /tmp/work/research/check_citations.py [report.md] [sources.json]
It must exit 0 and print "OK: ..." when the report is consistent, else print each problem and exit 1.
"""
import json
import re
import sys

REPORT = "/tmp/work/report/report.md"
SOURCES = "/tmp/work/research/sources.json"

_GROUP = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\](?!\()")   # [3]  [1, 2]  [1-3]; not [3](link)
_CODE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
_REF_HEADING = re.compile(r"(?m)^##[ \t]+References[ \t]*$")
_URL_REGEX = re.compile(r"https?://[^\s)\]]+")


def _group_numbers(group):
    numbers = []
    for part in re.split(r"\s*,\s*", group):
        span = re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", part)
        if span:
            a, b = int(span.group(1)), int(span.group(2))
            numbers.extend(range(a, b + 1) if 0 <= b - a <= 200 else [a, b])
        else:
            numbers.append(int(part))
    return numbers


def check(report_text, sources):
    """Return a list of problem strings (empty list = OK)."""
    problems = []
    if not isinstance(sources, list) or len(sources) == 0:
        return ["no sources in sources.json"]

    source_dict = {}
    seen_urls = set()

    for idx, s in enumerate(sources):
        if not isinstance(s, dict):
            problems.append(f"source item at index {idx} is not an object")
            continue
        n = s.get("n")
        if not isinstance(n, int):
            problems.append(f"source n={n!r} must be an integer")
        elif n in source_dict:
            problems.append(f"source [{n}] appears multiple times in sources.json")
        else:
            source_dict[n] = s

        url = s.get("url")
        if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
            problems.append(f"source n={n!r} has invalid url={url!r} (must start with http:// or https://)")
        else:
            if url in seen_urls:
                problems.append(f"duplicate url in sources.json: {url}")
            seen_urls.add(url)

    matches = list(_REF_HEADING.finditer(report_text))
    if not matches:
        problems.append("missing heading '## References'")
        return problems

    body = report_text[:matches[-1].start()]
    ref_section = report_text[matches[-1].end():]

    # Find cited numbers in BODY only (excluding code blocks and markdown links)
    cited = set()
    segments = _CODE.split(body)
    for i, segment in enumerate(segments):
        if i % 2 == 1:
            continue  # inside code block or inline code
        for match in _GROUP.finditer(segment):
            for num in _group_numbers(match.group(1)):
                cited.add(num)

    source_ns = set(source_dict.keys())
    for num in sorted(cited):
        if num not in source_ns:
            problems.append(f"[{num}] cited in body but missing from sources.json")

    for num in sorted(source_ns):
        if num not in cited:
            problems.append(f"source [{num}] never cited in report body")

    # Check References section lines
    ref_lines_by_n = {}
    ref_lines_count = 0
    for line in ref_section.splitlines():
        line_str = line.strip()
        if not line_str:
            continue
        m = re.match(r"^\[(\d+)\]\s*(.*)$", line_str)
        if m:
            ref_lines_count += 1
            num = int(m.group(1))
            ref_lines_by_n.setdefault(num, []).append((line_str, m.group(2)))
        else:
            problems.append(f"unexpected line in References section: {line_str[:60]}")

    for num in sorted(source_ns):
        entries = ref_lines_by_n.get(num, [])
        if len(entries) == 0:
            problems.append(f"missing reference line for source [{num}]")
        elif len(entries) > 1:
            problems.append(f"duplicate reference line for [{num}] (found {len(entries)})")
        else:
            full_line, rest = entries[0]
            # Check exactly ONE URL
            urls = _URL_REGEX.findall(full_line)
            if len(urls) != 1:
                problems.append(f"reference line [{num}] must hold exactly one URL (found {len(urls)})")
            else:
                expected_url = source_dict[num].get("url")
                if urls[0] != expected_url:
                    problems.append(f"reference line [{num}] URL {urls[0]!r} does not match sources.json {expected_url!r}")

    for num in sorted(ref_lines_by_n.keys()):
        if num not in source_ns:
            problems.append(f"reference line [{num}] is not a source in sources.json")

    return problems


def main(argv):
    report_path = argv[1] if len(argv) > 1 else REPORT
    sources_path = argv[2] if len(argv) > 2 else SOURCES
    try:
        with open(report_path, encoding="utf-8") as f:
            report = f.read()
        with open(sources_path, encoding="utf-8") as f:
            sources = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"cannot read inputs: {exc}")
        return 1
    problems = check(report, sources)
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {len(sources)} sources, all citations resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
