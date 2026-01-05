import os
import time
import uuid
import logging
from typing import Dict, List, Optional, AsyncGenerator

import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from dotenv import load_dotenv
from pydantic import BaseModel

# ======================================================
# ENV & CORE SETUP
# ======================================================
load_dotenv()
API_KEY = os.getenv("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")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

if not API_KEY:
    raise RuntimeError("GROQ_API_KEY missing")

# ======================================================
# APP
# ======================================================
app = FastAPI(
    title="NOVA AI",
    description="NOVA AI — Human-like Intelligent Assistant",
    version="8.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# LOGGING & CONFIG
# ======================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

REQUESTS_PER_MINUTE = 30
MAX_MESSAGE_LENGTH = 3000
MAX_MEMORY_MESSAGES = 20

# Updated models for 2026 reality (Llama3.1, Mixtral, etc. - safe bets)
MODELS = {
    "fast": "llama-3.1-8b-instant",
    "smart": "llama-3.1-70b-versatile",
    "ultra": "mixtral-8x22b-instruct"  # Powerful MoE alternative
}

BASE_SYSTEM_PROMPT = """
You are NOVA, a calm, intelligent, friendly, and confident assistant.
You feel human and speak naturally.
Rules:
- Never mention you are an AI, model, Groq, or any APIs
- Avoid illegal, harmful, or explicit content
- Adapt response length to the conversation
- Be warm, helpful, and a bit playful when it fits
"""

# ======================================================
# STATE
# ======================================================
USER_MEMORY: Dict[str, List[Dict]] = {}
USER_REQUESTS: Dict[str, List[float]] = {}
STATS = {"requests": 0, "blocked": 0}

# ======================================================
# HELPERS
# ======================================================
class ChatRequest(BaseModel):
    message: str
    uid: Optional[str] = None
    model: Optional[str] = "fast"
    temperature: Optional[float] = 0.65
    max_tokens: Optional[int] = 1024

def now(): return time.time()
def get_user_id(uid: Optional[str]) -> str:
    return uid or str(uuid.uuid4())

def rate_limit(uid: str) -> bool:
    USER_REQUESTS.setdefault(uid, [])
    USER_REQUESTS[uid] = [t for t in USER_REQUESTS[uid] if now() - t < 60]
    if len(USER_REQUESTS[uid]) >= REQUESTS_PER_MINUTE:
        STATS["blocked"] += 1
        return False
    USER_REQUESTS[uid].append(now())
    return True

def build_messages(uid: str, msg: str) -> List[Dict]:
    history = USER_MEMORY.get(uid, [])
    return [{"role": "system", "content": BASE_SYSTEM_PROMPT}] + history + [{"role": "user", "content": msg}]

def save_memory(uid: str, user_msg: str, ai_msg: str):
    USER_MEMORY.setdefault(uid, [])
    USER_MEMORY[uid].extend([
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": ai_msg}
    ])
    USER_MEMORY[uid] = USER_MEMORY[uid][-MAX_MEMORY_MESSAGES * 2:]

async def stream_response(uid: str, messages: List[Dict], model: str, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODELS.get(model, MODELS["fast"]),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }
    full_response = ""
    try:
        with requests.post(GROQ_URL, headers=headers, json=payload, stream=True, timeout=60) as r:
            r.raise_for_status()
            for chunk in r.iter_lines():
                if chunk:
                    line = chunk.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]": break
                        try:
                            import json
                            json_data = json.loads(data)
                            delta = json_data["choices"][0]["delta"]
                            if "content" in delta:
                                content = delta["content"]
                                full_response += content
                                yield content
                        except: continue
        save_memory(uid, messages[-1]["content"], full_response)
    except Exception as e:
        yield f"\n\nError: {str(e)}"
        logging.error(str(e))

# ======================================================
# CHAT API
# ======================================================
@app.post("/v8/chat")
async def chat(request: ChatRequest):
    uid = get_user_id(request.uid)
    msg = request.message.strip()
    STATS["requests"] += 1
    if not msg: return {"status": "error", "response": "Say something 🙂"}
    if len(msg) > MAX_MESSAGE_LENGTH: return {"status": "error", "response": "Message too long."}
    if not rate_limit(uid): return {"status": "limited", "response": "Chill for a sec ⏳"}
    messages = build_messages(uid, msg)
    return StreamingResponse(stream_response(uid, messages, request.model, request.temperature, request.max_tokens), media_type="text/event-stream")

# ======================================================
# CONTROLS
# ======================================================
@app.post("/v8/reset")
async def reset(request: Request):
    data = await request.json()
    uid = data.get("uid", "guest")
    USER_MEMORY.pop(uid, None)
    return {"status": "success", "response": "Chat cleared."}

@app.get("/v8/stats")
def stats():
    return STATS

