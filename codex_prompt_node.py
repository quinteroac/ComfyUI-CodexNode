import json
import os
import re
import shutil
import uuid
from pathlib import Path

import numpy as np
from PIL import Image


DEFAULT_MODELS = [
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5",
]
NO_SKILL = "(none)"


def project_root():
    return Path(__file__).resolve().parent


def skills_root():
    return project_root() / ".agents" / "skills"


def list_skills():
    root = skills_root()
    if not root.is_dir():
        return []
    return sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file() and re.fullmatch(r"[A-Za-z0-9._-]+", path.name)
    )


def list_models(codex_bin="", working_dir=""):
    """Ask the installed Python SDK for its model catalog when supported."""
    try:
        from codex_app_server import AppServerConfig, Codex

        binary = codex_bin.strip() or shutil.which("codex")
        if not binary:
            return DEFAULT_MODELS
        cwd = Path(working_dir).expanduser().resolve() if working_dir.strip() else project_root()
        config = AppServerConfig(codex_bin=binary, cwd=str(cwd))
        with Codex(config=config) as codex:
            method = getattr(codex, "model_list", None) or getattr(codex, "list_models", None)
            if not method:
                return DEFAULT_MODELS

            result = []
            cursor = None
            for _ in range(20):
                try:
                    response = method(cursor=cursor) if cursor else method()
                except TypeError:
                    response = method({"cursor": cursor}) if cursor else method({})

                if isinstance(response, dict):
                    values = response.get("data", response.get("models", []))
                    next_cursor = response.get("nextCursor", response.get("next_cursor"))
                else:
                    values = getattr(response, "data", None) or getattr(response, "models", [])
                    next_cursor = getattr(response, "nextCursor", None) or getattr(response, "next_cursor", None)

                for value in values or []:
                    if isinstance(value, dict):
                        model_id = value.get("model") or value.get("id")
                    else:
                        model_id = getattr(value, "model", None) or getattr(value, "id", None)
                    if model_id:
                        result.append(str(model_id))
                if not next_cursor or next_cursor == cursor:
                    break
                cursor = next_cursor

        # Keep the catalog usable when an older SDK cannot expose model/list.
        return sorted(set(result).union(DEFAULT_MODELS))
    except Exception:
        return DEFAULT_MODELS


