const socket = io();
const config = window.DISPLAY_CONFIG || {};
const mainContent = document.getElementById('main-content');
const stateTitle = document.getElementById('state-title');
const stateSubtitle = document.getElementById('state-subtitle');
const qrArea = document.getElementById('qr-area');
const questionArea = document.getElementById('question-area');
const countdown = document.getElementById('countdown');
const leaderboardArea = document.getElementById('leaderboard-area');
const timer = document.getElementById('timer');
const timerFill = document.getElementById('timer-fill');
const timerText = document.getElementById('timer-text');
const playersList = document.getElementById('players-list');
const playerCount = document.getElementById('player-count');
const roomCodeEl = document.getElementById('room-code');
const btnStart = document.getElementById('btn-start');
const menuToggle = document.getElementById('menu-toggle');
const gameMenu = document.getElementById('game-menu');
const btnMenuFinish = document.getElementById('btn-menu-finish');
const btnMenuPause = document.getElementById('btn-menu-pause');
const playersTitle = document.querySelector('.players-title');

let roomCode = config.roomCode || null;
let players = new Map();
let timerFrame = null;
let timerEndsAt = 0;
let timerDuration = 30;
let created = false;

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&':'&amp;',
        '<':'&lt;',
        '>':'&gt;',
        '"':'&quot;',
        "'":'&#039;'
    }[ch]));
}

function parseMedia(text) {
    const media = [];

    const clean = String(text || '')
        .replace(/\{(IMAGE|VIDEO|SOUND|MUSIC):([^}]+)\}/g, (_, type, filename) => {
            media.push({
                type,
                filename
            });

            return '';
        })
        .trim();

    return {
        text: clean,
        media
    };
}

function renderPlayers() {
    const list = [...players.values()].sort(
        (a, b) => (a.joined_at || 0) - (b.joined_at || 0)
    );

    playerCount.textContent = list.length;

    updatePlayerHint();

    playersList.innerHTML = list.map(player => `
        <div class="player-row ${player.answered ? 'answered' : ''} ${player.connected === false ? 'offline' : ''}" data-player-id="${escapeHtml(player.player_id)}">
            <span class="player-name">${escapeHtml(player.nickname)}</span>
        </div>
    `).join('');
}

function setPlayers(list) {
    players.clear();

    (list || []).forEach(player => {
        players.set(player.player_id, player);
    });

    renderPlayers();
}

function showOnly(element) {
    [
        qrArea,
        questionArea,
        countdown,
        leaderboardArea
    ].forEach(el => el.classList.add('hidden'));

    if (element) {
        element.classList.remove('hidden');
    }
}

function generateQRCode(code) {
    if (!code || typeof QRious === 'undefined') {
        return;
    }

    const connectUrl =
        `https://xn--b1akcg.su/connect?id=${encodeURIComponent(code)}`;

    new QRious({
        element: document.getElementById('qr-canvas'),
        value: connectUrl,
        size: 238,
        level: 'H',
        background: '#ffffff',
        foreground: '#4d2675'
    });
}

function setControls(startVisible) {
    btnStart.classList.toggle('hidden', !startVisible);
}

function setTimer(endsAt, duration) {
    cancelAnimationFrame(timerFrame);

    timerEndsAt = Number(endsAt);
    timerDuration = Math.max(1, Number(duration) || 30);

    timer.classList.remove('hidden');

    function frame() {
        const remaining = Math.max(
            0,
            timerEndsAt - Date.now() / 1000
        );

        const percent = Math.max(
            0,
            Math.min(
                100,
                remaining / timerDuration * 100
            )
        );

        timerFill.style.width = `${percent}%`;
        timerText.textContent = `${Math.ceil(remaining)}`;
        timerFill.style.backgroundColor = timerColor(remaining);

        if (remaining > 0) {
            timerFrame = requestAnimationFrame(frame);
        }
    }

    frame();
}

function stopTimer() {
    cancelAnimationFrame(timerFrame);

    timer.classList.add('hidden');
    timerFill.style.width = '0%';
}

