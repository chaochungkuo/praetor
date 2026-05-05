from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import (
    get_anthropic_api_key,
    get_anthropic_base_url,
    get_openai_api_key,
    get_openai_base_url,
)
from .models import MissionDefinition, RunRecord, UsageSummary, generate_id, utc_now


class ApiProviderError(RuntimeError):
    pass


@dataclass
class ApiMissionResult:
    run_record: RunRecord


def collect_retrieval_preview(workspace_root: Path) -> tuple[list[str], dict[str, str]]:
    wiki_root = workspace_root / "Wiki"
    preview: list[str] = []
    contents: dict[str, str] = {}
    if not wiki_root.exists():
        return preview, contents
    for path in sorted(wiki_root.glob("*.md"))[:6]:
        rel = path.relative_to(workspace_root)
        text = path.read_text(encoding="utf-8")
        preview.append(str(rel))
        contents[str(rel)] = text[:6000]
    return preview, contents


def build_generation_prompt(
    *,
    mission: MissionDefinition,
    retrieval_contents: dict[str, str],
    safety_policy: str | None = None,
) -> str:
    wiki_section = "\n\n".join(
        f"## Source: {path}\n{text}" for path, text in retrieval_contents.items()
    )
    requested_outputs = "\n".join(f"- {path}" for path in mission.requested_outputs) or "- none"
    return "\n".join(
        [
            "You are Praetor, an AI company operator.",
            "Return valid JSON only.",
            "Produce a concise execution summary plus files to write.",
            "",
            "Required JSON shape:",
            '{',
            '  "summary": "short summary",',
            '  "files": [{"path": "/workspace/Projects/X/FILE.md", "content": "..."}],',
            '  "decisions": ["..."],',
            '  "notes": ["..."]',
            '}',
            "",
            f"Mission title: {mission.title}",
            f"Mission summary: {mission.summary or ''}",
            f"Mission domains: {', '.join(mission.domains) or 'none'}",
            "Requested outputs:",
            requested_outputs,
            "",
            safety_policy or "No additional safety policy supplied.",
            "",
            "Use the company memory below when relevant.",
            wiki_section or "No wiki context available.",
        ]
    )


def parse_generation_payload(payload_text: str) -> dict[str, Any]:
    text = payload_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    return json.loads(text)


def _openai_chat_completion(
    model: str,
    prompt: str,
    base_url: str | None = None,
    api_key: str | None = None,
) -> tuple[str, UsageSummary]:
    api_key = api_key or get_openai_api_key()
    if not api_key:
        raise ApiProviderError("OPENAI_API_KEY is not configured.")
    url = f"{(base_url or get_openai_base_url()).rstrip('/')}/chat/completions"
    started = time.monotonic()
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You return strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
            },
        )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage") or {}
    return content, UsageSummary(
        duration_ms=int((time.monotonic() - started) * 1000),
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        usage_available=bool(usage),
    )


def openai_audio_transcription(
    audio: bytes,
    *,
    filename: str = "praetor-voice.webm",
    content_type: str = "audio/webm",
    model: str = "gpt-4o-mini-transcribe",
    language: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    api_key = api_key or get_openai_api_key()
    if not api_key:
        raise ApiProviderError("OPENAI_API_KEY is not configured.")
    if not audio:
        raise ApiProviderError("No audio was provided.")
    data: dict[str, str] = {"model": model}
    if language:
        data["language"] = language
    with httpx.Client(timeout=90.0) as client:
        response = client.post(
            f"{(base_url or get_openai_base_url()).rstrip('/')}/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files={"file": (filename, audio, content_type)},
        )
    response.raise_for_status()
    payload = response.json()
    text = str(payload.get("text", "")).strip()
    if not text:
        raise ApiProviderError("OpenAI returned an empty transcription.")
    return text


def _anthropic_messages(
    model: str,
    prompt: str,
    base_url: str | None = None,
    api_key: str | None = None,
) -> tuple[str, UsageSummary]:
    api_key = api_key or get_anthropic_api_key()
    if not api_key:
        raise ApiProviderError("ANTHROPIC_API_KEY is not configured.")
    url = f"{(base_url or get_anthropic_base_url()).rstrip('/')}/messages"
    started = time.monotonic()
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "max_tokens": 3000,
                "system": "Return valid JSON only.",
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    response.raise_for_status()
    payload = response.json()
    content_blocks = payload.get("content") or []
    text = "\n".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
    usage = payload.get("usage") or {}
    return text, UsageSummary(
        duration_ms=int((time.monotonic() - started) * 1000),
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        usage_available=bool(usage),
    )


def generate_json_response(*, provider: str, model: str, prompt: str, base_url: str | None = None) -> tuple[str, UsageSummary]:
    if provider in {"openai", "openai_compatible"}:
        return _openai_chat_completion(model, prompt, base_url=base_url)
    if provider == "anthropic":
        return _anthropic_messages(model, prompt, base_url=base_url)
    raise ApiProviderError(f"Unsupported API provider: {provider}")


def test_provider_connection(
    *,
    provider: str,
    model: str,
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        if provider in {"openai", "openai_compatible"}:
            content, usage = _openai_chat_completion(
                model,
                "Return only this JSON object: {\"ok\": true}",
                base_url=base_url,
                api_key=api_key,
            )
        elif provider == "anthropic":
            content, usage = _anthropic_messages(
                model,
                "Return only this JSON object: {\"ok\": true}",
                base_url=base_url,
                api_key=api_key,
            )
        else:
            raise ApiProviderError(f"Unsupported API provider: {provider}")
        return {
            "ok": True,
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "duration_ms": usage.duration_ms or int((time.monotonic() - started) * 1000),
            "response_preview": content[:160],
        }
    except Exception as exc:
        raise ApiProviderError(str(exc)) from exc


def run_api_mission(
    *,
    mission: MissionDefinition,
    workspace_root: Path,
    provider: str,
    model: str,
    base_url: str | None = None,
    safety_policy: str | None = None,
) -> tuple[dict[str, Any], ApiMissionResult]:
    preview, contents = collect_retrieval_preview(workspace_root)
    prompt = build_generation_prompt(
        mission=mission,
        retrieval_contents=contents,
        safety_policy=safety_policy,
    )
    response_text, usage = generate_json_response(provider=provider, model=model, prompt=prompt, base_url=base_url)
    payload = parse_generation_payload(response_text)
    run_record = RunRecord(
        run_id=generate_id("run"),
        request_id=generate_id("req"),
        mission_id=mission.id,
        task_id=generate_id("task"),
        executor=f"{provider}:{model}",
        status="completed",
        normalized_status="completed",
        host_workdir=str(workspace_root),
        usage=usage,
        stdout_tail=payload.get("summary"),
        retrieval_preview=preview,
        finished_at=utc_now(),
    )
    return payload, ApiMissionResult(run_record=run_record)