class CodexGeneratePromptNode:
    CATEGORY = "OpenAI/CodexNode"
    FUNCTION = "generate"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)

    @classmethod
    def INPUT_TYPES(cls):
        skills = [NO_SKILL] + list_skills()
        return {
            "required": {
                "prompt": ("STRING", {"default": "Describe the image as a prompt for a text encoder.", "multiline": True}),
            },
            "optional": {
                "skill": (skills, {"default": NO_SKILL}),
                "model": (DEFAULT_MODELS, {"default": DEFAULT_MODELS[0]}),
                "effort": (["medium", "low", "high", "xhigh"], {"default": "medium"}),
                "image": ("IMAGE",),
                "working_dir": ("STRING", {"default": "", "multiline": False}),
                "output_dir": ("STRING", {"default": "", "multiline": False}),
                "codex_bin": ("STRING", {"default": "", "multiline": False}),
            },
        }

    def generate(
        self, prompt, skill=NO_SKILL, model=DEFAULT_MODELS[0], effort="medium", image=None,
        working_dir="", output_dir="", codex_bin="",
    ):
        if not str(prompt).strip():
            raise RuntimeError("The prompt widget cannot be empty.")

        output_root = self._resolve_output_dir(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        cwd = Path(working_dir).expanduser().resolve() if working_dir.strip() else output_root
        if not cwd.is_dir():
            raise RuntimeError(f"Codex working_dir does not exist: {cwd}")

        reference_paths = self._save_batch(image, output_root)
        skill_text = self._load_skill(skill)
        request = self._build_prompt(prompt, skill, skill_text, reference_paths)
        response = self._run_codex(request, reference_paths, model, effort, cwd, codex_bin)
        return (self._extract_prompt(response),)

    @staticmethod
    def _resolve_output_dir(output_dir):
        if str(output_dir).strip():
            return Path(output_dir).expanduser().resolve()
        try:
            import folder_paths
            return Path(folder_paths.get_output_directory()).resolve() / "codex_prompt_references"
        except Exception:
            return project_root() / "codex_prompt_references"

    @staticmethod
    def _save_batch(tensor, output_root):
        if tensor is None:
            return []
        if getattr(tensor, "ndim", None) != 4:
            raise RuntimeError("The image input must be an IMAGE tensor with shape [B,H,W,C].")
        directory = output_root / "references" / uuid.uuid4().hex
        directory.mkdir(parents=True, exist_ok=True)
        paths = []
        for index, item in enumerate(tensor.detach().cpu().numpy()):
            item = np.clip(item * 255.0, 0, 255).astype(np.uint8)
            image = Image.fromarray(item[:, :, 0], mode="L").convert("RGB") if item.shape[-1] == 1 else Image.fromarray(item[:, :, :3], mode="RGB")
            path = directory / f"reference_{index:04d}.png"
            image.save(path)
            paths.append(path.resolve())
        return paths

    @staticmethod
    def _load_skill(skill):
        if not skill or skill == NO_SKILL:
            return ""
        candidate = (skills_root() / str(skill)).resolve()
        if candidate.parent != skills_root().resolve() or not re.fullmatch(r"[A-Za-z0-9._-]+", str(skill)):
            raise RuntimeError("Invalid skill name.")
        path = candidate / "SKILL.md"
        if not path.is_file():
            raise RuntimeError(f"Skill not found: {skill}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _build_prompt(user_prompt, skill, skill_text, reference_paths):
        references = "No reference images were provided."
        if reference_paths:
            references = "Analyze all of these images together as one reference batch:\n" + "\n".join(f"- {path}" for path in reference_paths)
        skill_section = "No skill selected."
        if skill_text:
            skill_section = f"Selected skill: {skill}\n\n{skill_text}"
        return f"""You are generating a single positive prompt for a ComfyUI text encoder.

User request:
{user_prompt}

Reference images:
{references}

Skill instructions:
{skill_section}

Requirements:
- Use all reference images together when they are provided.
- Return only the final positive prompt text.
- Do not include JSON, Markdown fences, labels, explanations, negative prompts, or commentary.
- Make the result self-contained and suitable for any ComfyUI text encoder.
- Do not ask follow-up questions.

Return JSON only with this exact shape: {{"prompt": "the final prompt text"}}""".strip()

    @staticmethod
    def _run_codex(prompt, reference_paths, model, effort, cwd, codex_bin):
        try:
            from codex_app_server import AppServerConfig, Codex, LocalImageInput, TextInput
        except ImportError as exc:
            raise RuntimeError(
                "codex_app_server with LocalImageInput is not installed in the ComfyUI Python environment. "
                "Install the Codex Python SDK from requirements.txt."
            ) from exc
        binary = codex_bin.strip() or shutil.which("codex")
        if not binary:
            raise RuntimeError("Codex binary was not found. Set codex_bin to its absolute path.")
        schema = {"type": "object", "properties": {"prompt": {"type": "string", "minLength": 1}}, "required": ["prompt"], "additionalProperties": False}
        # A path written in a text prompt is only a hint to the agent.  It does
        # not make the file a multimodal model input.  Use the SDK's typed
        # LocalImageInput entries so the app-server forwards every image to
        # Codex as an actual visual attachment (the equivalent of CLI --image).
        inputs = [TextInput(prompt)]
        for path in reference_paths:
            if not path.is_file():
                raise RuntimeError(f"Reference image was not written: {path}")
            inputs.append(LocalImageInput(str(path)))
        with Codex(config=AppServerConfig(codex_bin=binary, cwd=str(cwd))) as codex:
            thread = codex.thread_start(model=model, cwd=str(cwd))
            result = thread.run(inputs if reference_paths else prompt, cwd=str(cwd), model=model, effort=effort, output_schema=schema)
        if not result.final_response:
            raise RuntimeError("Codex completed without a prompt response.")
        return result.final_response.strip()

    @staticmethod
    def _extract_prompt(response):
        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", response, re.DOTALL)
            payload = json.loads(match.group(0)) if match else None
        value = payload.get("prompt") if isinstance(payload, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"Codex response did not include a non-empty prompt: {response}")
        return value.strip()


def create_skill(name, objective, rules, model=DEFAULT_MODELS[0], effort="medium", codex_bin=""):
    slug = re.sub(r"[^a-z0-9_-]+", "-", str(name).strip().lower()).strip("-")
    if not slug or len(slug) > 64:
        raise ValueError("Skill name must produce a slug of 1-64 characters.")
    destination = (skills_root() / slug).resolve()
    if destination.parent != skills_root().resolve() or destination.exists():
        raise FileExistsError(f"Skill already exists: {slug}")
    prompt = f"""Create a reusable Codex skill for prompt generation.
Name: {name}
Objective: {objective}
Rules:
{rules}

Return only the complete SKILL.md content. Use YAML frontmatter with name and description, followed by concise instructions.""".strip()
    binary = codex_bin.strip() or shutil.which("codex")
    if not binary:
        raise RuntimeError("Codex binary was not found.")
    try:
        from codex_app_server import AppServerConfig, Codex
    except ImportError as exc:
        raise RuntimeError("codex_app_server is not installed in the ComfyUI Python environment.") from exc
    with Codex(config=AppServerConfig(codex_bin=binary, cwd=str(project_root()))) as codex:
        thread = codex.thread_start(model=model, cwd=str(project_root()))
        result = thread.run(prompt, cwd=str(project_root()), model=model, effort=effort)
    content = (result.final_response or "").strip()
    if not content:
        raise RuntimeError("Codex returned an empty skill.")
    if content.startswith("```"):
        content = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", content, flags=re.IGNORECASE | re.DOTALL).strip()
    frontmatter = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, flags=re.DOTALL)
    if not frontmatter or not re.search(r"^name:\s*\S+", frontmatter.group(1), flags=re.MULTILINE) or not re.search(r"^description:\s*\S+", frontmatter.group(1), flags=re.MULTILINE):
        raise RuntimeError("Codex did not return SKILL.md content with name and description frontmatter.")
    destination.mkdir(parents=True)
    temporary = destination / f".SKILL.md.{uuid.uuid4().hex}.tmp"
    temporary.write_text(content + "\n", encoding="utf-8")
    temporary.replace(destination / "SKILL.md")
    return slug
