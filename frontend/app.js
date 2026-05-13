const $ = (id) => document.getElementById(id);

function readMaxDocuments() {
  const raw = $("maxDocs").value.trim();
  if (raw === "") return null;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) ? n : 20;
}

function getMode() {
  const el = document.querySelector('input[name="mode"]:checked');
  return el ? el.value : "abstract";
}

function setStatus(message, variant) {
  const el = $("status");
  el.textContent = message;
  el.classList.remove("success", "error");
  if (variant) el.classList.add(variant);
}

async function runGeneration() {
  const rawBase = $("apiBase").value.trim();
  const base = rawBase.replace(/\/$/, "");
  const mode = getMode();
  const testset_size = parseInt($("testsetSize").value, 10) || 5;
  const max_documents = readMaxDocuments();
  const data_dir_raw = $("dataDir").value.trim();
  const data_dir = data_dir_raw === "" ? null : data_dir_raw;

  const body = {
    mode,
    testset_size,
    max_documents,
    data_dir,
  };

  const btn = $("runBtn");
  setStatus("Executing RAGAS pipeline… This may take several minutes.", null);
  btn.disabled = true;
  btn.classList.add("loading");
  $("metaOut").textContent = "{}";
  $("tableWrap").innerHTML = "";

  try {
    const url = base === "" ? "/api/generate" : `${base}/api/generate`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(text.slice(0, 500));
    }
    if (!res.ok) {
      const detail = data.detail ?? data;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }

    const n = data.examples?.length ?? 0;
    setStatus(`Run completed · ${n} synthetic test row${n === 1 ? "" : "s"} returned.`, "success");
    $("metaOut").textContent = JSON.stringify(data.metadata ?? {}, null, 2);

    const examples = data.examples ?? [];
    if (examples.length === 0) {
      $("tableWrap").innerHTML = '<p class="empty-state">No synthetic test rows were returned.</p>';
      return;
    }
    const cols = Object.keys(examples[0]);
    const esc = (s) =>
      String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    let html = "<table><thead><tr>";
    for (const c of cols) html += `<th>${esc(c)}</th>`;
    html += "</tr></thead><tbody>";
    for (const row of examples) {
      html += "<tr>";
      for (const c of cols) {
        const v = row[c];
        const cell =
          v === null || v === undefined
            ? ""
            : typeof v === "object"
              ? JSON.stringify(v)
              : String(v);
        html += `<td>${esc(cell)}</td>`;
      }
      html += "</tr>";
    }
    html += "</tbody></table>";
    $("tableWrap").innerHTML = html;
  } catch (e) {
    setStatus(e.message || String(e), "error");
  } finally {
    btn.disabled = false;
    btn.classList.remove("loading");
  }
}

$("runBtn").addEventListener("click", runGeneration);