function timerColor(seconds) {
    let r;
    let g;
    let b;

    if (seconds >= 20) {
        return 'rgb(46, 204, 113)';
    }

    if (seconds >= 10) {
        const p = (seconds - 10) / 10;

        r = Math.round(
            241 - (241 - 46) * p
        );

        g = Math.round(
            196 + (204 - 196) * p
        );

        b = Math.round(
            15 + (113 - 15) * p
        );

        return `rgb(${r}, ${g}, ${b})`;
    }

    const p = Math.max(
        0,
        seconds / 10
    );

    r = Math.round(
        231 + (241 - 231) * p
    );

    g = Math.round(
        76 + (196 - 76) * p
    );

    b = Math.round(
        60 + (15 - 60) * p
    );

    return `rgb(${r}, ${g}, ${b})`;
}

function showCountdown(value) {
    stopTimer();

    showOnly(countdown);

    stateTitle.textContent = '';
    stateSubtitle.textContent = '';

    countdown.textContent = value;

    setControls(false);
}

function showStagePreview(data) {
    stopTimer();

    menuToggle.classList.remove('hidden');

    showOnly(questionArea);

    const mods =
        Array.isArray(data.modify) && data.modify.length
            ? data.modify
                .map(mod =>
                    mod === 'fastest'
                        ? '⚡ Самый быстрый'
                        : mod
                )
                .join(' · ')
            : 'Без модификаторов';

    questionArea.innerHTML = `
        <div class="stage-label">
            Раунд ${Number(data.stage_index || 0) + 1}
        </div>

        <div class="stage-title">
            ${escapeHtml(data.name || '')}
        </div>

        <div class="stage-meta">
            ${escapeHtml(mods)}
        </div>

        <div class="stage-time">
            ${escapeHtml(data.time_to_answer || 30)} секунд на вопрос
        </div>
    `;

    setControls(false);
}

function showQuestion(data) {
    menuToggle.classList.remove('hidden');

    showOnly(questionArea);

    stateTitle.textContent = '';
    stateSubtitle.textContent = '';

    const parsed = parseMedia(
        data.question.question
    );

    let mediaHtml = '';

    parsed.media.forEach(item => {
        const url =
            `/get_quiz_media/${encodeURIComponent(
                data.quiz_id || config.quizId || ''
            )}/${encodeURIComponent(item.filename)}`;

        if (item.type === 'IMAGE') {
            mediaHtml += `
                <img
                    class="question-media"
                    src="${url}"
                    alt="Медиа"
                >
            `;
        }

        if (item.type === 'VIDEO') {
            mediaHtml += `
                <video
                    class="question-media"
                    src="${url}"
                    controls
                    playsinline
                ></video>
            `;
        }

        if (
            item.type === 'SOUND' ||
            item.type === 'MUSIC'
        ) {
            mediaHtml += `
                <audio
                    class="question-audio"
                    src="${url}"
                    controls
                ></audio>
            `;
        }
    });

    questionArea.innerHTML = `
        <div class="question-text">
            ${escapeHtml(parsed.text)}
        </div>

        ${
            mediaHtml
                ? `<div class="question-media-list">${mediaHtml}</div>`
                : ''
        }
    `;

    setTimer(
        data.ends_at,
        data.duration
    );

    setControls(false);
}

function showQuestionResult(explanation) {
    stopTimer();

    showOnly(leaderboardArea);

    const text = String(
        explanation || ''
    ).trim();

    if (text) {
        leaderboardArea.innerHTML = `
            <div class="question-result">
                <div class="question-result-label">
                    Объяснение
                </div>

                <div class="question-result-text">
                    ${escapeHtml(text)}
                </div>
            </div>
        `;

        return;
    }

    showLeaderboardStart();
}

function showLeaderboardStart() {
    menuToggle.classList.remove('hidden');

    stopTimer();

    showOnly(leaderboardArea);

    leaderboardArea.innerHTML = `
        <div class="leaderboard-label">
            Результаты
        </div>

        <div class="leaderboard-list"></div>
    `;
}

