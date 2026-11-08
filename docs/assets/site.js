(function () {
  "use strict";
  var key = "ai-study-notes:v1";
  var progress = Object.create(null);
  var cards = [];
  var renders = [];
  var knownIds = [];
  try { knownIds = JSON.parse(document.getElementById("card-ids").textContent); } catch (_) { knownIds = []; }
  var notice = document.querySelector("[data-storage-notice]");
  function showNotice(text) {
    if (!notice) return;
    notice.textContent = text;
    notice.hidden = false;
  }
  try {
    var raw = JSON.parse(localStorage.getItem(key) || "{}");
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      Object.keys(raw).forEach(function (id) {
        if (knownIds.indexOf(id) !== -1 && (raw[id] === "familiar" || raw[id] === "again")) progress[id] = raw[id];
      });
    }
  } catch (_) { showNotice("目前無法讀取儲存紀錄，本次仍可翻卡與自評。"); }
  try { cards = JSON.parse(document.getElementById("study-data").textContent); } catch (_) { cards = []; }
  function save() {
    try { localStorage.setItem(key, JSON.stringify(progress)); }
    catch (_) { showNotice("瀏覽器無法保存紀錄，本次操作仍有效。離開前可匯出自評紀錄。"); }
    updateCounts();
  }
  function updateCounts() {
    var totalNode = document.querySelector("[data-all-card-count]");
    var total = totalNode ? Number(totalNode.getAttribute("data-all-card-count")) : 0;
    var count = Math.min(total, Object.values(progress).filter(function (v) { return v === "familiar"; }).length);
    document.querySelectorAll("[data-familiar-count]").forEach(function (el) { el.textContent = String(count).padStart(2, "0"); });
  }
  updateCounts();
  var search = document.querySelector("[data-search-input]");
  if (search) search.addEventListener("input", function () {
    var term = search.value.trim().toLocaleLowerCase();
    var visible = 0;
    document.querySelectorAll("[data-topic-row]").forEach(function (row) {
      row.hidden = row.getAttribute("data-search").toLocaleLowerCase().indexOf(term) === -1;
      if (!row.hidden) visible++;
    });
    document.querySelector("[data-search-empty]").hidden = visible !== 0;
    document.querySelector("[data-search-status]").textContent = "找到 " + visible + " 個主題";
  });
  var topicFilter = document.querySelector("[data-topic-filter]");
  var onlyAgain = document.querySelector("[data-only-again]");
  document.querySelectorAll("[data-deck]").forEach(function (deck) {
    var index = 0;
    var current = [];
    var question = deck.querySelector("[data-question]");
    var topic = deck.querySelector("[data-deck-topic]");
    var counter = deck.querySelector("[data-deck-counter]");
    var answerArea = deck.querySelector("[data-answer-area]");
    var answer = deck.querySelector("[data-answer]");
    var evidence = deck.querySelector("[data-evidence]");
    var source = deck.querySelector("[data-source]");
    var reveal = deck.querySelector("[data-reveal]");
    var rating = deck.querySelector("[data-rating]");
    var previous = deck.querySelector("[data-prev]");
    var next = deck.querySelector("[data-next]");
    var state = deck.querySelector("[data-card-state]");
    var empty = deck.querySelector("[data-deck-empty]");
    var status = deck.querySelector("[data-deck-status]");
    function filtered() {
      return cards.filter(function (card) {
        return (!topicFilter || topicFilter.value === "all" || card.topic === topicFilter.value) &&
          (!onlyAgain || !onlyAgain.checked || progress[card.id] === "again");
      });
    }
    function render(focus) {
      current = filtered();
      if (index >= current.length) index = Math.max(0, current.length - 1);
      var card = current[index];
      answerArea.hidden = true; rating.hidden = true;
      deck.querySelector("details").open = false;
      reveal.setAttribute("aria-expanded", "false");
      reveal.textContent = "顯示答案 ↗";
      deck.querySelector(".question-area").hidden = !card;
      reveal.hidden = !card;
      deck.querySelector(".deck-controls").hidden = !card;
      empty.hidden = !!card;
      counter.textContent = card ? String(index + 1).padStart(2, "0") + " / " + String(current.length).padStart(2, "0") : "00 / 00";
      topic.textContent = card ? card.topic_title : "沒有符合的卡片";
      if (!card) return;
      question.textContent = card.question;
      answer.textContent = card.answer;
      evidence.textContent = card.evidence;
      source.setAttribute("href", card.source_url);
      state.textContent = progress[card.id] === "familiar" ? "已熟悉 ✓" : progress[card.id] === "again" ? "需再複習" : "尚未自評";
      previous.disabled = index === 0;
      next.disabled = index === current.length - 1;
      if (focus) question.focus({preventScroll:true});
    }
    reveal.addEventListener("click", function () {
      var shown = answerArea.hidden;
      answerArea.hidden = !shown; rating.hidden = !shown;
      reveal.setAttribute("aria-expanded", shown ? "true" : "false");
      reveal.textContent = shown ? "收起答案 ↑" : "顯示答案 ↗";
    });
    previous.addEventListener("click", function () { if (index > 0) index--; render(true); });
    next.addEventListener("click", function () { if (index < current.length - 1) index++; render(true); });
    deck.querySelectorAll("[data-rate]").forEach(function (button) {
      button.addEventListener("click", function () {
        if (answerArea.hidden || !current[index]) return;
        var card = current[index];
        progress[card.id] = button.getAttribute("data-rate");
        save();
        status.textContent = "已將這張卡標記為" + (progress[card.id] === "again" ? "需再複習" : "已熟悉");
        if (!onlyAgain || !onlyAgain.checked) index = Math.min(index + 1, current.length - 1);
        render(true);
      });
    });
    function restart() { index = 0; render(false); }
    if (topicFilter) topicFilter.addEventListener("change", restart);
    if (onlyAgain) onlyAgain.addEventListener("change", restart);
    renders.push(restart);
    render(false);
  });
  var reset = document.querySelector("[data-reset-progress]");
  var dialog = document.querySelector("[data-reset-dialog]");
  if (reset && dialog) {
    reset.addEventListener("click", function () { dialog.showModal(); });
    dialog.addEventListener("close", function () {
      if (dialog.returnValue !== "confirm") return;
      progress = Object.create(null); save(); renders.forEach(function (r) { r(); });
      showNotice("已重設這個瀏覽器的複習進度。");
    });
  }
  var exportButton = document.querySelector("[data-export-progress]");
  if (exportButton) exportButton.addEventListener("click", function () {
    var payload = {version:1, exported_at:new Date().toISOString(), progress:progress};
    var blob = new Blob([JSON.stringify(payload, null, 2)], {type:"application/json;charset=utf-8"});
    var url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = "ai-study-progress.json"; document.body.appendChild(link); link.click(); link.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    showNotice("自評紀錄已匯出為 JSON 檔案。");
  });
})();
