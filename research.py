"""research.py - STUDENT IMPLEMENTS.  The main script.   Guide: GUIDE.md, part 3.

Usage:  python research.py "survey about world model"
Result: reports/<slug>.md   reports/<slug>.sources.json   reports/<slug>.meta.json
"""
import json  # noqa: F401
import os  # noqa: F401
import re  # noqa: F401
import sys
import time  # noqa: F401
from collections import Counter  # noqa: F401
from pathlib import Path

from agents import FINALIZER_PATH, REPORT_PATH, SOURCES_PATH, VALIDATOR_PATH, WORKDIR, build_lead_agent  # noqa: F401
from model import make_model  # noqa: F401
from sandbox import download, open_sandbox, upload  # noqa: F401

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"
VALIDATOR_SOURCE = ROOT / "check_citations.py"
FINALIZER_SOURCE = ROOT / "finalize_citations.py"   # provided: uploaded next to your validator


def slugify(topic):
    """Turn a topic into a safe file name: lower case, runs of non-word characters become one "-", max 60 chars,
    never empty (fall back to "topic"). The topic is user input: "../../x" must not escape reports/."""
    if not topic or not str(topic).strip():
        return "topic"
    s = str(topic).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    s = s[:60].rstrip("-")
    return s or "topic"


def build_prompt(topic):
    """The user message sent to the lead agent."""
    return (
        f"Conduct an in-depth, rigorous research survey on the following topic:\n\n"
        f"Topic: {topic}\n\n"
        f"Follow your complete operating workflow: plan with write_todos, split into at least 3-4 independent sub-questions, "
        f"delegate each sub-question to the 'researcher' subagent via the 'task' tool (at least 3 calls), "
        f"ensure coverage across at least 3 source families (arxiv, hf-daily, hf-search, web), merge findings into "
        f"{SOURCES_PATH}, write the comprehensive survey report body into {REPORT_PATH}, "
        f"run {FINALIZER_PATH}, validate with {VALIDATOR_PATH} until OK, "
        f"and spot-check citations with citation-checker."
    )


def summarize(messages, elapsed, model_name):
    """Return {"model", "elapsed_s", "subagent_calls", "tool_calls": {name: count}, "tokens": {"input", "output"}}."""
    tool_counts = Counter()
    total_input_tokens = 0
    total_output_tokens = 0

    for msg in messages:
        # Check tool_calls on message object or dict
        tcalls = getattr(msg, "tool_calls", None)
        if tcalls is None and isinstance(msg, dict):
            tcalls = msg.get("tool_calls")
        if tcalls:
            for tc in tcalls:
                tname = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if tname:
                    tool_counts[tname] += 1

        # Check usage_metadata
        usage = getattr(msg, "usage_metadata", None)
        if usage is None and isinstance(msg, dict):
            usage = msg.get("usage_metadata")
        if usage and isinstance(usage, dict):
            in_t = usage.get("input_tokens") or usage.get("prompt_tokens") or usage.get("input") or 0
            out_t = usage.get("output_tokens") or usage.get("completion_tokens") or usage.get("output") or 0
            total_input_tokens += int(in_t)
            total_output_tokens += int(out_t)

    subagent_calls = tool_counts.get("task", 0)

    return {
        "model": str(model_name),
        "elapsed_s": round(float(elapsed), 1),
        "subagent_calls": subagent_calls,
        "tool_calls": dict(tool_counts),
        "tokens": {
            "input": total_input_tokens,
            "output": total_output_tokens,
        },
    }


def save_outputs(backend, topic, messages, elapsed, model_name, reports_dir=REPORTS):
    """Download the report from the sandbox and write the three files into reports_dir. Return the report path."""
    files = download(backend, [REPORT_PATH, SOURCES_PATH])
    report_bytes = files.get(REPORT_PATH)
    sources_bytes = files.get(SOURCES_PATH)

    if not report_bytes or not report_bytes.strip():
        raise RuntimeError("Report file is missing or empty")
    if not sources_bytes or not sources_bytes.strip():
        raise RuntimeError("sources.json is missing or empty")

    try:
        sources_data = json.loads(sources_bytes.decode("utf-8"))
        if not isinstance(sources_data, list):
            raise ValueError("sources.json must be a JSON array")
    except Exception as exc:
        raise RuntimeError(f"sources.json is invalid JSON: {exc}") from exc

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(topic)
    meta = summarize(messages, elapsed, model_name)
    meta["topic"] = topic
    meta["n_sources"] = len(sources_data)
    meta["source_families"] = sorted(list({
        s.get("source") for s in sources_data if isinstance(s, dict) and s.get("source")
    }))

    md_path = reports_dir / f"{slug}.md"
    sources_path = reports_dir / f"{slug}.sources.json"
    meta_path = reports_dir / f"{slug}.meta.json"

    md_path.write_text(report_bytes.decode("utf-8"), encoding="utf-8")
    sources_path.write_text(json.dumps(sources_data, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return md_path


def main(topic):
    """Return the process exit code (0 ok, 1 failed run, 2 no topic)."""
    topic = str(topic or "").strip()
    if not topic:
        print("Usage: python research.py '<topic>'", file=sys.stderr)
        return 2

    model = make_model()
    model_name = getattr(model, "model_name", None) or getattr(model, "model", None) or os.getenv("LAB_MODEL", "unknown")
    start = time.monotonic()

    with open_sandbox() as backend:
        backend.execute(f"mkdir -p {WORKDIR}/research/notes {WORKDIR}/report")
        upload(backend, {
            VALIDATOR_PATH: VALIDATOR_SOURCE.read_bytes(),
            FINALIZER_PATH: FINALIZER_SOURCE.read_bytes(),
        })
        agent = build_lead_agent(backend, model)
        result = agent.invoke(
            {"messages": [{"role": "user", "content": build_prompt(topic)}]},
            config={"recursion_limit": 1000},
        )
        elapsed = time.monotonic() - start
        messages = result.get("messages", []) if isinstance(result, dict) else getattr(result, "messages", [])

        try:
            report_path = save_outputs(backend, topic, messages, elapsed, model_name)
            print(f"SUCCESS: Report saved to {report_path}")
            return 0
        except RuntimeError as exc:
            print(f"FAILED: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main(" ".join(sys.argv[1:])))