function showLeaderboardPlayer(data) {
    const list =
        leaderboardArea.querySelector(
            '.leaderboard-list'
        );

    if (!list) {
        showLeaderboardStart();
    }

    const target =
        leaderboardArea.querySelector(
            '.leaderboard-list'
        );

    const row =
        document.createElement('div');

    row.className = 'leaderboard-row';

    row.innerHTML = `
        <span class="leaderboard-position">
            #${data.position}
        </span>

        <span class="leaderboard-name">
            ${escapeHtml(data.nickname)}
        </span>

        <span class="leaderboard-score">
            ${data.score} очков
        </span>
    `;

    target.appendChild(row);
}

function showFinal(data) {
    stopTimer();

    showOnly(leaderboardArea);

    const ranking = data.players || [];

    leaderboardArea.innerHTML = `
        <div class="final-title">
            Игра окончена
        </div>

        <div class="final-list"></div>
    `;

    const list =
        leaderboardArea.querySelector(
            '.final-list'
        );

    ranking.forEach((player, index) => {
        const row =
            document.createElement('div');

        row.className =
            'leaderboard-row final-row';

        row.innerHTML = `
            <span class="leaderboard-position">
                #${index + 1}
            </span>

            <span class="leaderboard-name">
                ${escapeHtml(player.nickname)}
            </span>

            <span class="leaderboard-score">
                <span class="score-counter">0</span>
                очков
            </span>
        `;

        list.appendChild(row);

        setTimeout(() => {
            row.classList.add(
                'final-row-visible'
            );

            animateScore(
                row.querySelector(
                    '.score-counter'
                ),
                Number(player.score) || 0
            );
        }, index * 350);
    });

    setControls(false);

    menuToggle.classList.add('hidden');
    gameMenu.classList.add('hidden');
}

function animateScore(element, target) {
    if (!element) {
        return;
    }

    const duration = 700;
    const started = performance.now();

    function frame(now) {
        const progress =
            Math.min(
                1,
                (now - started) / duration
            );

        const eased =
            1 - Math.pow(
                1 - progress,
                3
            );

        element.textContent =
            Math.round(
                target * eased
            );

        if (progress < 1) {
            requestAnimationFrame(frame);
        }
    }

    requestAnimationFrame(frame);
}

function showPaused(
    message = 'Игра остановлена ждем ведущего'
) {
    stopTimer();

    showOnly(questionArea);

    stateTitle.textContent = message;
    stateSubtitle.textContent = '';

    questionArea.innerHTML = '';

    setControls(false);

    menuToggle.classList.remove('hidden');

    btnMenuPause.textContent = 'Продолжить';
}

function updatePlayerHint() {
    const count = players.size;

    if (playersTitle) {
        playersTitle.classList.toggle(
            'insufficient',
            count < 2
        );
    }
}

function reconnectDisplay() {
    if (roomCode) {
        socket.emit(
            'reconnect_display',
            {
                room_code: roomCode
            }
        );
    }
}

socket.on('connect', () => {
    if (
        config.autoCreate &&
        config.quizId &&
        !created
    ) {
        created = true;

        socket.emit(
            'create_game',
            {
                quiz_id: config.quizId
            }
        );
    } else {
        reconnectDisplay();
    }
});

socket.on('game_created', data => {
    roomCode = data.room_code;

    roomCodeEl.textContent =
        roomCode;

    generateQRCode(roomCode);

    setControls(true);

    window.location.href =
        data.redirect_url ||
        `/active_session?id=${encodeURIComponent(roomCode)}`;
});

socket.on('display_reconnected', data => {
    roomCode = data.room_code;

    roomCodeEl.textContent =
        roomCode;

    setPlayers(data.players);

    generateQRCode(roomCode);

    const state = data.state;

    if (state === 'WAITING') {
        stateTitle.textContent =
            'Ожидание игроков';

        stateSubtitle.textContent =
            'Подключите участников по QR-коду';

        showOnly(qrArea);

        menuToggle.classList.add('hidden');
        gameMenu.classList.add('hidden');

        setControls(true);

    } else if (state === 'PAUSED') {
        showPaused();

    } else if (state === 'QUESTION') {
        showQuestion({
            question: data.question,
            quiz_id: data.quiz_id,
            ends_at: data.question_ends_at,
            duration: data.duration || 30
        });

    } else if (state === 'FINAL') {
        showFinal({
            players: data.players
        });
    }
});

