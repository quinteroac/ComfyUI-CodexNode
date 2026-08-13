---
name: krea-prompt
description: Generate polished Krea image prompts from text descriptions and zero or more reference images, preserving requested visual elements and enriching prompts according to Krea's prompting guidelines.
---

# Krea Prompt Generation

Use this skill whenever the user asks for a prompt intended for Krea.

Follow the Krea prompting guide: https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md

- Accept a text description, zero or more reference images, or both.
- If reference images are provided, inspect them and identify the elements the user wants to replicate, such as subject, pose, composition, camera angle, lighting, palette, materials, clothing, environment, and visual style.
- Replicate only the requested aspects of reference images. Clearly adapt or replace anything the user specifies.
- If no reference image is provided, enrich the user's description using the Krea guide.
- Write prompts in natural language. Prefer detailed, concrete descriptions over disconnected keyword lists.
- Include relevant details about the subject, action, appearance, composition, perspective, setting, lighting, color palette, texture, medium, and mood.
- Preserve the user's explicit constraints, dimensions, text, identity, and intended result.
- For text that must appear in the image, place the exact wording in quotation marks.
- Do not add unwanted objects, text, logos, artists, or styles.
- Resolve ambiguities using reasonable visual assumptions; ask a brief clarification only when the ambiguity would materially change the image.
- Return the final Krea prompt in a copy-ready code block. Add a short note only when reference-image usage or an important assumption needs explanation.
