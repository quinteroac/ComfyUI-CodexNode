import json
import os
import re
import shutil
import uuid
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps


AUTO_SIZE = "auto"
SUPPORTED_WIDTHS = [AUTO_SIZE, "1024", "1536", "2048", "2160", "3840"]
SUPPORTED_HEIGHTS = [AUTO_SIZE, "1024", "1152", "1536", "2048", "2160", "3840"]


class CodexGenerateImageNode:
    CATEGORY = "OpenAI/CodexNode"
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "image_paths", "codex_response")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {
                        "default": "Generate a single PNG image.",
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
                "width": (SUPPORTED_WIDTHS, {"default": AUTO_SIZE}),
                "height": (SUPPORTED_HEIGHTS, {"default": AUTO_SIZE}),
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
        width=AUTO_SIZE,
        height=AUTO_SIZE,
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

        size = self._resolve_size(width, height)
        reference_paths = self._save_reference_images(
            [image, image_2, image_3, image_4],
            output_root,
        )
        final_prompt = self._build_prompt(prompt, output_root, size, reference_paths)
        codex_response = self._run_codex(final_prompt, model, effort, cwd, codex_bin)
        image_paths = self._extract_image_paths(codex_response, output_root, cwd)
        images = self._load_images(image_paths)
        image_paths_json = json.dumps([str(path) for path in image_paths], indent=2)
        return (images, image_paths_json, codex_response)

    @staticmethod
    def _resolve_output_dir(output_dir):
        if output_dir.strip():
            return Path(output_dir).expanduser().resolve()

        try:
            import folder_paths

            return Path(folder_paths.get_output_directory()).resolve() / "codex_generated"
        except Exception:
            return Path.cwd().resolve() / "codex_generated"

    @staticmethod
    def _resolve_size(width, height):
        if width == AUTO_SIZE and height == AUTO_SIZE:
            return AUTO_SIZE
        if width == AUTO_SIZE or height == AUTO_SIZE:
            raise RuntimeError("Set both width and height, or leave both as auto.")

        width_int = int(width)
        height_int = int(height)
        max_edge = max(width_int, height_int)
        min_edge = min(width_int, height_int)
        total_pixels = width_int * height_int

        if max_edge > 3840:
            raise RuntimeError("gpt-image-2 size is invalid: maximum edge must be <= 3840px.")
        if width_int % 16 != 0 or height_int % 16 != 0:
            raise RuntimeError("gpt-image-2 size is invalid: width and height must be multiples of 16px.")
        if max_edge / min_edge > 3:
            raise RuntimeError("gpt-image-2 size is invalid: long edge to short edge ratio must be <= 3:1.")
        if total_pixels < 655360 or total_pixels > 8294400:
            raise RuntimeError(
                "gpt-image-2 size is invalid: total pixels must be between 655,360 and 8,294,400."
            )

        return f"{width_int}x{height_int}"

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
    def _build_prompt(user_prompt, output_root, size, reference_paths):
        size_instruction = (
            "Let the image model choose the output size automatically."
            if size == AUTO_SIZE
            else f"Generate the image at exactly {size} pixels."
        )
        api_size_instruction = (
            'If you use gpt-image-2 or an image generation tool, use size="auto".'
            if size == AUTO_SIZE
            else f'If you use gpt-image-2 or an image generation tool, pass size="{size}".'
        )
        references_instruction = "No reference images were provided."
        if reference_paths:
            references = "\n".join(f"- {path}" for path in reference_paths)
            references_instruction = f"""
Use these input image files as references or edit sources, according to the task:
{references}
""".strip()

        return f"""
You are running from a ComfyUI node in non-interactive mode.

Task:
{user_prompt}

Size:
{size_instruction}

Input images:
{references_instruction}

Generate the number of image files needed to satisfy the user request and save them under this directory:
{output_root}

Requirements:
- Do not ask follow-up questions.
- Do not wait for interactive input.
- {api_size_instruction}
- If reference images are provided, load them from the listed file paths.
- Decide how many images to create from the user's prompt. If the user asks for an animation, sequence, storyboard, or frames, create multiple ordered images. Otherwise create one image.
- Create PNG, JPG, JPEG, or WEBP image files.
- If generating frames for an animation, return them in playback order.
- Every generated image must have the same pixel dimensions so ComfyUI can load them as one batch.
- The final response must be valid JSON only, with this exact shape:
{{"image_paths": ["/absolute/path/to/generated-image-or-frame.png"]}}
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
                "image_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
            },
            "required": ["image_paths"],
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
            raise RuntimeError("Codex completed without a final response containing image_paths.")
        return result.final_response.strip()

    @staticmethod
    def _extract_image_paths(codex_response, output_root, cwd):
        payload = None
        try:
            payload = json.loads(codex_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", codex_response, re.DOTALL)
            if match:
                payload = json.loads(match.group(0))

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Codex response did not include a JSON object with image_paths. "
                f"Response was: {codex_response}"
            )

        raw_paths = payload.get("image_paths")
        if raw_paths is None and payload.get("image_path"):
            raw_paths = [payload["image_path"]]
        if not isinstance(raw_paths, list) or not raw_paths:
            raise RuntimeError(
                "Codex response did not include a non-empty JSON image_paths list. "
                f"Response was: {codex_response}"
            )

        resolved_paths = []
        for raw_value in raw_paths:
            resolved_paths.append(CodexGenerateImageNode._resolve_returned_path(raw_value, output_root, cwd))
        return resolved_paths

    @staticmethod
    def _resolve_returned_path(raw_value, output_root, cwd):
        raw_path = Path(os.path.expanduser(str(raw_value)))
        candidates = [raw_path]
        if not raw_path.is_absolute():
            candidates = [output_root / raw_path, cwd / raw_path]

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.is_file():
                return resolved

        raise RuntimeError(f"Codex returned image_path, but the file was not found: {raw_path}")

    @staticmethod
    def _load_images(paths):
        tensors = []
        expected_size = None
        for path in paths:
            image = Image.open(path)
            image = ImageOps.exif_transpose(image).convert("RGB")
            if expected_size is None:
                expected_size = image.size
            elif image.size != expected_size:
                raise RuntimeError(
                    "Codex generated images with different sizes. "
                    f"Expected {expected_size}, got {image.size} for {path}."
                )

            array = np.asarray(image).astype(np.float32) / 255.0
            tensors.append(torch.from_numpy(array).unsqueeze(0))

        return torch.cat(tensors, dim=0)
