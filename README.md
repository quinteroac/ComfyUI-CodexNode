# ComfyUI CodexNode

Custom ComfyUI node that controls a local Codex agent from ComfyUI.

The package provides three nodes for generating text prompts, images, and
HyperFrames videos through the Codex runtime. All nodes run locally in the
same environment as ComfyUI.

## Nodes

| Node | Input | Output | Purpose |
| --- | --- | --- | --- |
| `Codex Generate Prompt` | Text and optional `IMAGE` batch | Positive `STRING` prompt | Turn a request and visual references into a text-encoder prompt |
| `Codex Generate Image` | Text and optional reference images | `IMAGE` batch, paths, response | Generate one or more images with Codex |
| `Codex Generate Video` | Text and optional reference images | `VIDEO`, paths, response | Create and render a HyperFrames composition |

## Codex Generate Prompt

`Codex Generate Prompt`

- Widget: `prompt`
- Optional input: one `IMAGE` batch, analyzed as a group
- Dynamic selectors: Codex model and one skill from `.agents/skills`
- Output: one plain positive `STRING` prompt ready for any ComfyUI text encoder
- The `Create skill` button opens a ComfyUI dialog and creates a new `SKILL.md` without queueing a workflow
- When an image is connected, it is saved as PNG and attached to Codex as an actual visual input (`LocalImageInput`), not only mentioned as a file path.

The node also exposes `effort`, `working_dir`, `output_dir`, and `codex_bin`
widgets. The model and skill lists are loaded dynamically when the node is
created. Skills are read from `.agents/skills/<skill-name>/SKILL.md`.

To create a skill from ComfyUI, click `Create skill`, enter its name,
objective, and rules, then select the generated skill in the node. Newly
created skills are written to the local `.agents/skills` directory.

The prompt node returns only the positive prompt, so it can be connected
directly to a text encoder. When an image batch is provided, every image is
sent to Codex as a visual reference and analyzed together.

## Codex Generate Image

`Codex Generate Image`

- Widget: `prompt`
- Optional inputs: `image`, `image_2`, `image_3`, `image_4`
- Output: `IMAGE` batch
- Output: `image_paths`
- Output: `codex_response`

The node starts Codex through the experimental Python SDK, asks it to generate one image file in non-interactive mode, parses the final JSON response, loads the returned file path, and returns it as a ComfyUI `IMAGE`.

If image inputs are connected, the node saves them under `codex_reference_inputs` and passes their file paths to Codex as reference/edit source images. Batched ComfyUI image tensors are expanded into multiple reference files.

The number of output images is determined by the prompt. If the user asks for an animation, sequence, storyboard, or frames, Codex should generate multiple ordered images; otherwise it should generate one image. The node loads every returned path as one ComfyUI image batch.

The default model settings are `gpt-5.5` with reasoning effort `medium`.

The `width` and `height` widgets support `gpt-image-2` popular dimensions:

- `1024x1024`
- `1536x1024`
- `1024x1536`
- `2048x2048`
- `2048x1152`
- `3840x2160`
- `2160x3840`
- `auto`

The node validates the selected pair against `gpt-image-2` constraints before calling Codex.

## Codex Generate Video

- Widget: `prompt`
- Optional inputs: `image`, `image_2`, `image_3`, `image_4`
- Output: `VIDEO`
- Output: `video_path`
- Output: `project_dir`
- Output: `codex_response`

The video node starts Codex through the same SDK path, asks it to create a HyperFrames project, optionally uses the image generation skill for raster assets, renders the composition, validates the returned file path, and returns it as a ComfyUI `VIDEO`.

The default target is a 6 second, 1920x1080, 30 FPS MP4 rendered at HyperFrames `standard` quality. The `width`, `height`, `duration_seconds`, `fps`, `format`, and `quality` widgets are passed to Codex as render requirements.

If image inputs are connected, the node saves them under `codex_reference_inputs` and passes their file paths to Codex as reference/edit source images for the video project.

## HyperFrames

The `Codex Generate Video` node uses HyperFrames for HTML-based video composition and rendering:

https://github.com/heygen-com/hyperframes

HyperFrames is licensed under the Apache License, Version 2.0.

## Usage and Safety

This node is intended for local ComfyUI workflows where the person running ComfyUI also controls the local Codex authentication/runtime.

Do not expose this node as a public or shared service that runs against your personal Codex session. If multiple people use this node, each user should authenticate and run Codex with their own authorized account or workspace controls.

Codex can read files and run commands in the selected working directory. Use a trusted working directory, review generated files before reuse, and avoid passing private or sensitive data unless you are comfortable sharing it with the configured Codex/OpenAI service.

Prompts and generated outputs must comply with OpenAI's terms and usage policies:

- https://openai.com/policies/terms-of-use/
- https://openai.com/policies/usage-policies/

Do not use this node to bypass Codex limits, safeguards, or approval flows.

## Setup

Install the Codex Python SDK in the same Python environment used by ComfyUI:

```bash
python -m pip install -r requirements.txt
```

The requirement installs the Python SDK from the `sdk/python` subdirectory of the open-source Codex repo. The official docs also support installing from a local Codex checkout:

```bash
cd sdk/python
python -m pip install -e .
```

Use the `python` executable from the same environment that starts ComfyUI. For example, this may be a virtualenv, Conda environment, or the embedded Python bundled with a portable ComfyUI install.

The node does not require `OPENAI_API_KEY`. It uses your local Codex authentication/runtime.

The node will try to find `codex` from `PATH` automatically. If ComfyUI starts with a different `PATH`, set the node's `codex_bin` widget to the absolute path of your local `codex` executable.
