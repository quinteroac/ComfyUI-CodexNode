import json
import os
import re
import shutil
import uuid
from pathlib import Path

import numpy as np
from PIL import Image


SUPPORTED_VIDEO_WIDTHS = ["1920", "1080", "1280", "720", "2048", "2160", "3840"]
SUPPORTED_VIDEO_HEIGHTS = ["1080", "1920", "720", "1280", "2048", "2160", "3840"]
SUPPORTED_VIDEO_FORMATS = ["mp4", "webm"]
SUPPORTED_VIDEO_QUALITIES = ["standard", "draft", "high"]


class CodexGenerateVideoNode:
    CATEGORY = "OpenAI/CodexNode"
    FUNCTION = "generate"
    RETURN_TYPES = ("VIDEO", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("video", "video_path", "project_dir", "codex_response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {
                        "default": "Generate a short HyperFrames MP4 video.",
                        "multiline": True,
                    },
                ),
            },
            "optional": {
                "model": (
                    [
                        "gpt-5.5",
                        "gpt-5.4",
                        "gpt-5",
                        "gpt-5.4-mini",
                    ],
                    {"default": "gpt-5.5"},
                ),
                "effort": (
                    [
                        "medium",
                        "low",
                        "high",
                        "xhigh",
                    ],
                    {"default": "medium"},
                ),
                "width": (SUPPORTED_VIDEO_WIDTHS, {"default": "1920"}),
                "height": (SUPPORTED_VIDEO_HEIGHTS, {"default": "1080"}),
                "duration_seconds": (
                    "FLOAT",
                    {"default": 6.0, "min": 0.5, "max": 300.0, "step": 0.5},
                ),
                "fps": ("INT", {"default": 30, "min": 1, "max": 60, "step": 1}),
                "format": (SUPPORTED_VIDEO_FORMATS, {"default": "mp4"}),
                "quality": (SUPPORTED_VIDEO_QUALITIES, {"default": "standard"}),
                "image": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
                "output_dir": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                    },
                ),
                "working_dir": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                    },
                ),
                "codex_bin": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                    },
                ),
            },
        }

    def generate(
        self,
        prompt,
        model="gpt-5.5",
        effort="medium",
        width="1920",
        height="1080",
        duration_seconds=6.0,
        fps=30,
        format="mp4",
        quality="standard",
        image=None,
        image_2=None,
        image_3=None,
        image_4=None,
        output_dir="",
        working_dir="",
        codex_bin="",
    ):
        output_root = self._resolve_output_dir(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)

        cwd = Path(working_dir).expanduser().resolve() if working_dir.strip() else output_root
        if not cwd.exists():
            raise RuntimeError(f"Codex working_dir does not exist: {cwd}")

        reference_paths = self._save_reference_images(
            [image, image_2, image_3, image_4],
            output_root,
        )
        final_prompt = self._build_prompt(
            user_prompt=prompt,
            output_root=output_root,
            width=int(width),
            height=int(height),
            duration_seconds=float(duration_seconds),
            fps=int(fps),
            video_format=format,
            quality=quality,
            reference_paths=reference_paths,
        )
        codex_response = self._run_codex(final_prompt, model, effort, cwd, codex_bin)
        video_path, project_dir = self._extract_video_result(codex_response, output_root, cwd)
        video = self._load_video(video_path)
        return (video, str(video_path), str(project_dir), codex_response)

    @staticmethod
    def _resolve_output_dir(output_dir):
        if output_dir.strip():
            return Path(output_dir).expanduser().resolve()

        try:
            import folder_paths

            return Path(folder_paths.get_output_directory()).resolve() / "codex_generated_videos"
        except Exception:
            return Path.cwd().resolve() / "codex_generated_videos"

    @staticmethod
    def _save_reference_images(images, output_root):
        reference_dir = output_root / "codex_reference_inputs"
        saved_paths = []

        for slot_index, tensor in enumerate(images, start=1):
            if tensor is None:
                continue
            if tensor.ndim != 4:
                raise RuntimeError(
                    f"Reference image input {slot_index} must be an IMAGE tensor with shape [B,H,W,C]."
                )

            reference_dir.mkdir(parents=True, exist_ok=True)
            batch = tensor.detach().cpu().numpy()
            for batch_index, item in enumerate(batch):
                item = np.clip(item * 255.0, 0, 255).astype(np.uint8)
                if item.shape[-1] == 1:
                    pil_image = Image.fromarray(item[:, :, 0], mode="L").convert("RGB")
                else:
                    pil_image = Image.fromarray(item[:, :, :3], mode="RGB")

                filename = f"reference_{uuid.uuid4().hex}_input{slot_index}_{batch_index}.png"
                path = reference_dir / filename
                pil_image.save(path)
                saved_paths.append(path.resolve())

        return saved_paths

    @staticmethod
    def _build_prompt(
        user_prompt,
        output_root,
        width,
        height,
        duration_seconds,
        fps,
        video_format,
        quality,
        reference_paths,
    ):
        references_instruction = "No reference images were provided."
        if reference_paths:
            references = "\n".join(f"- {path}" for path in reference_paths)
            references_instruction = f"""
Use these input image files as visual references, edit sources, or source assets according to the task:
{references}
""".strip()

        return f"""
You are running from a ComfyUI node in non-interactive mode.

Task:
{user_prompt}

Video target:
- Canvas: {width}x{height}
- Duration: {duration_seconds:g} seconds
- FPS: {fps}
- Format: {video_format}
- HyperFrames render quality: {quality}

Input images:
{references_instruction}

Generate one finished video file and save it under this directory:
{output_root}

Requirements:
- Do not ask follow-up questions.
- Do not wait for interactive input.
- Use the local HyperFrames skills/workflow to create an HTML video composition.
- Use the image generation skill when raster assets, illustrated scenes, textures, backgrounds, or image edits are useful for the video.
- Prefer `npx hyperframes init --non-interactive`, then author the composition, run `npx hyperframes lint`, run `npx hyperframes inspect`, and render with `npx hyperframes render`.
- Render with `--fps {fps}`, `--quality {quality}`, `--format {video_format}`, and `--output` pointing to a file under the requested output directory.
- If reference images are provided, load them from the listed file paths and copy any project-bound assets into the HyperFrames project.
- The final video file must be an existing .{video_format} file.
- Also keep the HyperFrames project directory on disk for inspection or later edits.
- The final response must be valid JSON only, with this exact shape:
{{"video_path": "/absolute/path/to/generated-video.{video_format}", "project_dir": "/absolute/path/to/hyperframes-project"}}
""".strip()

    @staticmethod
    def _run_codex(prompt, model, effort, cwd, codex_bin):
        try:
            from codex_app_server import AppServerConfig, Codex
        except ImportError as exc:
            raise RuntimeError(
                "codex_app_server is not installed in the ComfyUI Python environment. "
                "Install the Codex Python SDK, for example from the Codex repo's "
                "sdk/python directory, before using this node."
            ) from exc

        resolved_codex_bin = codex_bin.strip() or shutil.which("codex")
        if not resolved_codex_bin:
            raise RuntimeError(
                "Codex binary was not found. Set the node's codex_bin widget to the absolute "
                "path of your local codex executable."
            )

        config = AppServerConfig(codex_bin=resolved_codex_bin, cwd=str(cwd))

        output_schema = {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
                "project_dir": {"type": "string"},
            },
            "required": ["video_path", "project_dir"],
            "additionalProperties": False,
        }

        with Codex(config=config) as codex:
            thread = codex.thread_start(model=model, cwd=str(cwd))
            result = thread.run(
                prompt,
                cwd=str(cwd),
                model=model,
                effort=effort,
                output_schema=output_schema,
            )

        if not result.final_response:
            raise RuntimeError("Codex completed without a final response containing video_path.")
        return result.final_response.strip()

    @staticmethod
    def _extract_video_result(codex_response, output_root, cwd):
        payload = None
        try:
            payload = json.loads(codex_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", codex_response, re.DOTALL)
            if match:
                payload = json.loads(match.group(0))

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Codex response did not include a JSON object with video_path. "
                f"Response was: {codex_response}"
            )

        raw_video_path = payload.get("video_path")
        if not raw_video_path:
            raise RuntimeError(
                "Codex response did not include a non-empty video_path. "
                f"Response was: {codex_response}"
            )

        video_path = CodexGenerateVideoNode._resolve_returned_file(raw_video_path, output_root, cwd)
        if video_path.suffix.lower() not in {".mp4", ".webm", ".mov", ".mkv"}:
            raise RuntimeError(f"Codex returned a path that does not look like a video file: {video_path}")

        raw_project_dir = payload.get("project_dir") or video_path.parent
        project_dir = CodexGenerateVideoNode._resolve_returned_dir(raw_project_dir, output_root, cwd)
        return video_path, project_dir

    @staticmethod
    def _resolve_returned_file(raw_value, output_root, cwd):
        raw_path = Path(os.path.expanduser(str(raw_value)))
        candidates = [raw_path]
        if not raw_path.is_absolute():
            candidates = [output_root / raw_path, cwd / raw_path]

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.is_file():
                return resolved

        raise RuntimeError(f"Codex returned video_path, but the file was not found: {raw_path}")

    @staticmethod
    def _resolve_returned_dir(raw_value, output_root, cwd):
        raw_path = Path(os.path.expanduser(str(raw_value)))
        candidates = [raw_path]
        if not raw_path.is_absolute():
            candidates = [output_root / raw_path, cwd / raw_path]

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.is_dir():
                return resolved

        raise RuntimeError(f"Codex returned project_dir, but the directory was not found: {raw_path}")

    @staticmethod
    def _load_video(path):
        try:
            from comfy_api.latest import InputImpl
        except ImportError as exc:
            raise RuntimeError(
                "comfy_api.latest is required to return a ComfyUI VIDEO output."
            ) from exc

        return InputImpl.VideoFromFile(str(path))
