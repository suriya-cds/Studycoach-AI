import json
import time
from pathlib import Path
from datetime import date, datetime, timedelta

import requests
import streamlit as st

APP_NAME = "StudyCoach AI"
DATA_FILE = Path("studycoach_data.json")
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2:3b"

st.set_page_config(page_title=APP_NAME, page_icon="🧠", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown('''
<style>
.stApp {
 background: radial-gradient(ellipse at 14% 3%,rgba(42,102,240,.19),transparent 42%),
 radial-gradient(ellipse at 88% 90%,rgba(50,76,170,.10),transparent 38%),
 linear-gradient(145deg,#060b17 0%,#0a1630 52%,#070d1c 100%);
 color:#f4f7ff;
}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#09162d 0%,#070e1d 100%);border-right:1px solid rgba(130,169,255,.15)}
.block-container{max-width:1250px;padding-top:1.6rem;padding-bottom:2.5rem}
h1,h2,h3{letter-spacing:-.7px}
.hero{padding:25px 27px;border:1px solid rgba(125,165,255,.20);border-radius:20px;background:linear-gradient(125deg,rgba(23,54,103,.82),rgba(13,27,52,.85));margin-bottom:22px}
.hero p{color:#b8c9e8;margin-bottom:0;line-height:1.7}
.metric-card{padding:18px;border-radius:16px;border:1px solid rgba(125,165,255,.18);background:linear-gradient(145deg,rgba(20,41,74,.88),rgba(12,27,50,.88));min-height:108px}
.metric-label{color:#a8bbda;font-size:13px;letter-spacing:.7px}
.metric-value{font-size:27px;font-weight:760;color:#f5f8ff;margin-top:5px}
.muted{color:#a8bbda;font-size:13px}
div.stButton>button,div.stFormSubmitButton>button,div.stDownloadButton>button{border-radius:10px;min-height:42px;font-weight:600}
div[data-testid="stForm"],div[data-testid="stExpander"]{border-color:rgba(125,165,255,.18);border-radius:14px}
[data-testid="stProgressBar"]>div>div{background:linear-gradient(90deg,#45d8d0,#568bff)}
footer{visibility:hidden}
.dashboard-page{min-height:78vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:35px 18px;position:relative;isolation:isolate}
.dashboard-page::before{content:"";position:absolute;width:min(68vw,650px);height:min(68vw,650px);border-radius:50%;background:radial-gradient(circle,rgba(39,105,255,.17),rgba(25,67,158,.06) 45%,transparent 70%);filter:blur(18px);z-index:-1;animation:glow 7s ease-in-out infinite alternate}
.dashboard-title{max-width:900px;margin:0 auto 22px;font-size:clamp(40px,6.5vw,82px);font-weight:850;line-height:1.08;letter-spacing:-3.5px;background:linear-gradient(110deg,#fff 12%,#d1e1ff 46%,#7daaff 78%,#fff 100%);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;animation:rise .9s ease-out both}
.dashboard-subtitle{max-width:580px;margin:auto;color:#b3c6e8;font-size:clamp(15px,1.8vw,19px);line-height:1.8;animation:rise 1.1s ease-out both}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
@keyframes glow{from{transform:scale(.94);opacity:.65}to{transform:scale(1.07);opacity:1}}
@media(max-width:600px){.dashboard-title{letter-spacing:-1.8px}.dashboard-page{min-height:70vh}}
</style>
''', unsafe_allow_html=True)

SYSTEM_PROMPT = '''
You are StudyCoach AI, a careful, accurate, supportive personal tutor.

ACCURACY:
- Answer the exact question. Start with a direct answer.
- Correctness matters more than sounding confident. Never invent facts, formulas,
  quotations, sources, or claim to have checked something you did not check.
- If unsure, state what is uncertain; do not present a guess as fact.
- If ambiguous, ask a short clarification or state your assumption.
- Separate facts from estimates, interpretations, and opinions.
- For maths, show steps and check the result.
- For programming, consider syntax, types, version assumptions, and edge cases.
- For multiple-choice questions, evaluate options before choosing.
- If challenged, re-evaluate independently rather than automatically agreeing
  or defending the previous answer.
- For recent information, explain that it needs an up-to-date source.
- Never claim verification unless you actually verified the answer.
- Define unfamiliar terms for beginners and use simple examples.
- For follow-ups, use conversation context and avoid repeating everything.
- If answers depend on context, explain the conditions.

TEACHING:
- Explain reasoning clearly and step by step when needed.
- Give useful examples and common mistakes when relevant.
- Avoid unnecessary introductions, repetition, and unrelated information.
- Help the student understand, not merely memorize.
'''

def default_data():
    return {"sessions": [], "quiz_history": [],
            "settings": {"model": DEFAULT_MODEL, "daily_goal": 120}}

def load_data():
    if not DATA_FILE.exists():
        return default_data()
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        data = default_data()
        if isinstance(raw, dict):
            if isinstance(raw.get("sessions"), list):
                data["sessions"] = raw["sessions"]
            if isinstance(raw.get("quiz_history"), list):
                data["quiz_history"] = raw["quiz_history"]
            if isinstance(raw.get("settings"), dict):
                data["settings"].update(raw["settings"])
        return data
    except (OSError, ValueError, TypeError):
        st.warning("Saved data could not be read. A fresh session is loaded; the original file was not deleted.")
        return default_data()

if "data" not in st.session_state:
    st.session_state.data = load_data()

DEFAULT_STATE = {
    "timer_running": False, "timer_end": 0.0, "timer_minutes": 25,
    "timer_topic": "Focused study", "timer_logged": False,
    "active_quiz": None, "quiz_answers": {}, "quiz_submitted": False,
    "teacher_conversation": [], "teacher_topic": "",
    "coach_conversation": [], "coach_level": "Beginner",
    "coach_style": "Step-by-step solution",
}
for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value

def save_data():
    temp = DATA_FILE.with_suffix(DATA_FILE.suffix + ".tmp")
    try:
        temp.write_text(json.dumps(st.session_state.data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        temp.replace(DATA_FILE)
    except (OSError, TypeError, ValueError) as exc:
        st.error(f"Could not save local data: {exc}")
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass

def get_sessions():
    return st.session_state.data["sessions"]

def log_session(minutes, topic, session_date=None):
    minutes = max(0, int(minutes))
    if minutes:
        get_sessions().append({
            "date": (session_date or date.today()).isoformat(),
            "time": datetime.now().strftime("%H:%M"),
            "minutes": minutes, "topic": (topic or "Focused study").strip()[:120]
        })
        save_data()

def safe_minutes(session):
    try:
        return max(0, int(session.get("minutes", 0)))
    except (TypeError, ValueError, AttributeError):
        return 0

def total_minutes():
    return sum(safe_minutes(s) for s in get_sessions())

def streak_count():
    studied = {s.get("date") for s in get_sessions()
               if s.get("date") and safe_minutes(s) > 0}
    current = date.today()
    if current.isoformat() not in studied:
        current -= timedelta(days=1)
    streak = 0
    while current.isoformat() in studied:
        streak += 1
        current -= timedelta(days=1)
    return streak

def current_model():
    return st.session_state.data["settings"].get("model", DEFAULT_MODEL)

def ollama_generate(prompt, system_prompt=SYSTEM_PROMPT, max_tokens=450,
                    temperature=0.2, json_mode=False):
    payload = {
        "model": current_model(), "prompt": prompt, "system": system_prompt,
        "stream": False, "keep_alive": "10m",
        "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": 4096}
    }
    if json_mode:
        payload["format"] = "json"
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=(5, 180))
        response.raise_for_status()
        answer = response.json().get("response", "").strip()
        if not answer:
            raise RuntimeError("The model returned an empty response. Try again.")
        return answer
    except requests.ConnectionError as exc:
        raise RuntimeError("Ollama is not running. Open Ollama or run `ollama serve`.") from exc
    except requests.Timeout as exc:
        raise RuntimeError("The AI request timed out. Try a shorter prompt or smaller model.") from exc
    except requests.HTTPError as exc:
        raise RuntimeError(f"Ollama returned an HTTP error. Check that '{current_model()}' is installed.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not connect to Ollama: {exc}") from exc

def stream_ai(prompt, system_prompt=SYSTEM_PROMPT, max_tokens=450):
    payload = {
        "model": current_model(), "prompt": prompt, "system": system_prompt,
        "stream": True, "keep_alive": "10m",
        "options": {"temperature": 0.2, "num_predict": max_tokens, "num_ctx": 4096}
    }
    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=(5, 180)) as response:
            response.raise_for_status()
            received = False
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if item.get("error"):
                    yield f"\n\n**Ollama error:** {item['error']}"
                    return
                chunk = item.get("response", "")
                if chunk:
                    received = True
                    yield chunk
                if item.get("done"):
                    break
            if not received:
                yield "The model returned an empty response. Check that the selected model is installed."
    except requests.ConnectionError:
        yield "\n\n**Ollama is not running.** Open Ollama or run `ollama serve`."
    except requests.Timeout:
        yield "\n\n**The request timed out.** Try a shorter question or smaller model."
    except requests.HTTPError:
        yield f"\n\n**Ollama HTTP error.** Check that `{current_model()}` is installed."
    except requests.RequestException as exc:
        yield f"\n\n**AI request failed:** `{exc}`"

