/* Providence Community Church website assistant — drop-in chat widget.
 * Embed with:  <script src="/chat-widget.js" defer></script>
 * No dependencies, no cookies, no localStorage. Session id lives in memory only.
 * The Anthropic key never touches the browser — this only calls the edge function.
 */
(function () {
  "use strict";
  if (window.__pccBotLoaded) return;
  window.__pccBotLoaded = true;

  var API = "https://twbunmbzyqcqzgffdrib.supabase.co/functions/v1/chat";
  var CONTACT = "info@kcprovidence.org";
  var sessionId = (crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + Math.random();
  var messages = [];         // running conversation, in memory only
  var opened = false, busy = false;

  var css = ""
    + ".pccbot,.pccbot *{box-sizing:border-box}"
    + ".pccbot{position:fixed;bottom:20px;right:20px;z-index:2147483000;"
    + "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}"
    + ".pccbot-btn{width:60px;height:60px;border-radius:50%;border:none;cursor:pointer;"
    + "background:#075c2e;color:#fff;box-shadow:0 6px 20px rgba(0,0,0,.22);display:flex;"
    + "align-items:center;justify-content:center;transition:transform .15s ease}"
    + ".pccbot-btn:hover{transform:scale(1.05)}"
    + ".pccbot-btn svg{width:28px;height:28px}"
    + ".pccbot-panel{position:absolute;bottom:74px;right:0;width:370px;max-width:calc(100vw - 32px);"
    + "height:540px;max-height:calc(100vh - 120px);background:#fff;border-radius:16px;"
    + "box-shadow:0 12px 40px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden}"
    + ".pccbot-panel.open{display:flex}"
    + ".pccbot-head{background:#075c2e;color:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px}"
    + ".pccbot-head h3{margin:0;font-size:15px;font-weight:600;line-height:1.2}"
    + ".pccbot-head .sub{font-size:11px;opacity:.85;font-weight:500;letter-spacing:.03em}"
    + ".pccbot-head .x{margin-left:auto;background:none;border:none;color:#fff;cursor:pointer;"
    + "font-size:22px;line-height:1;padding:2px 6px;border-radius:6px}"
    + ".pccbot-head .x:hover{background:rgba(255,255,255,.15)}"
    + ".pccbot-log{flex:1;overflow-y:auto;padding:16px;background:#f7f6f2;display:flex;flex-direction:column;gap:10px}"
    + ".pccbot-msg{max-width:85%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.5;white-space:normal;word-wrap:break-word}"
    + ".pccbot-msg.bot{background:#fff;color:#1c1c1a;border:1px solid #e6e3db;align-self:flex-start;border-bottom-left-radius:4px}"
    + ".pccbot-msg.me{background:#075c2e;color:#fff;align-self:flex-end;border-bottom-right-radius:4px}"
    + ".pccbot-msg a{color:inherit;text-decoration:underline}"
    + ".pccbot-msg.bot a{color:#075c2e}"
    + ".pccbot-typing{align-self:flex-start;display:flex;gap:4px;padding:12px 14px;background:#fff;border:1px solid #e6e3db;border-radius:14px}"
    + ".pccbot-typing span{width:7px;height:7px;border-radius:50%;background:#b8b4a8;animation:pccblink 1.2s infinite}"
    + ".pccbot-typing span:nth-child(2){animation-delay:.2s}.pccbot-typing span:nth-child(3){animation-delay:.4s}"
    + "@keyframes pccblink{0%,60%,100%{opacity:.3}30%{opacity:1}}"
    + ".pccbot-foot{border-top:1px solid #eee;padding:10px;background:#fff}"
    + ".pccbot-row{display:flex;gap:8px;align-items:flex-end}"
    + ".pccbot-row textarea{flex:1;resize:none;border:1px solid #d8d5cd;border-radius:10px;padding:9px 11px;"
    + "font:inherit;font-size:14px;max-height:100px;outline:none}"
    + ".pccbot-row textarea:focus{border-color:#075c2e}"
    + ".pccbot-send{background:#075c2e;border:none;color:#fff;width:38px;height:38px;border-radius:10px;cursor:pointer;flex:none}"
    + ".pccbot-send:disabled{opacity:.5;cursor:default}"
    + ".pccbot-note{font-size:10.5px;color:#8a8676;text-align:center;margin-top:7px;line-height:1.4}"
    + "@media (prefers-reduced-motion: reduce){.pccbot-btn,.pccbot-typing span{transition:none;animation:none}}";

  function el(html) { var d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstChild; }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function fmt(s) {
    var h = esc(s);
    h = h.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    h = h.replace(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g, '<a href="mailto:$1">$1</a>');
    h = h.replace(/\bhttps?:\/\/[^\s<]+/g, function (u) { return '<a href="' + u + '" target="_blank" rel="noopener">' + u + "</a>"; });
    h = h.replace(/(^|[^\/])\b(sovgracekc\.org)\b/g, '$1<a href="https://sovgracekc.org" target="_blank" rel="noopener">$2</a>');
    h = h.replace(/\n/g, "<br>");
    return h;
  }

  var root, panel, log, input, sendBtn;

  function build() {
    var style = document.createElement("style"); style.textContent = css; document.head.appendChild(style);
    root = el('<div class="pccbot"></div>');
    var btn = el('<button class="pccbot-btn" aria-label="Open Sermon Bot chat">'
      + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg></button>');
    panel = el('<div class="pccbot-panel" role="dialog" aria-label="Church assistant chat"></div>');
    panel.appendChild(el('<div class="pccbot-head"><div><h3>Sermon Bot</h3>'
      + '<div class="sub">Providence Community Church · AI assistant</div></div>'
      + '<button class="x" aria-label="Close chat">&times;</button></div>'));
    log = el('<div class="pccbot-log" aria-live="polite"></div>'); panel.appendChild(log);
    var foot = el('<div class="pccbot-foot"><div class="pccbot-row">'
      + '<textarea rows="1" placeholder="Ask a question…" aria-label="Type your message"></textarea>'
      + '<button class="pccbot-send" aria-label="Send message"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></button>'
      + '</div><div class="pccbot-note">Automated assistant. Please don’t share sensitive personal information.</div></div>');
    panel.appendChild(foot);
    root.appendChild(panel); root.appendChild(btn); document.body.appendChild(root);

    input = foot.querySelector("textarea"); sendBtn = foot.querySelector(".pccbot-send");
    btn.addEventListener("click", toggle);
    panel.querySelector(".x").addEventListener("click", toggle);
    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
    input.addEventListener("input", function () { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 100) + "px"; });
  }

  function toggle() {
    opened = !opened;
    panel.classList.toggle("open", opened);
    if (opened) {
      if (!messages.length) {
        addBot("Hi! I’m Sermon Bot, Providence Community Church’s automated (AI) assistant. Ask me about Pastor Chris’s preaching and teaching, questions about the church, or how to get in touch. What can I help you with?");
      }
      setTimeout(function () { input.focus(); }, 50);
    }
  }

  function addMsg(text, who) {
    var m = el('<div class="pccbot-msg ' + who + '"></div>');
    m.innerHTML = fmt(text); log.appendChild(m); log.scrollTop = log.scrollHeight; return m;
  }
  function addBot(t) { addMsg(t, "bot"); }

  function typing(on) {
    var t = log.querySelector(".pccbot-typing");
    if (on && !t) { log.appendChild(el('<div class="pccbot-typing"><span></span><span></span><span></span></div>')); log.scrollTop = log.scrollHeight; }
    else if (!on && t) { t.remove(); }
  }

  function send() {
    var text = input.value.trim();
    if (!text || busy) return;
    input.value = ""; input.style.height = "auto";
    addMsg(text, "me");
    messages.push({ role: "user", content: text });
    busy = true; sendBtn.disabled = true; typing(true);

    fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, messages: messages })
    }).then(function (r) { return r.json(); }).then(function (j) {
      typing(false);
      var reply = (j && j.reply) ? j.reply : ("Sorry, I’m having trouble right now. Please email the church at " + CONTACT + ".");
      addBot(reply);
      messages.push({ role: "assistant", content: reply });
    }).catch(function () {
      typing(false);
      addBot("Sorry, I couldn’t reach the assistant. Please email the church at " + CONTACT + " and we’ll help you directly.");
    }).then(function () { busy = false; sendBtn.disabled = false; input.focus(); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
