document.addEventListener('DOMContentLoaded', () => {
    const viewMode = document.getElementById('view-mode');
    const editMode = document.getElementById('edit-mode');
    const btnStartEdit = document.getElementById('btn-start-edit');
    const btnSave = document.getElementById('btn-save');
    const btnCancel = document.getElementById('btn-cancel');
    const inputNewName = document.getElementById('new-username-input');
    const currentNameDisplay = document.getElementById('current-username');
    const statusMsg = document.getElementById('status-message');

    btnStartEdit.addEventListener('click', () => {
        viewMode.style.display = 'none';
        editMode.style.display = 'flex';
        inputNewName.value = currentNameDisplay.innerText;
        inputNewName.focus();
        statusMsg.innerText = '';
    });

    btnCancel.addEventListener('click', () => {
        viewMode.style.display = 'flex';
        editMode.style.display = 'none';
        statusMsg.innerText = '';
    });

    btnSave.addEventListener('click', async () => {
        const newName = inputNewName.value.trim();

        if (!newName || newName.length < 3) {
            showStatus("Имя должно быть не короче 3 символов", "error");
            return;
        }

        try {
            const response = await fetch('/api/update-username', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: newName })
            });

            const data = await response.json();

            if (response.ok) {
                currentNameDisplay.innerText = data.new_username;
                
                const headerName = document.getElementById('profileName');
                if (headerName) {
                    headerName.innerText = data.new_username;
                }

                showStatus("Имя успешно изменено!", "success");
                
                setTimeout(() => {
                    viewMode.style.display = 'flex';
                    editMode.style.display = 'none';
                    statusMsg.innerText = '';
                }, 1500);

            } else {
                showStatus(data.error || "Ошибка при сохранении", "error");
            }
        } catch (error) {
            console.error(error);
            showStatus("Ошибка сети", "error");
        }
    });

    function showStatus(text, type) {
        statusMsg.innerText = text;
        statusMsg.className = 'status-msg ' + type;
    }
});