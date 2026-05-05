from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .models import AgentSkillSpec, SkillSource, utc_now


class SkillsMixin:
    """GitHub skill registry import and management."""

    def add_skill_source(self, url: str, name: str | None = None, branch: str = "main") -> SkillSource:

        self._require_settings()

        owner, repo = self._parse_github_repo_url(url)

        source_name = name.strip() if name and name.strip() else f"{owner}/{repo}"

        existing = next((item for item in self.storage.list_skill_sources() if item.url == url), None)

        source = existing or SkillSource(name=source_name, url=url, branch=branch or "main")

        source.name = source_name

        source.branch = self._validate_branch(branch or source.branch or "main")

        source.status = "enabled"

        source.updated_at = utc_now()

        self.storage.save_skill_source(source)

        return source





    def import_skill_source(self, source_id: str) -> dict[str, Any]:

        self._require_settings()

        source = next((item for item in self.storage.list_skill_sources() if item.id == source_id), None)

        if source is None:

            raise KeyError(source_id)

        owner, repo = self._parse_github_repo_url(source.url)

        branch = self._validate_branch(source.branch or "main")

        tree = self._fetch_github_tree(owner, repo, branch)

        if tree is None and branch == "main":

            branch = "master"

            tree = self._fetch_github_tree(owner, repo, branch)

        if tree is None:

            raise RuntimeError("Could not read GitHub repository tree.")

        imported = 0

        skipped = 0

        for item in tree[:120]:

            path = str(item.get("path") or "")

            if not self._skill_candidate_path(path):

                skipped += 1

                continue

            text = self._fetch_text(

                self._raw_github_url(owner, repo, branch, path),

                timeout=12,

            )

            if not text or len(text.strip()) < 80:

                skipped += 1

                continue

            skill = self._normalize_external_skill(source, path, text)

            self.storage.save_agent_skill(skill)

            imported += 1

        source.branch = branch

        source.imported_skill_count = len(self.storage.list_agent_skills(source_id=source.id))

        source.last_imported_at = utc_now()

        source.updated_at = utc_now()

        source.trust_status = "imported_requires_review"

        source.notes = f"Imported {imported} skill candidate(s), skipped {skipped} file(s)."

        self.storage.save_skill_source(source)

        return {"source": source, "imported": imported, "skipped": skipped}





    def _parse_github_repo_url(self, url: str) -> tuple[str, str]:

        parsed = urlparse(url.strip())

        if parsed.netloc.lower() != "github.com":

            raise ValueError("Skill source must be a github.com repository URL.")

        parts = [part for part in parsed.path.strip("/").split("/") if part]

        if len(parts) < 2:

            raise ValueError("GitHub repository URL must include owner and repo.")

        owner, repo = parts[0], parts[1].removesuffix(".git")

        if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo):

            raise ValueError("GitHub repository owner or name contains unsupported characters.")

        return owner, repo





    def _validate_branch(self, branch: str) -> str:

        normalized = branch.strip()

        if not normalized:

            return "main"

        if len(normalized) > 120:

            raise ValueError("GitHub branch name is too long.")

        if normalized.startswith(("-", ".", "/")) or normalized.endswith((".", "/")):

            raise ValueError("GitHub branch name is not supported.")

        if ".." in normalized or "@{" in normalized or "\\" in normalized:

            raise ValueError("GitHub branch name is not supported.")

        if not re.fullmatch(r"[A-Za-z0-9._/-]+", normalized):

            raise ValueError("GitHub branch name contains unsupported characters.")

        return normalized





    def _raw_github_url(self, owner: str, repo: str, branch: str, path: str) -> str:

        safe_path = "/".join(quote(part, safe="") for part in path.split("/") if part)

        return (

            "https://raw.githubusercontent.com/"

            f"{quote(owner, safe='')}/{quote(repo, safe='')}/{quote(branch, safe='')}/{safe_path}"

        )





    def _fetch_github_tree(self, owner: str, repo: str, branch: str) -> list[dict[str, Any]] | None:

        url = (

            "https://api.github.com/repos/"

            f"{quote(owner, safe='')}/{quote(repo, safe='')}/git/trees/{quote(branch, safe='')}?recursive=1"

        )

        try:

            payload = json.loads(self._fetch_text(url, timeout=15))

        except RuntimeError:

            return None

        tree = payload.get("tree") if isinstance(payload, dict) else None

        if not isinstance(tree, list):

            return None

        return [item for item in tree if item.get("type") == "blob"]





    def _fetch_text(self, url: str, timeout: int = 15) -> str:

        req = Request(url, headers={"User-Agent": "Praetor-Skill-Importer/1.0"})

        try:

            with urlopen(req, timeout=timeout) as response:

                raw = response.read(512_000)

        except (HTTPError, URLError, TimeoutError) as exc:

            raise RuntimeError(f"Could not fetch skill source: {exc}") from exc

        return raw.decode("utf-8", errors="replace")





    def _skill_candidate_path(self, path: str) -> bool:

        lowered = path.lower()

        if not lowered.endswith((".md", ".markdown", ".yaml", ".yml", ".json")):

            return False

        name = Path(path).name.lower()

        if name in {"readme.md", "license.md", "contributing.md", "changelog.md"}:

            return False

        return True





    def _normalize_external_skill(self, source: SkillSource, path: str, text: str) -> AgentSkillSpec:

        title = self._extract_skill_title(path, text)

        lowered = text.lower()

        domains = self._infer_skill_domains(path, lowered)

        bullets = self._extract_bullets(text)

        risk_flags = self._infer_skill_risks(lowered)

        return AgentSkillSpec(

            source_id=source.id,

            source_url=source.url,

            source_path=path,

            name=title,

            description=self._extract_description(text),

            domains=domains,

            suitable_for=[domain for domain in domains[:4]],

            responsibilities=bullets[:8],

            tools=[],

            constraints=[

                "Must stay within Praetor workspace and permission policy.",

                "Must not transmit sensitive data or take external action without approval.",

            ],

            escalation_triggers=[

                "privacy, security, legal, financial, or external communication risk",

                "unclear authority or conflict with standing orders",

            ],

            output_contract=["owner-readable summary", "decisions needed", "changed artifacts or recommendations"],

            risk_flags=risk_flags,

            safety_notes=[

                "Imported from external repository as an untrusted capability summary.",

                "Original prompt text is not used as authority without Praetor governance.",

            ],

            status="imported_requires_review",

        )





    def _extract_skill_title(self, path: str, text: str) -> str:

        for line in text.splitlines()[:40]:

            stripped = line.strip()

            if stripped.startswith("#"):

                return stripped.lstrip("#").strip()[:96] or Path(path).stem.replace("-", " ").title()

            if stripped.lower().startswith(("name:", "title:")):

                return stripped.split(":", 1)[1].strip().strip("\"'")[:96]

        return Path(path).stem.replace("-", " ").replace("_", " ").title()





    def _extract_description(self, text: str) -> str | None:

        for line in text.splitlines():

            stripped = line.strip()

            if not stripped or stripped.startswith(("#", "-", "*", "```", "---")):

                continue

            if ":" in stripped and len(stripped.split(":", 1)[0]) < 24:

                continue

            return stripped[:280]

        return None





    def _extract_bullets(self, text: str) -> list[str]:

        bullets: list[str] = []

        for line in text.splitlines():

            stripped = line.strip()

            if stripped.startswith(("- ", "* ")):

                value = stripped[2:].strip()

                if 8 <= len(value) <= 180:

                    bullets.append(value)

            if len(bullets) >= 12:

                break

        return bullets





    def _infer_skill_domains(self, path: str, lowered_text: str) -> list[str]:

        haystack = f"{path.lower()} {lowered_text[:4000]}"

        domain_terms = {

            "legal": ["legal", "contract", "license", "policy", "compliance"],

            "engineering": ["engineer", "developer", "code", "software", "debug", "test"],

            "product": ["product", "roadmap", "feature", "user story", "prioritization"],

            "marketing": ["marketing", "growth", "seo", "campaign", "messaging"],

            "sales": ["sales", "customer", "lead", "qualification", "business development"],

            "design": ["design", "ux", "ui", "visual", "interface"],

            "finance": ["finance", "pricing", "revenue", "forecast", "budget"],

            "operations": ["operations", "project manager", "coordination", "support"],

            "security": ["security", "privacy", "threat", "risk", "credential"],

        }

        matches = [domain for domain, terms in domain_terms.items() if any(term in haystack for term in terms)]

        return matches[:5] or ["operations"]





    def _infer_skill_risks(self, lowered_text: str) -> list[str]:

        risks = []

        terms = {

            "external_communication": ["send email", "contact customer", "post", "publish", "outreach"],

            "financial": ["payment", "invoice", "budget", "pricing", "revenue", "bank"],

            "legal": ["contract", "legal", "liability", "license", "compliance"],

            "privacy": ["personal data", "credential", "secret", "token", "private"],

            "destructive": ["delete", "remove files", "drop database", "overwrite"],

        }

        for risk, keywords in terms.items():

            if any(keyword in lowered_text for keyword in keywords):

                risks.append(risk)

        return risks