socket.on('player_joined', data => {
    players.set(
        data.player_id,
        {
            player_id: data.player_id,
            nickname: data.nickname,
            score: 0,
            answered: false,
            connected: true,
            joined_at: data.joined_at
        }
    );

    renderPlayers();
});

socket.on('player_status', data => {
    const player =
        players.get(data.player_id);

    if (player) {
        player.connected =
            data.connected;

        renderPlayers();
    }
});

socket.on('question_started', data => {
    setPlayers(data.players);

    showQuestion({
        question: data.question,
        quiz_id: data.quiz_id,
        ends_at: data.ends_at,
        duration: data.duration
    });
});

socket.on('player_answered', data => {
    const player =
        players.get(data.player_id);

    if (player) {
        player.answered = true;

        renderPlayers();
    }
});

socket.on('question_finished', data => {
    setPlayers(data.players);

    showQuestionResult(
        data.explanation
    );
});

socket.on('leaderboard_player', data => {
    showLeaderboardPlayer(data);
});

socket.on('final_results', data => {
    showFinal(data);
});

socket.on('countdown', data => {
    showCountdown(data.value);
});

socket.on('error', data => {
    alert(
        data.msg || 'Ошибка'
    );
});

socket.on('need_players', () => {
    if (playersTitle) {
        playersTitle.classList.remove(
            'insufficient'
        );

        void playersTitle.offsetWidth;

        playersTitle.classList.add(
            'insufficient'
        );
    }
});

socket.on('game_paused', data => {
    showPaused(
        data.message ||
        'Игра остановлена ждем ведущего'
    );
});

socket.on('game_resumed', data => {
    btnMenuPause.textContent = 'Пауза';

    gameMenu.classList.add('hidden');

    if (!data) {
        return;
    }

    if (data.state === 'QUESTION') {
        if (!data.question) {
            console.error(
                'game_resumed: QUESTION received without question',
                data
            );

            return;
        }

        showQuestion({
            question: data.question,
            quiz_id:
                data.quiz_id ||
                config.quizId,

            stage_index:
                data.stage_index,

            question_index:
                data.question_index,

            ends_at:
                data.ends_at,

            duration:
                data.duration || 30
        });

    } else if (
        data.state === 'STAGE_PREVIEW' &&
        data.stage
    ) {
        showStagePreview({
            stage_index:
                data.stage_index,

            name:
                data.stage.name,

            modify:
                data.stage.modify,

            time_to_answer:
                data.stage.time_to_answer
        });

    } else if (
        data.state === 'COUNTDOWN'
    ) {
        showCountdown(
            data.value || 3
        );

    } else if (
        data.state === 'QUESTION_RESULT'
    ) {


    } else if (
        data.state === 'LEADERBOARD'
    ) {

    } else if (
        data.state === 'FINAL'
    ) {
        showFinal({
            players:
                data.players || []
        });
    }
});

btnStart.addEventListener(
    'click',
    () => {
        if (!roomCode) {
            return;
        }

        if (players.size < 2) {
            if (playersTitle) {
                playersTitle.classList.remove(
                    'insufficient'
                );

                void playersTitle.offsetWidth;

                playersTitle.classList.add(
                    'insufficient'
                );
            }

            return;
        }

        socket.emit(
            'start_game',
            {
                room_code: roomCode
            }
        );
    }
);

menuToggle.addEventListener(
    'click',
    () => {
        gameMenu.classList.toggle(
            'hidden'
        );
    }
);

btnMenuPause.addEventListener(
    'click',
    () => {
        if (!roomCode) {
            return;
        }

        socket.emit(
            btnMenuPause.textContent === 'Продолжить'
                ? 'resume_game'
                : 'pause_game',
            {
                room_code: roomCode
            }
        );
    }
);

btnMenuFinish.addEventListener(
    'click',
    () => {
        if (roomCode) {
            socket.emit(
                'finish_game',
                {
                    room_code: roomCode
                }
            );
        }

        gameMenu.classList.add('hidden');
    }
);

socket.on('finish_complete', () => {
    gameMenu.classList.add('hidden');
    menuToggle.classList.add('hidden');
});

socket.on('game_finished', data => {
    showFinal(
        data && data.players
            ? data
            : {
                players: [...players.values()]
            }
    );
});