def ask_ai(prompt, max_tokens=450):
    output = st.empty()
    answer = ""
    started = time.time()
    for chunk in stream_ai(prompt, SYSTEM_PROMPT, max_tokens):
        answer += chunk
        output.markdown(answer + " ▌")
    output.markdown(answer or "The model returned an empty response.")
    st.caption(f"Response time: {time.time()-started:.1f}s · {current_model()}")
    return answer

with st.sidebar:
    st.markdown("# 🧠 StudyCoach AI")
    st.caption("YOUR PERSONAL LEARNING SPACE")
    st.divider()
    page = st.radio("Navigation",
        ["Dashboard", "AI Teacher", "AI Coach", "AI Quiz", "Study Timer", "Progress"],
        label_visibility="collapsed")
    st.divider()
    st.markdown("### 🔥 Study streak")
    st.markdown(f"## {streak_count()} days")
    st.caption("Keep showing up, one session at a time.")
    with st.expander("⚙️ AI settings"):
        model_options = ["llama3.2:3b", "gemma3:1b", "qwen2.5:3b", "phi3:mini"]
        model = current_model()
        if model not in model_options:
            model_options.insert(0, model)
        chosen = st.selectbox("Local Ollama model", model_options, index=model_options.index(model))
        if chosen != model:
            st.session_state.data["settings"]["model"] = chosen
            save_data()
        st.caption("The selected model must be installed in Ollama.")
        if st.button("Test AI connection", use_container_width=True):
            try:
                r = requests.get("http://localhost:11434/api/tags", timeout=3)
                r.raise_for_status()
                installed = [m.get("name", "") for m in r.json().get("models", [])]
                st.success("Ollama is running.")
                if not any(x.split(":")[0] == chosen.split(":")[0] for x in installed):
                    st.warning(f"Install the model using `ollama pull {chosen}`")
            except requests.RequestException:
                st.error("Ollama is not responding at localhost:11434.")
    st.caption("Study history is saved locally.")

