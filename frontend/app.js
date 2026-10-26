"use strict";

const MAX_FILE_SIZE_MB = 10;
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const TITLES = { visual: "Sua Receita", illiterate: "💊" };

const $ = (id) => document.getElementById(id);
const els = {
  form: $("translate-form"),
  dropzone: $("dropzone"),
  dropzoneText: $("dropzone-text"),
  fileInput: $("file-input"),
  textInput: $("text-input"),
  panelFile: $("panel-file"),
  panelText: $("panel-text"),
  translateBtn: $("translate-btn"),
  error: $("error"),
  downloadError: $("download-error"),
  upload: $("upload-section"),
  loading: $("loading-section"),
  resultSection: $("result-section"),
  result: $("result"),
  newBtn: $("new-btn"),
};

// input: "file" (enviar arquivo) ou "text" (digitar receita) — aba ativa.
const state = { input: "file", file: null, mode: null, text: null };

// ---------- Abas: arquivo | texto ----------

const tabs = [...document.querySelectorAll(".tab")];

function selectTab(tab) {
  state.input = tab.dataset.input;
  tabs.forEach((t) => {
    const active = t === tab;
    t.setAttribute("aria-selected", String(active));
    t.tabIndex = active ? 0 : -1;
  });
  els.panelFile.hidden = state.input !== "file";
  els.panelText.hidden = state.input !== "text";
  hideError(els.error);
  updateTranslateButton();
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => selectTab(tab));
  tab.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    const next = tabs[(tabs.indexOf(tab) + 1) % tabs.length];
    selectTab(next);
    next.focus();
  });
});

els.textInput.addEventListener("input", updateTranslateButton);

// ---------- Seleção de arquivo ----------

function setFile(file) {
  hideError(els.error);
  if (!file) return;

  const name = file.name.toLowerCase();
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return rejectFile("Formato não suportado. Envie um arquivo PDF, Word (.docx) ou TXT.");
  }
  if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
    return rejectFile(`O arquivo é maior que ${MAX_FILE_SIZE_MB} MB. Envie um arquivo menor.`);
  }

  state.file = file;
  els.dropzone.classList.add("has-file");
  els.dropzoneText.textContent = `✅ ${file.name}`;
  updateTranslateButton();
}

function rejectFile(message) {
  state.file = null;
  els.fileInput.value = "";
  els.dropzone.classList.remove("has-file");
  els.dropzoneText.innerHTML = "Arraste a receita aqui ou <strong>clique para selecionar</strong>";
  showError(els.error, message);
  updateTranslateButton();
}

els.fileInput.addEventListener("change", () => setFile(els.fileInput.files[0]));

els.dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    els.fileInput.click();
  }
});

["dragenter", "dragover"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.remove("dragover");
  })
);
els.dropzone.addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));

// ---------- Seleção de modo ----------

document.querySelectorAll(".mode-btn").forEach((btn) =>
  btn.addEventListener("click", () => {
    state.mode = btn.dataset.mode;
    document
      .querySelectorAll(".mode-btn")
      .forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
    updateTranslateButton();
  })
);

function hasInput() {
  return state.input === "file" ? Boolean(state.file) : Boolean(els.textInput.value.trim());
}

function updateTranslateButton() {
  els.translateBtn.disabled = !(hasInput() && state.mode);
}

// ---------- Tradução ----------

els.form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!hasInput() || !state.mode) return;

  hideError(els.error);
  show("loading");

  const body = new FormData();
  if (state.input === "file") body.append("file", state.file);
  else body.append("text", els.textInput.value);
  body.append("mode", state.mode);

  try {
    const res = await fetch("/api/translate", { method: "POST", body });
    if (!res.ok) throw new Error(await errorMessage(res));
    const data = await res.json();
    state.text = data.translated_text;
    renderResult(data.translated_text, data.mode);
    show("result");
  } catch (err) {
    show("upload");
    showError(els.error, friendly(err));
  }
});

// Divide em blocos separados por linha em branco (mesma regra de exporter.split_blocks).
function splitBlocks(text) {
  return text
    .trim()
    .split(/\n\s*\n/)
    .map((block) => block.split("\n").map((l) => l.trim()).filter(Boolean))
    .filter((lines) => lines.length);
}

// ---------- Banco de imagens (Noto Emoji) ----------
// catalog.json é gerado por backend/fetch_emoji.py a partir de backend/symbols.py.

