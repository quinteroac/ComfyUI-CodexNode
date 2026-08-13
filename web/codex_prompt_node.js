import { app } from "/scripts/app.js";

const base = "/codex-node/prompt";

async function json(path, options) {
    const response = await fetch(`${base}${path}`, { cache: "no-store", ...options });
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
    return value;
}

function updateCombo(node, name, values, fallback) {
    const widget = node.widgets?.find((item) => item.name === name);
    if (!widget || !values.length) return;
    widget.options.values = values;
    if (!values.includes(widget.value)) widget.value = fallback || values[0];
}

function field(label, type = "text") {
    const wrapper = document.createElement("label");
    wrapper.textContent = label;
    const input = document.createElement(type === "textarea" ? "textarea" : "input");
    if (type !== "textarea") input.type = type;
    input.style.width = "100%";
    input.style.boxSizing = "border-box";
    wrapper.appendChild(input);
    return { wrapper, input };
}

function openSkillDialog(node) {
    const dialog = new app.ui.dialog.constructor();
    dialog.element.classList.add("comfy-settings");
    const container = document.createElement("div");
    container.style.display = "grid";
    container.style.gap = "8px";
    const name = field("Name");
    const objective = field("Objective");
    const rules = field("Rules", "textarea");
    rules.input.rows = 7;
    const status = document.createElement("div");
    status.style.minHeight = "1.4em";
    status.style.color = "#9ca3af";
    container.append(name.wrapper, objective.wrapper, rules.wrapper, status);
    const close = dialog.element.querySelector("button");
    close.textContent = "CANCEL";
    const save = document.createElement("button");
    save.textContent = "CREATE SKILL";
    save.onclick = async () => {
        if (!name.input.value.trim() || !objective.input.value.trim() || !rules.input.value.trim()) {
            alert("Name, objective, and rules are required.");
            return;
        }
        save.disabled = true;
        close.disabled = true;
        status.textContent = "Generating skill with Codex… This may take a moment.";
        status.style.color = "#60a5fa";
        try {
            const selectedModel = node.widgets?.find((widget) => widget.name === "model")?.value || "gpt-5.6-terra";
            await json("/skills/create", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: name.input.value, objective: objective.input.value, rules: rules.input.value, model: selectedModel }) });
            const result = await json("/skills");
            updateCombo(node, "skill", ["(none)", ...result.skills], "(none)");
            status.textContent = "Skill created successfully.";
            status.style.color = "#4ade80";
            dialog.close();
        } catch (error) {
            alert(`Could not create skill: ${error.message}`);
            save.disabled = false;
            close.disabled = false;
            status.textContent = `Error: ${error.message}`;
            status.style.color = "#f87171";
        }
    };
    close.before(save);
    // ComfyDialog.show() resets textElement, so append the editable controls after opening it.
    dialog.show("");
    dialog.textElement.append(container);
}

app.registerExtension({
    name: "CodexNode.PromptGenerator",
    async nodeCreated(node) {
        if ((node.comfyClass || node.type) !== "CodexGeneratePromptNode") return;
        if (!node.widgets?.some((widget) => widget.name === "create_skill")) {
            node.addWidget("button", "create_skill", "Create skill", () => {
                try {
                    openSkillDialog(node);
                } catch (error) {
                    console.error("Could not open Codex skill dialog", error);
                    alert(`Could not open skill dialog: ${error.message}`);
                }
            });
        }
        try {
            const [skills, models] = await Promise.all([json("/skills"), json("/models")]);
            updateCombo(node, "skill", ["(none)", ...skills.skills], "(none)");
            updateCombo(node, "model", models.models, models.models[0]);
            node.setSize([Math.max(node.size[0], 320), node.size[1]]);
        } catch (error) {
            console.warn("Codex prompt node metadata unavailable", error);
        }
    },
});