if page == "Dashboard":
    st.markdown('''
    <div class="dashboard-page"><div>
      <h1 class="dashboard-title">Hello there!</h1>
      <p class="dashboard-subtitle">Focus better. Learn faster. Build consistency.</p>
    </div></div>''', unsafe_allow_html=True)

elif page == "AI Teacher":
    st.markdown('<div class="hero"><h1>AI Teacher</h1><p>Learn any topic, then ask follow-up questions in the same conversation.</p></div>', unsafe_allow_html=True)
    with st.form("teacher_form"):
        topic = st.text_input("What do you want to learn?", placeholder="e.g. Python functions, databases, calculus")
        c1, c2 = st.columns(2)
        with c1:
            level = st.selectbox("Your level", ["Complete beginner", "Beginner", "Intermediate", "Advanced"])
        with c2:
            style = st.selectbox("Teaching style", ["Simple explanation", "Real-world examples", "Step-by-step lesson", "Analogies and intuition"])
        length = st.select_slider("Lesson length", ["Short", "Standard", "Detailed"], value="Standard")
        submit = st.form_submit_button("✨ Teach me", use_container_width=True)
    if submit:
        if not topic.strip():
            st.warning("Enter a topic first.")
        else:
            tokens = {"Short": 250, "Standard": 450, "Detailed": 700}[length]
            prompt = f'''Teach the topic: {topic}
Student level: {level}
Teaching style: {style}
Explain accurately and define unfamiliar terms.
Structure: 1. Definition 2. How it works 3. Checked example
4. Common mistakes 5. Three practice questions with answer key.
If uncertain, state the uncertainty rather than inventing facts.'''
            st.session_state.teacher_topic = topic.strip()
            st.session_state.teacher_conversation = []
            with st.spinner("Preparing your lesson..."):
                answer = ask_ai(prompt, tokens)
            st.session_state.teacher_conversation.append({"role": "assistant", "content": answer})
    if st.session_state.teacher_conversation:
        st.divider()
        st.subheader(f"Lesson conversation · {st.session_state.teacher_topic}")
        for message in st.session_state.teacher_conversation:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        follow = st.chat_input("Ask a follow-up about this lesson...", key="teacher_follow_up")
        if follow:
            st.session_state.teacher_conversation.append({"role": "user", "content": follow})
            recent = st.session_state.teacher_conversation[-8:]
            history = "\n\n".join(f"{'Student' if m['role']=='user' else 'Tutor'}: {m['content']}" for m in recent)
            prompt = f'''The student is learning {st.session_state.teacher_topic}.
Continue this conversation. Answer the newest question directly, use context,
explain carefully, and do not repeat the whole lesson.
Conversation:
{history}
Respond to the latest student message.'''
            with st.chat_message("user"):
                st.markdown(follow)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    answer = ask_ai(prompt, 450)
            st.session_state.teacher_conversation.append({"role": "assistant", "content": answer})
            st.rerun()
        if st.button("Start a new lesson", use_container_width=True):
            st.session_state.teacher_conversation = []
            st.session_state.teacher_topic = ""
            st.rerun()
    else:
        st.info("Create a lesson above. A follow-up message box will appear below the lesson.")