const VS16 = /️/g;
let symbolCatalog = {};
let symbolPattern = null;

fetch("emoji/catalog.json")
  .then((res) => (res.ok ? res.json() : {}))
  .then((catalog) => {
    symbolCatalog = catalog;
    const keys = Object.keys(catalog).sort((a, b) => b.length - a.length);
    const escaped = keys.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    symbolPattern = keys.length ? new RegExp(escaped.join("|"), "gu") : null;
  })
  .catch(() => {
    /* sem catálogo: os emojis aparecem como texto */
  });

// Troca cada símbolo do catálogo pela imagem (mesma regra de exporter.symbols_html).
function appendSymbols(el, text) {
  text = text.replace(VS16, "");
  if (!symbolPattern) {
    el.append(text);
    return;
  }
  let pos = 0;
  for (const match of text.matchAll(symbolPattern)) {
    if (match.index > pos) el.append(text.slice(pos, match.index));
    const info = symbolCatalog[match[0]];
    const img = document.createElement("img");
    // Ícones do Health Icons têm margem interna: são exibidos maiores (classe "hi").
    img.className = info.file.startsWith("hi_") ? "emoji hi" : "emoji";
    img.src = `emoji/${info.file}`;
    img.alt = info.alt;
    el.append(img);
    pos = match.index + match[0].length;
  }
  if (pos < text.length) el.append(text.slice(pos));
}

// Modo analfabetismo: "☀️ 💊 | 1 comprimido de manhã" -> [símbolos, legenda]
// (mesma regra de exporter.split_line).
function splitLine(line) {
  const i = line.indexOf("|");
  return i === -1 ? [line.trim(), ""] : [line.slice(0, i).trim(), line.slice(i + 1).trim()];
}

function renderResult(text, mode) {
  els.result.className = `result result-${mode}`;
  els.result.replaceChildren();

  const title = document.createElement("h2");
  if (mode === "visual") title.textContent = TITLES[mode];
  else appendSymbols(title, TITLES[mode]);
  els.result.append(title);

  for (const lines of splitBlocks(text)) {
    if (mode === "visual") {
      const p = document.createElement("p");
      lines.forEach((line, i) => {
        if (i) p.append(document.createElement("br"));
        p.append(line);
      });
      els.result.append(p);
    } else {
      const card = document.createElement("div");
      card.className = "card";
      lines.forEach((line, i) => {
        const [symbols, caption] = splitLine(line);
        const div = document.createElement("div");
        div.className = i === 0 ? "line card-title" : "line";
        const sym = document.createElement("span");
        sym.className = "symbols";
        appendSymbols(sym, symbols);
        const cap = document.createElement("span");
        cap.className = "caption";
        cap.textContent = caption;
        div.append(sym, cap);
        card.append(div);
      });
      els.result.append(card);
    }
  }
}

// ---------- Download ----------

document.querySelectorAll(".download-btn").forEach((btn) =>
  btn.addEventListener("click", async () => {
    hideError(els.downloadError);
    btn.disabled = true;
    try {
      const res = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: state.text, mode: state.mode, format: btn.dataset.format }),
      });
      if (!res.ok) throw new Error(await errorMessage(res));
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `receita.${btn.dataset.format}`;
      document.body.append(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      showError(els.downloadError, friendly(err));
    } finally {
      btn.disabled = false;
    }
  })
);

// ---------- Nova receita ----------

els.newBtn.addEventListener("click", () => {
  state.text = null;
  els.textInput.value = "";
  rejectFile("");
  hideError(els.error);
  hideError(els.downloadError);
  els.result.replaceChildren();
  show("upload");
});

// ---------- Utilidades ----------

function show(section) {
  els.upload.hidden = section !== "upload";
  els.loading.hidden = section !== "loading";
  els.resultSection.hidden = section !== "result";
}

function showError(el, message) {
  el.textContent = message;
  el.hidden = !message;
}

function hideError(el) {
  el.textContent = "";
  el.hidden = true;
}

async function errorMessage(res) {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
  } catch (_) {
    /* resposta sem JSON */
  }
  return "Ocorreu um erro ao processar a receita. Tente novamente.";
}

function friendly(err) {
  if (err instanceof TypeError) {
    return "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.";
  }
  return err.message;
}
