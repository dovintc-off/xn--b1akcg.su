document.addEventListener('DOMContentLoaded', async function() {
    try {
        const res = await fetch('/api/check-session');
        if (res.ok) {
            const data = await res.json();
            if (data.logged_in) {
                const openBtn = document.getElementById('openLoginBtn');
                const userProfile = document.getElementById('userProfile');
                const profileName = document.getElementById('profileName');
                const profileId = document.getElementById('profileId');
                
                if (openBtn) openBtn.style.display = 'none';
                if (userProfile) {
                    userProfile.style.display = 'flex';
                    
                    userProfile.style.cursor = 'pointer';
                    userProfile.onclick = () => {
                        window.location.href = '/profile';
                    };
                }
                
                if (profileName) profileName.innerText = data.username;
                if (profileId) profileId.innerText = `ID: ${data.user_id}`;
            }
        }
    } catch (e) {
        console.error("Ошибка проверки сессии:", e);
    }

    const modal = document.getElementById('loginModal');
    const stepEmail = document.getElementById('step-email');
    const stepCode = document.getElementById('step-code');
    
    const emailInput = document.getElementById('emailInput');
    const getCodeBtn = document.getElementById('getCodeBtn');
    const displayEmail = document.getElementById('displayEmail');
    const changeEmailLink = document.getElementById('changeEmailLink');
    const verifyBtn = document.getElementById('verifyBtn');
    const codeBoxes = document.querySelectorAll('.code-box');
    
    let currentEmail = "";
    const STORAGE_KEY = "quizix_login_pending_email";
    
    function saveLoginState(email) { localStorage.setItem(STORAGE_KEY, email); }
    function loadLoginState() { return localStorage.getItem(STORAGE_KEY); }
    function clearLoginState() { localStorage.removeItem(STORAGE_KEY); }

    function showStep(step) {
        if (step === 'code') {
            stepEmail.style.display = 'none';
            stepCode.style.display = 'block';
            setTimeout(() => codeBoxes[0].focus(), 100);
        } else {
            stepCode.style.display = 'none';
            stepEmail.style.display = 'block';
            emailInput.focus();
        }
    }

    document.getElementById('openLoginBtn').onclick = () => {
        const savedEmail = loadLoginState();
        if (savedEmail) {
            currentEmail = savedEmail;
            displayEmail.innerText = currentEmail;
            modal.style.display = 'flex';
            showStep('code');
        } else {
            resetModal();
            modal.style.display = 'flex';
        }
    };

    document.getElementById('closeLoginBtn').onclick = () => modal.style.display = 'none';
    window.onclick = (e) => { if(e.target === modal) modal.style.display = 'none'; };

    function resetModal() {
        currentEmail = "";
        emailInput.value = '';
        codeBoxes.forEach(box => box.value = '');
        getCodeBtn.disabled = false;
        getCodeBtn.innerText = "Получить код";
        showStep('email');
    }

    getCodeBtn.onclick = async function() {
        const email = emailInput.value.trim();
        if (!email || !email.includes('@')) {
            alert("Пожалуйста, введите корректный email.");
            return;
        }
        getCodeBtn.disabled = true;
        getCodeBtn.innerText = "Отправка...";
        try {
            const response = await fetch('/api/send-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: email })
            });
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || "Ошибка отправки");
            }
            currentEmail = email;
            saveLoginState(email); 
            displayEmail.innerText = email;
            showStep('code');
        } catch (err) {
            alert("Не удалось отправить код: " + err.message);
        } finally {
            getCodeBtn.disabled = false;
            getCodeBtn.innerText = "Получить код";
        }
    };

    changeEmailLink.onclick = (e) => {
        e.preventDefault();
        clearLoginState();
        resetModal();
    };

    codeBoxes.forEach((box, index) => {
        box.oninput = function() {
            this.value = this.value.replace(/[^0-9]/g, '');
            if (this.value && index < codeBoxes.length - 1) codeBoxes[index + 1].focus();
        };
        box.onkeydown = function(e) {
            if (e.key === 'Backspace' && !this.value && index > 0) codeBoxes[index - 1].focus();
        };
        box.onpaste = function(e) {
            e.preventDefault();
            const pasteData = e.clipboardData.getData('text').trim();
            if (/^\d{6}$/.test(pasteData)) {
                pasteData.split('').forEach((char, i) => { if(codeBoxes[i]) codeBoxes[i].value = char; });
                codeBoxes[5].focus();
            }
        };
    });

    verifyBtn.onclick = async function() {
        let fullCode = '';
        codeBoxes.forEach(box => fullCode += box.value);
        if (fullCode.length !== 6) {
            alert("Введите все 6 цифр кода.");
            return;
        }
        verifyBtn.innerText = "Проверка...";
        verifyBtn.disabled = true;
        try {
            const response = await fetch('/api/verify-code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: currentEmail, code: fullCode })
            });
            const data = await response.json();
            if (response.ok) {
                document.getElementById('profileName').innerText = data.username;
                document.getElementById('profileId').innerText = `ID: ${data.user_id}`;
                document.getElementById('openLoginBtn').style.display = 'none';
                document.getElementById('userProfile').style.display = 'flex';
                clearLoginState();
                modal.style.display = 'none';
            } else {
                alert("Ошибка: " + (data.error || "Неверный код"));
                codeBoxes.forEach(b => b.value = '');
                codeBoxes[0].focus();
            }
        } catch (err) {
            alert("Ошибка соединения с сервером.");
        } finally {
            verifyBtn.innerText = "Войти";
            verifyBtn.disabled = false;
        }
    };

    async function loadQuizzes() {
        const grid = document.getElementById('quizzes-grid');
        if (!grid) return;

        try {
            const response = await fetch('/api/quizzes?param=ids&ids_first=1&ids_end=10');
            if (!response.ok) throw new Error(`Ошибка сервера: ${response.status}`);
            
            const quizzes = await response.json();
            grid.innerHTML = '';

            if (quizzes.length === 0) {
                grid.innerHTML = '<p style="color:#aaa; grid-column: 1/-1; text-align:center;">Квизы пока не добавлены.</p>';
                return;
            }

            quizzes.forEach(quiz => {
                if (!Array.isArray(quiz) || quiz.length < 3) return;
                const [id, name, imagePath] = quiz;
                const safeName = name || "Без названия";

                const safeImage = imagePath ? `/quiz-images/${id}/${imagePath.replace(/^\//, '')}` : '/static/images/placeholder.png';

                const card = document.createElement('div');
                card.className = 'quiz-card';
                
                card.innerHTML = `
                    <img src="${safeImage}" 
                         alt="${safeName}" 
                         class="quiz-image" 
                         loading="lazy"
                         onerror="this.onerror=null; this.src='/static/images/placeholder.png';">
                    <div class="quiz-info">
                        <h3 class="quiz-title">${safeName}</h3>
                        <button class="quiz-play-btn" onclick="window.location.href='/quiz?id=${id}'">Играть</button>
                    </div>
                `;
                
                card.addEventListener('click', (e) => {
                    if(e.target.tagName !== 'BUTTON') startQuiz(id);
                });
                grid.appendChild(card);
            });
        } catch (error) {
            console.error('Ошибка загрузки квизов:', error);
            grid.innerHTML = `<p style="color:red; text-align:center;">Ошибка: ${error.message}</p>`;
        }
    }

    function setupFooter() {
        const privacyLink = document.getElementById('privacy-link');
        if (!privacyLink) return;

        const userLang = getUserLanguage();
        privacyLink.href = `/privacy_policy?l=${userLang}`;
        
        if (userLang === 'ru') {
            privacyLink.innerText = 'Политика конфиденциальности';
        } else {
            privacyLink.innerText = 'Privacy Policy';
        }
    }

    function initCookieBanner() {
        const banner = document.getElementById('cookie-banner');
        const acceptBtn = document.getElementById('accept-cookies');
        const declineBtn = document.getElementById('decline-cookies');

        if (!banner || !acceptBtn || !declineBtn) return;

        if (localStorage.getItem('cookiesAccepted')) {
            banner.style.display = 'none';
            return;
        }

        banner.style.display = 'flex';

        acceptBtn.onclick = () => {
            localStorage.setItem('cookiesAccepted', 'true');
            banner.style.display = 'none';
        };

        declineBtn.onclick = () => {
            localStorage.setItem('cookiesAccepted', 'false');
            banner.style.display = 'none';
            console.log("Cookie отклонены");
        };
    }

    function getUserLanguage() {
        const lang = navigator.language || navigator.userLanguage; 
        return lang ? lang.substring(0, 2).toLowerCase() : 'en';
    }

    loadQuizzes();
    setupFooter();
    initCookieBanner();
});

function startQuiz(id) {
    console.log("Запуск квиза ID:", id);
    window.location.href = `/quiz?id=${id}`;
}