elif page == "AI Coach":
    st.markdown('<div class="hero"><h1>AI Coach</h1><p>Ask questions, get explanations, and continue the same conversation when switching pages.</p></div>', unsafe_allow_html=True)
    with st.expander("Response preferences", expanded=not bool(st.session_state.coach_conversation)):
        st.session_state.coach_level = st.selectbox("Your level", ["Beginner", "Intermediate", "Advanced"],
            index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.coach_level), key="coach_level_select")
        styles = ["Step-by-step solution", "Hints first", "Explain the concept", "Direct answer with reasoning"]
        st.session_state.coach_style = st.selectbox("How should I help?", styles,
            index=styles.index(st.session_state.coach_style), key="coach_style_select")
    for message in st.session_state.coach_conversation:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Ask StudyCoach anything...")
    if question:
        st.session_state.coach_conversation.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        recent = st.session_state.coach_conversation[-10:]
        history = "\n\n".join(f"{'Student' if m['role']=='user' else 'StudyCoach'}: {m['content']}" for m in recent)
        prompt = f'''Student level: {st.session_state.coach_level}
Preferred response style: {st.session_state.coach_style}
Conversation:
{history}
Answer the newest message accurately. Use context. If ambiguous or uncertain,
say so rather than guessing.'''
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = ask_ai(prompt, 450)
        st.session_state.coach_conversation.append({"role": "assistant", "content": answer})
        st.session_state.coach_conversation = st.session_state.coach_conversation[-40:]
        st.rerun()
    if st.session_state.coach_conversation:
        if st.button("Clear AI Coach conversation", use_container_width=True):
            st.session_state.coach_conversation = []
            st.rerun()
    else:
        st.info("Ask your first question below. Your conversation remains when you switch sections.")

