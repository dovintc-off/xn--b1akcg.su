const inputCode = document.getElementById('input-code');
const btnFind = document.getElementById('btn-find');
const errorEl = document.getElementById('code-error');

function showError(message) {
    errorEl.textContent = message;
    btnFind.classList.remove('error-shake');
    void btnFind.offsetWidth;
    btnFind.classList.add('error-shake');
    setTimeout(() => {
        btnFind.classList.remove('error-shake');
    }, 600);
}

function clearError() {
    errorEl.textContent = '';
}

function findGame() {
    const code = inputCode.value.trim();
    clearError();
    if (!/^\d{6}$/.test(code)) {
        showError('Введите 6-значный код игры');
        return;
    }
    window.location.href = `/connect?id=${encodeURIComponent(code)}`;
}

btnFind.addEventListener('click', findGame);

inputCode.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') findGame();
});

inputCode.addEventListener('input', () => {
    inputCode.value = inputCode.value.replace(/\D/g, '').slice(0, 6);
    clearError();
});