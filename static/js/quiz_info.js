document.addEventListener('DOMContentLoaded', function() {
    const quiz = window.currentQuizData;
    const quizId = window.currentQuizId;
    const menu = document.querySelector('.menu');
    const container = document.getElementById('quiz-app');

    if (!container) return;
    
    if (quiz && quizId && menu) {
        const oldPlayBtn = menu.querySelector('.play-btn');
        if (oldPlayBtn) oldPlayBtn.remove();

        const playBtn = document.createElement('button');
        playBtn.className = 'play-btn';
        playBtn.type = 'button';
        playBtn.textContent = 'Играть';

        playBtn.onclick = async function() {
            try {
                const res = await fetch('/api/check-session');
                if (!res.ok) throw new Error("Network error");
                const data = await res.json();
                
                if (data.logged_in) {
                    window.location.href = `/display?new_room=${encodeURIComponent(quizId)}`;
                } else {
                    const modal = document.getElementById('loginRequiredModal');
                    if (modal) modal.style.display = 'flex';
                }
            } catch (e) {
                console.error("Session check failed:", e);
                alert("Не удалось проверить статус входа.");
            }
        };

        const loginLink = document.getElementById('openLoginBtn');
        if (loginLink) menu.insertBefore(playBtn, loginLink);
        else menu.appendChild(playBtn);
    }

    const reqModal = document.getElementById('loginRequiredModal');
    const goToLoginBtn = document.getElementById('goToLoginBtn');
    const closeReqBtn = document.getElementById('closeLoginReqBtn');

    if (reqModal) reqModal.addEventListener('click', (e) => { if (e.target === reqModal) reqModal.style.display = 'none'; });
    if (goToLoginBtn) goToLoginBtn.addEventListener('click', () => {
        reqModal.style.display = 'none';
        const mainLoginTrigger = document.getElementById('openLoginBtn');
        if (mainLoginTrigger) mainLoginTrigger.click();
        else window.location.href = '/home';
    });
    if (closeReqBtn) closeReqBtn.addEventListener('click', () => { reqModal.style.display = 'none'; });

    if (!quiz || !quizId) {
        init404Effect();
        const navLogo = document.getElementById('nav-logo');
        if (navLogo) navLogo.innerHTML = `<a href="/home" class="logo">Главная</a> / Не найдено`;
        return;
    }

    function escapeHtml(value) {
        if (!value) return '';
        return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function renderDescription() {
        container.innerHTML = `
            <section class="quiz-description-page">
                <div class="quiz-description-card">
                    <div class="quiz-description-image-wrap">
                        <img src="${escapeHtml(quiz.PreviewImagePath || '')}" alt="" class="quiz-description-image" onerror="this.parentElement.style.display='none';">
                    </div>
                    <div class="quiz-description-content">
                        <h1>${escapeHtml(quiz.Name || 'Без названия')}</h1>
                        <p>${escapeHtml(quiz.Description || 'Описание отсутствует.')}</p>
                    </div>
                </div>
            </section>`;
    }

    function initQuiz() {
        const navLogo = document.getElementById('nav-logo');
        if (navLogo && quiz.Name) {
            navLogo.innerHTML = `<a href="/home" class="logo">Главная</a> / ${escapeHtml(quiz.Name)}`;
        }
        renderDescription();
    }

    function init404Effect() {
        container.innerHTML = `<div class="error-overlay"><canvas id="dot-canvas"></canvas><div class="error-404-container"><h1 class="error-404-text">404</h1><p class="error-404-subtext">Квиз не найден</p></div></div>`;
        const canvas = document.getElementById('dot-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let width, height, dots = [];
        const gridSize = 20, interactionRadius = gridSize * 5, baseRadius = 1, maxRadius = baseRadius * 3.25;
        const mouse = { x: -9999, y: -9999 };
        class Dot {
            constructor(x, y) { this.originX = x; this.originY = y; this.currentRadius = baseRadius; this.targetRadius = baseRadius; this.baseOpacity = 0.15; this.currentOpacity = this.baseOpacity; this.targetOpacity = this.baseOpacity; }
            update() {
                const dx = mouse.x - this.originX, dy = mouse.y - this.originY, dist = Math.sqrt(dx*dx + dy*dy);
                if (dist < interactionRadius) { const f = 1 - dist/interactionRadius; this.targetRadius = baseRadius + (maxRadius-baseRadius)*f; this.targetOpacity = this.baseOpacity + (0.85-this.baseOpacity)*f; } 
                else { this.targetRadius = baseRadius; this.targetOpacity = this.baseOpacity; }
                this.currentRadius += (this.targetRadius - this.currentRadius) * 0.12;
                this.currentOpacity += (this.targetOpacity - this.currentOpacity) * 0.12;
            }
            draw() { ctx.beginPath(); ctx.arc(this.originX, this.originY, this.currentRadius, 0, Math.PI*2); ctx.fillStyle = `rgba(60,60,60,${this.currentOpacity})`; ctx.fill(); }
        }
        function initGrid() { width = canvas.width = window.innerWidth; height = canvas.height = window.innerHeight; dots = []; for(let x=0; x<width; x+=gridSize) for(let y=0; y<height; y+=gridSize) dots.push(new Dot(x+gridSize/2, y+gridSize/2)); }
        function animate() { ctx.clearRect(0,0,width,height); for(let i=0; i<dots.length; i++) { dots[i].update(); dots[i].draw(); } requestAnimationFrame(animate); }
        window.addEventListener('mousemove', e => { const r = canvas.getBoundingClientRect(); mouse.x = e.clientX-r.left; mouse.y = e.clientY-r.top; });
        window.addEventListener('mouseleave', () => { mouse.x = -9999; mouse.y = -9999; });
        window.addEventListener('resize', initGrid);
        initGrid(); animate();
    }

    initQuiz();
});