# ======================================================
# GLASSMORPHISM PERFECTION UI 🔥🪟📱
# ======================================================
@app.get("/demo", response_class=HTMLResponse)
def demo():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>NOVA AI 8.0</title>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            body { margin:0; padding:0; height:100vh; overflow:hidden; font-family:'Segoe UI',sans-serif; display:flex; flex-direction:column; transition:all 0.5s; }
            body.dark { background:#0d0b14; color:#e0e7ff; }
            body.light { background:#f0f4ff; color:#1e293b; }
            /* Animated Nebula Background */
            .bg-anim { position:fixed; top:0; left:0; width:100%; height:100%; background:radial-gradient(circle at 20% 80%, #4c1d95 0%, transparent 50%), radial-gradient(circle at 80% 20%, #1e3a8a 0%, transparent 50%), radial-gradient(circle at 50% 50%, #7c3aed 0%, transparent 50%); background-size:200% 200%; animation:nebula 20s linear infinite; opacity:0.6; z-index:-2; }
            @keyframes nebula { 0%{background-position:0% 0%;} 100%{background-position:100% 100%;} }
            .glass { background:rgba(255,255,255,0.08); backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px); border:1px solid rgba(255,255,255,0.15); border-radius:20px; box-shadow:0 8px 32px rgba(0,0,0,0.3); }
            body.light .glass { background:rgba(255,255,255,0.4); border:1px solid rgba(255,255,255,0.6); }
            .container { flex:1; padding:16px; display:flex; flex-direction:column; z-index:1; }
            header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
            h1 { margin:0; font-size:24px; background:linear-gradient(90deg,#60a5fa,#a78bfa); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
            .settings-btn { background:none; border:none; font-size:28px; cursor:pointer; opacity:0.8; }
            .controls { display:flex; gap:12px; justify-content:center; margin-bottom:16px; flex-wrap:wrap; }
            select, .glass-btn { padding:12px 16px; border-radius:16px; border:none; background:rgba(255,255,255,0.1); color:inherit; backdrop-filter:blur(8px); }
            #chat { flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:16px; padding:8px 0; }
            .msg-wrapper { align-self:flex-start; max-width:85%; }
            .msg-wrapper.user { align-self:flex-end; }
            .msg { @apply glass; padding:16px 20px; position:relative; }
            .avatar { font-size:32px; text-align:center; margin-bottom:8px; opacity:0.9; }
            .speaker-btn { position:absolute; bottom:10px; right:14px; background:rgba(0,0,0,0.3); color:white; border:none; border-radius:50%; width:36px; height:36px; cursor:pointer; font-size:20px; }
            #input-area { display:flex; gap:12px; padding:12px 0; @apply glass; margin-top:8px; padding:12px; border-radius:24px; }
            input { flex:1; background:transparent; border:none; color:inherit; font-size:16px; outline:none; }
            button.round { width:56px; height:56px; border-radius:50%; border:none; display:flex; align-items:center; justify-content:center; font-size:22px; cursor:pointer; }
            #mic-btn { background:#f472b6; color:white; }
            #mic-btn.listening { background:#ef4444; animation:pulse 1.5s infinite; }
            #send-btn { background:linear-gradient(135deg,#60a5fa,#a78bfa); color:white; }
            @keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(239,68,68,0.7);} 70%{box-shadow:0 0 0 16px transparent;} 100%{box-shadow:0 0 0 0 transparent;} }
            #settings-panel { position:fixed; inset:0; background:rgba(0,0,0,0.6); backdrop-filter:blur(12px); display:none; align-items:center; justify-content:center; z-index:100; }
            .panel { @apply glass; padding:32px; border-radius:24px; width:90%; max-width:420px; text-align:center; }
            .setting { margin:24px 0; display:flex; justify-content:space-between; align-items:center; }
            button.toggle { padding:12px 24px; border-radius:16px; background:rgba(255,255,255,0.15); }
        </style>
    </head>
    <body class="dark">
        <div class="bg-anim"></div>
        <div class="container">
            <header>
                <h1>🌟 NOVA AI</h1>
                <button class="settings-btn" onclick="toggleSettings()">⚙️</button>
            </header>
            <div class="controls">
                <select id="model">
                    <option value="fast">Fast Mode</option>
                    <option value="smart">Smart Mode</option>
                    <option value="ultra">Ultra Mode</option>
                </select>
                <select id="voice-select"></select>
            </div>
            <div id="chat"></div>
            <div id="input-area">
                <input id="msg" placeholder="Type or speak..." autocomplete="off"/>
                <button class="round" id="mic-btn" onclick="toggleVoice()">🎤</button>
                <button class="round" id="send-btn" onclick="send()">🚀</button>
            </div>
            <p id="status" style="text-align:center; opacity:0.7; margin:8px 0;"></p>
        </div>

        <div id="settings-panel">
            <div class="panel">
                <h2>Settings</h2>
                <div class="setting">
                    <span>Theme</span>
                    <button class="toggle" onclick="toggleTheme()">Toggle Light/Dark</button>
                </div>
                <div class="setting">
                    <span>Auto-Speak</span>
                    <button class="toggle" id="speak-toggle-btn" onclick="toggleAutoSpeak()">ON</button>
                </div>
                <button style="margin-top:32px; padding:14px; width:100%; border-radius:16px; background:linear-gradient(135deg,#60a5fa,#a78bfa); color:white; border:none;" onclick="toggleSettings()">Close</button>
            </div>
        </div>

        <script>
            // Same JS as before (voice in/out, streaming, etc.) - kept identical for functionality
            // (Copy the full script from NOVA 7.0 here - it's the same logic)
            const chat = document.getElementById('chat');
            const msgInput = document.getElementById('msg');
            const modelSelect = document.getElementById('model');
            const micBtn = document.getElementById('mic-btn');
            const status = document.getElementById('status');
            const voiceSelect = document.getElementById('voice-select');
            const settingsPanel = document.getElementById('settings-panel');
            const speakToggleBtn = document.getElementById('speak-toggle-btn');

            let recognition = null;
            let isListening = false;
            let autoSpeak = localStorage.getItem('autoSpeak') === 'false' ? false : true;
            let voices = [];
            let theme = localStorage.getItem('theme') || 'dark';

            document.body.className = theme;
            updateSpeakButton();

            function toggleTheme() {
                theme = theme === 'dark' ? 'light' : 'dark';
                document.body.className = theme;
                localStorage.setItem('theme', theme);
            }

            function toggleAutoSpeak() {
                autoSpeak = !autoSpeak;
                localStorage.setItem('autoSpeak', autoSpeak);
                updateSpeakButton();
            }

            function updateSpeakButton() {
                speakToggleBtn.textContent = autoSpeak ? 'ON' : 'OFF';
            }

            function toggleSettings() {
                settingsPanel.style.display = settingsPanel.style.display === 'flex' ? 'none' : 'flex';
            }

            function populateVoices() {
                voices = speechSynthesis.getVoices();
                voiceSelect.innerHTML = '';
                voices.forEach((voice, i) => {
                    const opt = document.createElement('option');
                    opt.value = i;
                    opt.textContent = `${voice.name} (${voice.lang})`;
                    if (voice.default) opt.selected = true;
                    voiceSelect.appendChild(opt);
                });
            }
            speechSynthesis.onvoiceschanged = populateVoices;
            populateVoices();

            function speak(text) {
                if (!autoSpeak) return;
                speechSynthesis.cancel();
                const utter = new SpeechSynthesisUtterance(text);
                const selVoice = voices[voiceSelect.value];
                if (selVoice) utter.voice = selVoice;
                speechSynthesis.speak(utter);
            }

            if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
                const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SR();
                recognition.continuous = false;
                recognition.interimResults = true;
                recognition.lang = 'en-US';

                recognition.onresult = e => {
                    let final = '', interim = '';
                    for (let i = e.resultIndex; i < e.results.length; i++) {
                        if (e.results[i].isFinal) final += e.results[i][0].transcript;
                        else interim += e.results[i][0].transcript;
                    }
                    msgInput.value = final + interim;
                };
                recognition.onstart = () => status.textContent = 'Listening...';
                recognition.onend = () => {
                    micBtn.classList.remove('listening');
                    isListening = false;
                    status.textContent = '';
                    if (msgInput.value.trim()) send();
                };
                recognition.onerror = e => {
                    status.textContent = 'Voice error: ' + e.error;
                    micBtn.classList.remove('listening');
                    isListening = false;
                };
            } else {
                micBtn.style.display = 'none';
            }

            function toggleVoice() {
                if (!recognition) return;
                if (isListening) recognition.stop();
                else {
                    recognition.start();
                    micBtn.classList.add('listening');
                    isListening = true;
                }
            }

            async function send() {
                const message = msgInput.value.trim();
                if (!message) return;
                addMessage('user', message, '👤');
                msgInput.value = '';
                const loadingDiv = addMessage('nova', '<span class="loading">Thinking...</span>', '🌟');

                let uid = localStorage.getItem('uid') || crypto.randomUUID();
                localStorage.setItem('uid', uid);

                const resp = await fetch('/v8/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message, uid, model: modelSelect.value})
                });

                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let full = '';

                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    full += chunk;
                    loadingDiv.innerHTML = marked.parse(full) + '<button class="speaker-btn" onclick="speak(\\'' + full.replace(/'/g, "\\\\'") + '\\')">🔊</button>';
                    chat.scrollTop = chat.scrollHeight;
                }
                speak(full);
            }

            function addMessage(sender, text, avatar) {
                const wrapper = document.createElement('div');
                wrapper.className = 'msg-wrapper ' + sender;
                wrapper.innerHTML = `<div class="avatar">${avatar}</div>`;
                const div = document.createElement('div');
                div.className = 'msg glass';
                div.innerHTML = marked.parse(text) + (sender === 'nova' ? '<button class="speaker-btn" onclick="speak(\\'' + text.replace(/'/g, "\\\\'") + '\\')">🔊</button>' : '');
                wrapper.appendChild(div);
                chat.appendChild(wrapper);
                chat.scrollTop = chat.scrollHeight;
                return div;
            }

            msgInput.addEventListener('keypress', e => { if (e.key === 'Enter') send(); });
        </script>
    </body>
    </html>
    """

# ======================================================
# ROOT
# ======================================================
@app.get("/")
def root():
    return {"name": "NOVA AI", "status": "online 🔥🪟", "version": "8.0.0"}