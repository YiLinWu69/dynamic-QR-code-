# -*- coding: utf-8 -*-
"""
產生「動態失效 QRCode」現場簽到網頁（公開主機版）。

這個版本只負責「產生 checkin.html」這個檔案，
不會啟動本機網頁伺服器，因為將把 checkin.html
上傳到 GitHub Pages / Netlify 等公開主機上。

執行方式：
    python generate_qrcode_html_public.py

執行後會：
    在這支程式所在的資料夾產生 checkin.html

⚠️ 產生後的步驟：
    1. 把 checkin.html 上傳到 GitHub Pages（或 Netlify 等公開主機）
    2. 之後每次上課，投影幕電腦只要打開上傳後拿到的公開網址即可
       （例如 https://你的帳號.github.io/你的repo/checkin.html）
       不要用 file:///... 打開，否則 QRCode 裡編碼的會是本機路徑，
       手機掃了打不開。
    3. 不需要每次上課都重新執行這支程式或重新上傳，
       除非要更改 GOOGLE_FORM_URL 或倒數秒數等設定。
"""

import os

GOOGLE_FORM_URL = "https://forms.gle/1196RADJTEFjV4Zf7"

# HTML 檔案會產生在這支程式所在的資料夾
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "checkin.html")

PAGE_HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>現場簽到 · 動態 QRCode</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
  :root{
    --bg: #0b0d0f; --panel: #14171a; --line: #232830;
    --accent: #4ee1a0; --text: #e8ecef; --muted: #7d8791; --danger:#ff6b6b;
  }
  *{ box-sizing:border-box; }
  body{
    margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
    background:var(--bg); font-family:'Courier New', ui-monospace, monospace; color:var(--text);
    padding:24px;
  }
  .panel{
    background:var(--panel); border:1px solid var(--line); border-radius:4px;
    padding:32px 36px; width:360px; text-align:center;
  }
  .eyebrow{
    letter-spacing:.2em; font-size:11px; color:var(--accent);
    text-transform:uppercase; margin-bottom:16px;
  }
  #qrcode{
    display:flex; justify-content:center; margin:0 auto 18px; padding:12px;
    background:#fff; width:fit-content; border-radius:2px;
  }
  .countdown-wrap{
    height:3px; background:var(--line); border-radius:2px; overflow:hidden; margin-bottom:18px;
  }
  .countdown-bar{ height:100%; width:100%; background:var(--accent); transform-origin:left; }
  .hint{ font-size:12px; color:var(--muted); margin-bottom:20px; }
  .settings{
    display:flex; align-items:center; justify-content:center; gap:10px;
    border-top:1px solid var(--line); padding-top:16px; font-size:12px; color:var(--muted);
  }
  .settings input{
    width:56px; background:var(--bg); border:1px solid var(--line); color:var(--text);
    font-family:inherit; font-size:13px; text-align:center; border-radius:3px; padding:4px 2px;
  }
  .settings input:focus{ outline:1px solid var(--accent); }
  h1{ color:var(--danger); font-size:20px; margin:0 0 12px; }
  p{ color:var(--muted); font-size:14px; line-height:1.6; margin:0; }
</style>
</head>
<body>

<div class="panel" id="panel"></div>

<script>
const GOOGLE_FORM_URL = "__GOOGLE_FORM_URL__";
const panel = document.getElementById("panel");
const params = new URLSearchParams(window.location.search);
const baseUrl = window.location.origin + window.location.pathname;

function currentSlot(intervalSec){
  return Math.floor(Date.now() / 1000 / intervalSec);
}

if (params.has("t") && params.has("i")) {
  // ---------- 手機掃碼進來的簽到頁 ----------
  const i = parseFloat(params.get("i"));
  const scanned = parseInt(params.get("t"), 10);
  const nowSlot = currentSlot(i);

  // 有效條件：掃到的是「目前這一組」或「前一組」。
  // 多給前一輪的緩衝，避免使用者剛好在 QR 切換的瞬間掃到就被判失效。
  // 若想更嚴格（只有目前這一組有效），把「|| scanned === nowSlot - 1」拿掉即可。
  const valid = i > 0 && !isNaN(scanned) && (scanned === nowSlot || scanned === nowSlot - 1);

  if (valid) {
    panel.innerHTML = `<div class="eyebrow">簽到中...</div><p>驗證成功，正在跳轉到表單</p>`;
    window.location.replace(GOOGLE_FORM_URL);
  } else {
    panel.innerHTML = `
      <h1>此連結已失效</h1>
      <p>這個 QRCode 已經被新的一輪取代了。<br>請重新掃描投影幕上「目前」顯示的 QRCode。</p>
    `;
  }

} else {
  // ---------- 投影幕顯示頁 ----------
  panel.innerHTML = `
    <div class="eyebrow">現場簽到 · Live Check-in</div>
    <div id="qrcode"></div>
    <div class="countdown-wrap"><div class="countdown-bar" id="bar"></div></div>
    <div class="hint">掃描此碼即可簽到，過期會自動換下一組</div>
    <div class="settings">
      每 <input type="number" id="intervalInput" min="2" max="600" step="1"> 秒換一次
    </div>
  `;

  const bar = document.getElementById("bar");
  const input = document.getElementById("intervalInput");
  const qrBox = document.getElementById("qrcode");

  let intervalSec = parseInt(localStorage.getItem("checkinInterval") || "5", 10);
  input.value = intervalSec;

  let qrcode = null;
  let lastSlot = null;

  function renderQR(){
    const slot = currentSlot(intervalSec);
    const url = `${baseUrl}?t=${slot}&i=${intervalSec}`;
    if (!qrcode) {
      qrcode = new QRCode(qrBox, {
        text: url, width: 260, height: 260,
        colorDark: "#0b0d0f", colorLight: "#ffffff",
      });
    } else {
      qrcode.clear();
      qrcode.makeCode(url);
    }
    lastSlot = slot;

    const elapsedMs = (Date.now() / 1000 - slot * intervalSec) * 1000;
    const remainingMs = Math.max(0, intervalSec * 1000 - elapsedMs);
    bar.style.transition = "none";
    bar.style.transform = "scaleX(1)";
    void bar.offsetWidth;
    bar.style.transition = `transform ${remainingMs}ms linear`;
    bar.style.transform = "scaleX(0)";
  }

  function tick(){
    const slot = currentSlot(intervalSec);
    if (slot !== lastSlot) renderQR();
  }

  renderQR();
  setInterval(tick, 500);

  input.addEventListener("change", () => {
    let v = parseInt(input.value, 10);
    if (isNaN(v) || v < 2) v = 2;
    if (v > 600) v = 600;
    input.value = v;
    intervalSec = v;
    localStorage.setItem("checkinInterval", String(v));
    lastSlot = null;
    renderQR();
  });
}
</script>

</body>
</html>
""".replace("__GOOGLE_FORM_URL__", GOOGLE_FORM_URL)


def main():
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(PAGE_HTML)

    print("已產生 checkin.html！")
    print(f"檔案位置：{OUTPUT_PATH}")
    print()
    print("接下來把這個檔案上傳到公開主機（例如 GitHub Pages）")
    print()
    print("上傳完成、拿到公開網址後，之後每次上課只要打開")
    print("那個網址即可，不需要再重新執行這支程式。")


if __name__ == "__main__":
    main()
