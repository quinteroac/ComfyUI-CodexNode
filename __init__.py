from .codex_image_node import CodexGenerateImageNode
from .codex_video_node import CodexGenerateVideoNode

NODE_CLASS_MAPPINGS = {
    "CodexGenerateImageNode": CodexGenerateImageNode,
    "CodexGenerateVideoNode": CodexGenerateVideoNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CodexGenerateImageNode": "Codex Generate Image",
    "CodexGenerateVideoNode": "Codex Generate Video",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
