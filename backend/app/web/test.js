"use strict";
const $ = id => document.getElementById(id);
let active = null, accessKey = null, quiz = null, index = 0, away = false;
let fullscreenUnavailable = false, saving = false, pending = new Map(), answers = new Map();
let chosen = null, serverEpoch = 0, monotonicAt = 0, finishArmed = false, ending = false;
const sections = ["auth", "catalog", "rules", "exam", "result"];
function screen(name) { sections.forEach(id => $(id).hidden = id !== name); }
function notice(text = "") { $("notice").textContent = text; }
async function api(path, options = {}) {
  const response = await fetch("/api" + path, {credentials: "same-origin", ...options,
    headers: {"Content-Type": "application/json", ...(options.headers || {})}});
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Проверьте введённые данные.");
  return body;
}
const post = (path, data, options = {}) => api(path, {method: "POST", body: JSON.stringify(data), ...options});
function element(tag, text, cls) { const node = document.createElement(tag); if (text) node.textContent = text; if (cls) node.className = cls; return node; }
function remember() { sessionStorage.setItem("delul_attempt", JSON.stringify({id: active.id, token: accessKey})); }
function apply(data) {
  active = data; serverEpoch = Date.parse(data.server_time); monotonicAt = performance.now();
  if (data.attempt_token) accessKey = data.attempt_token;
  if (data.status !== "in_progress") { closeAttempt(data); return; }
  if (data.quiz) { quiz = data.quiz; answers = new Map(data.answers.map(a => [a.question_id, a.answer_option_id])); }
  remember(); $("exam-title").textContent = quiz.title; $("focus-warning").hidden = !away;
  screen("exam"); renderQuestion(); tick();
}
function renderQuestion() {
  if (!quiz || !active || active.status !== "in_progress") return;
  const q = quiz.questions[index];
  $("progress").textContent = `Вопрос ${index + 1} из ${quiz.questions.length} · предупреждений ${active.focus_count} из 2`;
  $("question-text").textContent = q.text; $("choices").replaceChildren(element("legend", "Выберите ответ"));
  for (const option of q.options) {
    const label = element("label", "", "option"), radio = element("input");
    radio.type = "radio"; radio.name = "answer"; radio.value = option.id;
    radio.checked = (pending.has(q.id) ? pending.get(q.id) : answers.get(q.id)) === option.id;
    radio.addEventListener("change", () => {pending.set(q.id, option.id); flushAnswers();});
    label.append(radio, element("span", option.text)); $("choices").append(label);
  }
  $("previous").disabled = index === 0; $("next").disabled = index === quiz.questions.length - 1;
  $("save-status").textContent = pending.size ? "Сохранение ответа…" : "Ответы сохранены на сервере";
}
async function flushAnswers() {
  if (saving || !pending.size || !active || active.status !== "in_progress" || away) return;
  saving = true; const batch = new Map(pending);
  try {
    const data = await api(`/attempts/${active.id}/answers`, {method: "PATCH", body: JSON.stringify({attempt_token: accessKey,
      answers: [...batch].map(([question_id, answer_option_id]) => ({question_id, answer_option_id}))})});
    for (const [key, value] of batch) {answers.set(key, value); if (pending.get(key) === value) pending.delete(key);}
    apply(data); notice();
  } catch (error) {notice("Ответ пока не сохранён: " + error.message);} finally {saving = false;}
  renderQuestion();
}
function tick() {
  if (!active || active.status !== "in_progress") return;
  const left = Math.max(0, Math.ceil((Date.parse(active.deadline_at) - (serverEpoch + performance.now() - monotonicAt)) / 1000));
  $("timer").textContent = `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
  if (!left) {$("question-card").hidden = true; $("finish-test").disabled = true; endAttempt(false);}
}
function closeAttempt(data) {
  active = data; away = false; pending.clear(); quiz = null; sessionStorage.removeItem("delul_attempt");
  sessionStorage.removeItem("delul_focus_event"); screen("result");
  const titles = {submitted: "Тест завершён", expired: "Время истекло", blocked: "Доступ к попытке закрыт"};
  const reasons = {focus_lost: "Зарегистрирован повторный уход из вкладки или полного экрана.", connection_lost: "Не было связи с сервером более 45 секунд."};
  $("result-title").textContent = titles[data.status] || "Попытка недоступна";
  $("result-text").textContent = data.status === "blocked" ? (reasons[data.blocked_reason] || "Попытка заблокирована.") : `Сохранённый результат: ${data.score ?? 0} из ${data.max_score ?? 0}.`;
  $("question-text").textContent = ""; $("choices").replaceChildren();
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
}
async function endAttempt(ask = true) {
  if (!active || active.status !== "in_progress" || saving || ending) return;
  if (ask && !finishArmed) {
    finishArmed = true; $("finish-test").textContent = "Нажмите ещё раз, чтобы завершить";
    setTimeout(() => {finishArmed = false; $("finish-test").textContent = "Завершить тест";}, 6000);
    return;
  }
  await flushAnswers(); if (pending.size) {notice("Сначала дождитесь сохранения ответов."); return;}
  ending = true;
  try {apply(await post(`/attempts/${active.id}/submit`, {attempt_token: accessKey}));} catch (error) {notice(error.message);} finally {ending = false;}
}
function loseFocus(kind) {
  if (!active || active.status !== "in_progress" || away) return;
  away = true; $("focus-warning").hidden = false;
  const payload = {attempt_token: accessKey, event_id: crypto.randomUUID(), kind};
  sessionStorage.setItem("delul_focus_event", JSON.stringify(payload));
  if (kind === "pagehide") {
    navigator.sendBeacon(`/api/attempts/${active.id}/events`, new Blob([JSON.stringify(payload)], {type: "application/json"}));
  } else post(`/attempts/${active.id}/events`, payload, {keepalive: true}).then(data => {
    sessionStorage.removeItem("delul_focus_event"); apply(data);
  }).catch(() => {});
}
async function returnToExam() {
  if (!active || active.status !== "in_progress" || document.hidden) return;
  if (!document.fullscreenElement && !fullscreenUnavailable) {
    $("focus-warning").hidden = false; return;
  }
  try {
    const event = sessionStorage.getItem("delul_focus_event");
    if (event) {apply(await post(`/attempts/${active.id}/events`, JSON.parse(event))); sessionStorage.removeItem("delul_focus_event");}
    if (active.status !== "in_progress") return;
    away = false; apply(await post(`/attempts/${active.id}/heartbeat`, {attempt_token: accessKey})); flushAnswers();
  } catch (error) {notice(error.message);}
}
async function listTests() {
  notice(); active = null; screen("catalog"); $("quiz-list").replaceChildren();
  const [page, attempts] = await Promise.all([api("/quizzes?limit=100"), api("/attempts/me?limit=100")]);
  if (!page.items.length) $("quiz-list").append(element("p", "Опубликованных тестов пока нет."));
  for (const item of page.items) {
    const card = element("article", "", "card"), previous = attempts.items.find(a => a.quiz_id === item.id);
    card.append(element("h2", item.title), element("p", `${item.time_limit_minutes} минут · одна попытка`));
    if (previous) {card.append(element("p", `Попытка уже начата. Статус: ${previous.status}.`));
      const saved = JSON.parse(sessionStorage.getItem("delul_attempt") || "null");
      if (previous.status === "in_progress" && saved && saved.id === previous.id) {
        const button = element("button", "Продолжить в этой вкладке"); button.onclick = () => resume(saved); card.append(button);
      }
    } else {
      const button = element("button", "Прочитать правила"); button.onclick = () => {
        chosen = item; $("rules-title").textContent = item.title; $("duration").textContent = `Время: ${item.time_limit_minutes} минут.`;
        $("accept-rules").checked = false; $("start-test").disabled = true; screen("rules");
      }; card.append(button);
    } $("quiz-list").append(card);
  }
}
async function resume(saved) {
  accessKey = saved.token;
  try {apply(await api(`/attempts/${saved.id}`, {headers: {"X-Attempt-Token": accessKey}}));}
  catch (error) {notice(error.message);}
}
async function loadAccount() {
  const user = await api("/auth/me"); $("account").textContent = user.full_name; $("logout").hidden = false;
  if (user.role !== "student") {screen("catalog"); $("quiz-list").replaceChildren(element("p", "Эта страница предназначена для студентов. Управление тестами и просмотр попыток доступны через Swagger /api/docs.")); return;}
  await listTests();
}
$("login-form").onsubmit = async event => {event.preventDefault(); try {
  await post("/auth/session", {email: $("email").value, password: $("password").value}); $("password").value = ""; await loadAccount();
} catch (error) {notice(error.message);}};
$("register-form").onsubmit = async event => {event.preventDefault(); try {
  const values = Object.fromEntries(new FormData(event.target)); await post("/auth/register", values); event.target.reset(); notice("Аккаунт создан. Теперь войдите.");
} catch (error) {notice(error.message);}};
$("logout").onclick = async () => {if (active?.status === "in_progress") {notice("Сначала завершите попытку."); return;} await post("/auth/logout", {}); $("logout").hidden = true; $("account").textContent = ""; screen("auth");};
$("accept-rules").onchange = () => $("start-test").disabled = !$("accept-rules").checked;
$("cancel-start").onclick = () => screen("catalog");
$("start-test").onclick = async () => {
  $("start-test").disabled = true;
  try {try {await document.documentElement.requestFullscreen();} catch {fullscreenUnavailable = true;}
    index = 0; $("question-card").hidden = false; $("finish-test").disabled = false; pending.clear(); away = false; apply(await post(`/quizzes/${chosen.id}/attempts`, {accepted_rules: true})); notice();
  } catch (error) {notice(error.message); $("start-test").disabled = false;}
};
$("previous").onclick = () => {if (index > 0) {index--; renderQuestion();}};
$("next").onclick = () => {if (index < quiz.questions.length - 1) {index++; renderQuestion();}};
$("finish-test").onclick = () => endAttempt();
$("back-to-list").onclick = () => listTests().catch(error => notice(error.message));
$("return-fullscreen").onclick = async () => {try {await document.documentElement.requestFullscreen();} catch {fullscreenUnavailable = true;} returnToExam();};
document.addEventListener("visibilitychange", () => document.hidden ? loseFocus("hidden") : returnToExam());
window.addEventListener("blur", () => loseFocus("blur")); window.addEventListener("focus", returnToExam);
document.addEventListener("fullscreenchange", () => document.fullscreenElement ? returnToExam() : loseFocus("fullscreen_exit"));
window.addEventListener("pagehide", () => loseFocus("pagehide"));
window.addEventListener("beforeunload", event => {if (active?.status === "in_progress") {event.preventDefault(); event.returnValue = "";}});
for (const type of ["copy", "cut", "contextmenu", "dragstart"]) document.addEventListener(type, event => {if (active?.status === "in_progress") event.preventDefault();});
document.addEventListener("keydown", event => {if (active?.status === "in_progress" && (event.ctrlKey || event.metaKey) && ["c", "x", "a", "p", "s"].includes(event.key.toLowerCase())) event.preventDefault();});
setInterval(tick, 1000);
setInterval(async () => {if (active?.status !== "in_progress" || away || saving) return; try {apply(await post(`/attempts/${active.id}/heartbeat`, {attempt_token: accessKey})); flushAnswers();} catch {notice("Нет связи с сервером. Если она не восстановится за 45 секунд, попытка закроется.");}}, 5000);
loadAccount().catch(() => screen("auth"));