elif page == "AI Quiz":
    st.markdown('<div class="hero"><h1>AI Quiz</h1><p>Generate a quiz on any topic, answer it, and review your score.</p></div>', unsafe_allow_html=True)
    with st.form("quiz_setup"):
        topic = st.text_input("Quiz topic", placeholder="e.g. Python loops, geography, biology")
        c1, c2, c3 = st.columns(3)
        with c1:
            count = st.selectbox("Questions", [3, 5, 8, 10], index=1)
        with c2:
            difficulty = st.selectbox("Difficulty", ["Easy", "Mixed", "Challenging"])
        with c3:
            quiz_level = st.selectbox("Level", ["Beginner", "Intermediate", "Advanced"])
        generate = st.form_submit_button("✨ Generate quiz", use_container_width=True)
    if generate:
        if not topic.strip():
            st.warning("Enter a quiz topic first.")
        else:
            prompt = f'''Create exactly {count} multiple-choice questions about "{topic}".
Difficulty: {difficulty}. Learner level: {quiz_level}.
Return ONLY valid JSON:
{{"questions":[{{"question":"Question text","options":["option one","option two","option three","option four"],"answer":0,"explanation":"Why correct"}}]}}
Rules:
- Exactly {count} questions and four distinct options per question.
- answer is an integer 0-3 and matches the correct option.
- Solve/check each question independently before choosing the answer index.
- Each question must have one clear, unambiguous correct answer.
- Verify calculations; avoid disputed facts and duplicate questions.
- Explanations must support the correct answer. Return JSON only.'''
            with st.spinner("Creating your quiz with local AI..."):
                try:
                    raw = ollama_generate(prompt, "Create accurate educational quizzes. Check answer keys. Return valid JSON only.", 1800, 0.1, True)
                    result = json.loads(raw)
                    questions = result.get("questions", []) if isinstance(result, dict) else []
                    valid = len(questions) == count and all(
                        isinstance(q, dict) and isinstance(q.get("question"), str) and q["question"].strip()
                        and isinstance(q.get("options"), list) and len(q["options"]) == 4
                        and all(isinstance(o, str) and o.strip() for o in q["options"])
                        and len(set(q["options"])) == 4
                        and isinstance(q.get("answer"), int) and not isinstance(q.get("answer"), bool)
                        and 0 <= q["answer"] <= 3 and isinstance(q.get("explanation"), str)
                        for q in questions)
                    if not valid:
                        st.error("The model returned an invalid quiz. Try again or choose fewer questions.")
                    else:
                        st.session_state.active_quiz = {"topic": topic.strip(), "difficulty": difficulty,
                            "questions": questions, "created": datetime.now().strftime("%Y-%m-%d %H:%M")}
                        st.session_state.quiz_answers = {}
                        st.session_state.quiz_submitted = False
                        st.rerun()
                except (RuntimeError, ValueError, TypeError, KeyError) as exc:
                    st.error(f"Could not create quiz: {exc}")
    quiz = st.session_state.active_quiz
    if quiz:
        st.divider()
        st.subheader(f"{quiz['topic']} · {quiz['difficulty']}")
        st.caption(f"{len(quiz['questions'])} questions · Generated {quiz['created']}")
        if not st.session_state.quiz_submitted:
            with st.form("quiz_answer_form"):
                answers = {}
                for i, q in enumerate(quiz["questions"]):
                    st.markdown(f"**{i+1}. {q['question']}**")
                    answers[str(i)] = st.radio("Choose one answer", q["options"], index=None,
                        key=f"quiz_answer_{i}_{quiz['created']}", label_visibility="collapsed")
                    st.write("")
                submitted = st.form_submit_button("Check my answers", use_container_width=True)
            if submitted:
                st.session_state.quiz_answers = answers
                st.session_state.quiz_submitted = True
                st.rerun()
        else:
            questions, answers = quiz["questions"], st.session_state.quiz_answers
            correct_count = sum(
                (q["options"].index(answers[str(i)]) if answers.get(str(i)) in q["options"] else None) == q["answer"]
                for i, q in enumerate(questions))
            percentage = round(correct_count / len(questions) * 100)
            st.markdown(f'<div class="metric-card"><div class="metric-label">YOUR RESULT</div><div class="metric-value">{correct_count} / {len(questions)} · {percentage}%</div><div class="muted">{"Excellent work!" if percentage >= 80 else "Review the explanations below and try again."}</div></div>', unsafe_allow_html=True)
            st.progress(percentage / 100)
            for i, q in enumerate(questions):
                chosen = answers.get(str(i))
                index = q["options"].index(chosen) if chosen in q["options"] else None
                with st.container(border=True):
                    st.markdown(f"**{i+1}. {q['question']}**")
                    if chosen is None:
                        st.warning("Not answered")
                    elif index == q["answer"]:
                        st.success(f"Your answer: {chosen}")
                    else:
                        st.error(f"Your answer: {chosen}")
                    st.markdown(f"**Correct answer:** {q['options'][q['answer']]}")
                    st.write(q["explanation"])
            if st.button("Create another quiz", use_container_width=True):
                st.session_state.active_quiz = None
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.rerun()
            if st.button("Save quiz result", use_container_width=True):
                st.session_state.data["quiz_history"].append({"topic": quiz["topic"], "date": quiz["created"],
                    "score": correct_count, "total": len(questions), "percentage": percentage})
                st.session_state.data["quiz_history"] = st.session_state.data["quiz_history"][-100:]
                save_data()
                st.success("Quiz result saved locally.")
    if st.session_state.data["quiz_history"]:
        with st.expander("Previous saved quiz results"):
            st.dataframe(list(reversed(st.session_state.data["quiz_history"][-20:])),
                         use_container_width=True, hide_index=True)

