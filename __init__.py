from .codex_image_node import CodexGenerateImageNode
from .codex_prompt_node import CodexGeneratePromptNode
from .codex_video_node import CodexGenerateVideoNode

try:
    from aiohttp import web
    from server import PromptServer

    from .codex_prompt_node import create_skill, list_models, list_skills

    @PromptServer.instance.routes.get("/codex-node/prompt/skills")
    async def codex_prompt_skills(request):
        return web.json_response({"skills": list_skills()})

    @PromptServer.instance.routes.get("/codex-node/prompt/models")
    async def codex_prompt_models(request):
        return web.json_response({"models": list_models()})

    @PromptServer.instance.routes.post("/codex-node/prompt/skills/create")
    async def codex_prompt_create_skill(request):
        payload = await request.json()
        required = ("name", "objective", "rules")
        missing = [key for key in required if not str(payload.get(key, "")).strip()]
        if missing:
            return web.json_response({"error": f"Missing fields: {', '.join(missing)}"}, status=400)
        try:
            slug = await __import__("asyncio").to_thread(
                create_skill,
                payload["name"],
                payload["objective"],
                payload["rules"],
                payload.get("model") or "gpt-5.6-terra",
                payload.get("effort", "medium"),
                payload.get("codex_bin", ""),
            )
            return web.json_response({"skill": slug})
        except FileExistsError as exc:
            return web.json_response({"error": str(exc)}, status=409)
        except Exception as exc:
            return web.json_response({"error": str(exc)}, status=500)
except Exception:
    # Importing the node must remain possible in tooling that does not run ComfyUI.
    pass

NODE_CLASS_MAPPINGS = {
    "CodexGenerateImageNode": CodexGenerateImageNode,
    "CodexGeneratePromptNode": CodexGeneratePromptNode,
    "CodexGenerateVideoNode": CodexGenerateVideoNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CodexGenerateImageNode": "Codex Generate Image",
    "CodexGeneratePromptNode": "Codex Generate Prompt",
    "CodexGenerateVideoNode": "Codex Generate Video",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
