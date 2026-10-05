const socket = io();
const config = window.CONNECT_CONFIG || {};
const stepNick = document.getElementById('step-nick');
const stepWaiting = document.getElementById('step-waiting');
const stepGame = document.getElementById('step-game');
const inputNick = document.getElementById('input-nick');
const btnJoin = document.getElementById('btn-join');
const errorEl = document.getElementById('nick-error');
const phoneStage = document.getElementById('phone-stage');
const roomCode = config.roomCode;
let playerId = getCookie('qweezxr_player_id');
let currentQuestion = null;
let answerLocked = false;
let timerFrame = null;

function getCookie(name) {
    const value = document.cookie.split('; ').find(row => row.startsWith(`${name}=`));
    return value ? decodeURIComponent(value.split('=').slice(1).join('=')) : null;
}
function setCookie(name, value, maxAge) {
    document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${maxAge}; Path=/; SameSite=Lax`;
}
function createPlayerId() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}
function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'
    }[ch]));
}
function showStep(step) {
    [stepNick, stepWaiting, stepGame].forEach(el => {
        if (!el) return;
        el.classList.toggle('hidden-step', el !== step);
        el.classList.toggle('active-step', el === step);
    });
}
function showError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    if (btnJoin) {
        btnJoin.classList.remove('error-shake');
        void btnJoin.offsetWidth;
        btnJoin.classList.add('error-shake');
    }
}
function ensurePlayerId() {
    if (!playerId) {
        playerId = createPlayerId();
        setCookie('qweezxr_player_id', playerId, 60 * 60 * 24 * 365);
    }
}
function parseMedia(text) {
    const media = [];
    const clean = String(text || '').replace(/\{(IMAGE|VIDEO|SOUND|MUSIC):([^}]+)\}/g, (_, type, filename) => {
        media.push({type, filename});
        return '';
    }).trim();
    return {text: clean, media};
}
function renderQuestion(data) {
    if (!phoneStage) return;
    currentQuestion = data.question;
    answerLocked = false;
    const parsed = parseMedia(data.question.question);
    let mediaHtml = '';
    parsed.media.forEach(item => {
        const url = `/get_quiz_media/${encodeURIComponent(data.quiz_id || window.CONNECT_CONFIG.quizId || '')}/${encodeURIComponent(item.filename)}`;
        if (item.type === 'IMAGE') mediaHtml += `<img class="phone-media" src="${url}" alt="Медиа">`;
        if (item.type === 'VIDEO') mediaHtml += `<video class="phone-media" src="${url}" controls playsinline></video>`;
        if (item.type === 'SOUND' || item.type === 'MUSIC') mediaHtml += `<audio class="phone-audio" src="${url}" controls></audio>`;
    });
    const options = Array.isArray(data.question.question_options) ? data.question.question_options : [];
    phoneStage.innerHTML = `
        <div class="phone-question">${escapeHtml(parsed.text)}</div>
        ${mediaHtml ? `<div class="phone-media-list">${mediaHtml}</div>` : ''}
        <div class="phone-options">
            ${options.map((option, index) => `<button class="phone-answer" type="button" data-answer="${escapeHtml(option)}">${escapeHtml(option)}</button>`).join('')}
        </div>
        <div class="phone-timer"><div id="phone-timer-fill"></div><span id="phone-timer-text"></span></div>
    `;
    phoneStage.querySelectorAll('.phone-answer').forEach(button => {
        button.addEventListener('click', () => submitAnswer(button.dataset.answer, button));
    });
    startPhoneTimer(data.ends_at, data.duration);
}
function startPhoneTimer(endsAt, duration) {
    cancelAnimationFrame(timerFrame);
    const fill = document.getElementById('phone-timer-fill');
    const text = document.getElementById('phone-timer-text');
    function frame() {
        const remaining = Math.max(0, endsAt - Date.now() / 1000);
        const percent = Math.max(0, Math.min(100, remaining / duration * 100));
        if (fill) fill.style.width = `${percent}%`;
        if (text) text.textContent = `${Math.ceil(remaining)} сек`;
        if (remaining > 0 && !answerLocked) timerFrame = requestAnimationFrame(frame);
    }
    frame();
}
function submitAnswer(answer, button) {
    if (answerLocked) return;
    answerLocked = true;
    document.querySelectorAll('.phone-answer').forEach(btn => btn.disabled = true);
    button.classList.add('selected');
    socket.emit('submit_answer', {room_code: roomCode, player_id: playerId, answer});
}
function showPaused(text = 'Игра остановлена ждем ведущего') {
    cancelAnimationFrame(timerFrame);
    answerLocked = true;
    if (!phoneStage) return;
    phoneStage.innerHTML = `<div class="phone-waiting"><div class="phone-waiting-title">⏸</div><div>${escapeHtml(text)}</div></div>`;
}
function showWaiting(text = 'Ждём остальных участников…') {
    cancelAnimationFrame(timerFrame);
    if (!phoneStage) return;
    phoneStage.innerHTML = `
        <div class="phone-waiting">
            <div class="phone-waiting-title">⏳</div>
            <div>${escapeHtml(text)}</div>
            <div class="loader-dots"><span></span><span></span><span></span></div>
        </div>
    `;
}
function showResult(result) {
    cancelAnimationFrame(timerFrame);

    const correct = !!result.correct;

    phoneStage.innerHTML = `
        <div class="phone-answer-result ${correct ? 'result-correct' : 'result-incorrect'}">
            ${correct ? 'ПРАВИЛЬНО' : 'НЕПРАВИЛЬНО'}
        </div>
    `;

    setTimeout(() => showWaiting(), 2000);
}
function showFinal(data) {
    cancelAnimationFrame(timerFrame);
    if (!phoneStage) return;
    phoneStage.innerHTML = `
        <div class="phone-result final-result">
            <div class="result-icon">🏆</div>
            <div class="result-title">Игра окончена</div>
            <div class="result-points">${escapeHtml(data.score ?? 0)} очков</div>
            <div class="result-correct">Спасибо за игру!</div>
        </div>
    `;
}
function connectPlayer() {
    ensurePlayerId();
    if (!roomCode) return;
    socket.emit('reconnect_player', {room_code: roomCode, player_id: playerId});
}
if (config.roomExists && btnJoin) {
    ensurePlayerId();
    btnJoin.addEventListener('click', () => {
        const nickname = inputNick.value.trim();
        if (!nickname) {
            showError('Введите никнейм');
            return;
        }
        btnJoin.disabled = true;
        btnJoin.textContent = 'Подключение...';
        socket.emit('join_game', {code: roomCode, nickname, player_id: playerId});
    });
    inputNick.addEventListener('keydown', event => {
        if (event.key === 'Enter') btnJoin.click();
    });
}
socket.on('connect', () => {
    if (config.roomExists && playerId) connectPlayer();
});
socket.on('joined_success', () => {
    showStep(stepWaiting);
});
socket.on('reconnected', () => {
    showStep(stepWaiting);
});
socket.on('game_state', data => {
    if (data.state === 'PAUSED') {
        showStep(stepGame);
        showPaused();
        return;
    }
    if (data.state === 'QUESTION' && !data.already_answered) {
        showStep(stepGame);
        renderQuestion({question:data.question, quiz_id:data.quiz_id, ends_at:data.ends_at, duration:data.duration || 30});
        return;
    }
    if (data.state === 'FINAL') {
        showStep(stepGame);
        showFinal(data);
        return;
    }
    if (data.state === 'QUESTION_RESULT' && data.last_result) {
        showStep(stepGame);
        showResult(data.last_result);
        return;
    }
    showStep(stepWaiting);
});
socket.on('question', data => {
    showStep(stepGame);
    renderQuestion(data);
});
socket.on('game_paused', data => {
    showStep(stepGame);
    showPaused(data.message || 'Игра остановлена ждем ведущего');
});
socket.on('game_resumed', data => {
    if (data.state === 'QUESTION' && data.question && data.ends_at) {
        showStep(stepGame);
        if (data.already_answered) {
            answerLocked = true;
            showWaiting('Ответ принят. Ждём остальных участников…');
            return;
        }
        answerLocked = false;
        renderQuestion({question:data.question, quiz_id:data.quiz_id, ends_at:data.ends_at, duration:data.duration || 30});
    }
});
socket.on('final_results', data => {
    showStep(stepGame);
    showFinal(data);
});
socket.on('answer_accepted', () => {
    showWaiting('Ответ принят. Ждём остальных участников…');
});
socket.on('answer_result', result => {
    showStep(stepGame);
    showResult(result);
});
socket.on('game_finished', () => {
    showStep(stepWaiting);
    if (phoneStage) phoneStage.innerHTML = '<div class="phone-result"><div class="result-title">Игра завершена</div></div>';
});
socket.on('answer_error', data => {
    answerLocked = false;
    document.querySelectorAll('.phone-answer').forEach(btn => btn.disabled = false);
    showError(data.msg || 'Не удалось отправить ответ');
});
socket.on('error', data => {
    if (btnJoin) {
        btnJoin.disabled = false;
        btnJoin.textContent = 'Войти';
    }
    showError(data.msg || 'Ошибка подключения');
});
socket.on('player_game_not_found', data => {
    showError(data.msg || 'Игра не найдена');
});