elif page == "Study Timer":
    st.markdown('<div class="hero"><h1>Focus mode</h1><p>One task. One session. Give your attention to what matters.</p></div>', unsafe_allow_html=True)
    st.session_state.timer_topic = st.text_input("What are you working on?", value=st.session_state.timer_topic)
    durations = [15, 25, 45, 60, 90]
    selected = st.radio("Focus duration", durations,
        index=durations.index(st.session_state.timer_minutes if st.session_state.timer_minutes in durations else 25),
        horizontal=True, format_func=lambda x: f"{x} min")
    if not st.session_state.timer_running:
        st.session_state.timer_minutes = selected

    @st.fragment(run_every="1s")
    def timer_panel():
        running = st.session_state.timer_running
        remaining = max(0, int(st.session_state.timer_end - time.time())) if running else st.session_state.timer_minutes * 60
        if running and remaining == 0 and not st.session_state.timer_logged:
            log_session(st.session_state.timer_minutes, st.session_state.timer_topic)
            st.session_state.timer_running = False
            st.session_state.timer_logged = True
            st.success("🎉 Session complete. Your time has been saved.")
            st.rerun()
        mins, secs = divmod(remaining, 60)
        label = "FOCUS IN PROGRESS" if running else "READY TO FOCUS"
        st.markdown(f'<div class="hero" style="text-align:center;padding:35px"><div class="muted">{label}</div><div style="font-size:clamp(55px,9vw,95px);font-weight:800;letter-spacing:2px">{mins:02d}:{secs:02d}</div><p>{st.session_state.timer_topic or "Focused study"}</p></div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        with a:
            if not running and st.button("▶ Start focus", use_container_width=True):
                st.session_state.timer_minutes = selected
                st.session_state.timer_end = time.time() + selected * 60
                st.session_state.timer_running = True
                st.session_state.timer_logged = False
                st.rerun()
        with b:
            if st.button("↺ Reset", use_container_width=True):
                st.session_state.timer_running = False
                st.session_state.timer_logged = False
                st.session_state.timer_minutes = selected
                st.rerun()
    timer_panel()
    st.caption("Keep this browser tab open while the timer runs. Completed sessions save automatically.")

elif page == "Progress":
    st.markdown('<div class="hero"><h1>Your progress</h1><p>Review your study history and set a daily focus target.</p></div>', unsafe_allow_html=True)
    total = total_minutes()
    studied_days = len({s.get("date") for s in get_sessions() if s.get("date") and safe_minutes(s) > 0})
    c1, c2, c3 = st.columns(3)
    def metric(label, value, note):
        st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="muted">{note}</div></div>', unsafe_allow_html=True)
    with c1:
        metric("TOTAL FOCUS", f"{total//60}h {total%60}m", "Recorded study time")
    with c2:
        metric("DAYS STUDIED", str(studied_days), "Days with sessions")
    with c3:
        metric("CURRENT STREAK", f"{streak_count()} days", "Consecutive study days")
    st.divider()
    st.subheader("Daily target")
    old_goal = int(st.session_state.data["settings"].get("daily_goal", 120))
    goal = st.number_input("Minutes per day", 15, 720, max(15, min(720, old_goal)), step=15)
    if st.button("Save daily target"):
        st.session_state.data["settings"]["daily_goal"] = int(goal)
        save_data()
        st.success("Daily target saved.")
    st.divider()
    st.subheader("Log a completed session")
    with st.form("manual_session_form"):
        c1, c2 = st.columns(2)
        with c1:
            manual_topic = st.text_input("Topic", placeholder="e.g. Python practice")
        with c2:
            manual_minutes = st.number_input("Minutes studied", 1, 1000, 30)
        manual_date = st.date_input("Session date", value=date.today(), max_value=date.today())
        submit = st.form_submit_button("Add session", use_container_width=True)
    if submit:
        log_session(int(manual_minutes), manual_topic or "Independent study", manual_date)
        st.success("Session saved.")
        st.rerun()
    st.divider()
    st.subheader("Study history")
    if get_sessions():
        st.dataframe([{"Date": s.get("date", ""), "Time": s.get("time", ""),
                       "Topic": s.get("topic", ""), "Minutes": s.get("minutes", 0)}
                      for s in reversed(get_sessions()[-100:])],
                     use_container_width=True, hide_index=True)
        st.download_button("⬇ Export study history",
            data=json.dumps(get_sessions(), ensure_ascii=False, indent=2),
            file_name="studycoach_history.json", mime="application/json",
            use_container_width=True)
    else:
        st.info("No study sessions recorded yet.")

st.divider()
st.caption("StudyCoach AI · Local-first learning workspace")