const VIEW_MODE = "{{ view_mode }}";
let selectedIds = new Set();

document.addEventListener('DOMContentLoaded', () => {
    setupSearch();
    setupBulkActions();
    setupLoadMore();
});

function setupSearch() {
    const input = document.getElementById('searchInput');
    const filterSelect = document.getElementById('filterSelect');
    if (!input) return;

    const performSearch = () => {
        const term = input.value.toLowerCase().trim();
        const filterKey = filterSelect ? filterSelect.value : null;
        const rows = document.querySelectorAll('#tableBody tr[data-id]');
        
        rows.forEach(row => {
            let match = false;
            if (!term) match = true;
            else if (filterKey) {
                const cell = row.querySelector(`[data-field="${filterKey}"]`);
                if (cell && cell.textContent.toLowerCase().includes(term)) match = true;
            } else {
                if (row.textContent.toLowerCase().includes(term)) match = true;
            }
            row.style.display = match ? '' : 'none';
        });
    };

    input.addEventListener('input', performSearch);
    if (filterSelect) filterSelect.addEventListener('change', performSearch);
}

function setupBulkActions() {
    const selectAll = document.getElementById('selectAll');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    
    const updateBulkButton = () => {
        if (selectedIds.size > 0 && bulkDeleteBtn) {
            bulkDeleteBtn.classList.add('visible');
            bulkDeleteBtn.innerHTML = `Удалить (${selectedIds.size})`;
        } else if (bulkDeleteBtn) {
            bulkDeleteBtn.classList.remove('visible');
        }
    };

    document.addEventListener('change', (e) => {
        if (e.target.classList.contains('row-checkbox')) {
            const id = e.target.value;
            if (e.target.checked) selectedIds.add(id);
            else selectedIds.delete(id);
            updateBulkButton();
        }
    });

    if (selectAll) {
        selectAll.onchange = (e) => {
            const isChecked = e.target.checked;
            document.querySelectorAll('.row-checkbox').forEach(cb => {
                cb.checked = isChecked;
                const id = cb.value;
                if (isChecked) selectedIds.add(id);
                else selectedIds.delete(id);
            });
            updateBulkButton();
        };
    }

    if (bulkDeleteBtn) {
        bulkDeleteBtn.onclick = async () => {
            if (!confirm(`Удалить ${selectedIds.size} записей?`)) return;
            try {
                const endpoint = VIEW_MODE === 'codes' ? '/api/delete-codes' : '/api/delete-rooms-bulk';
                const payload = VIEW_MODE === 'codes' 
                    ? { mode: 'selected', ids: [...selectedIds] }
                    : { ids: [...selectedIds] };

                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if (res.ok) location.reload();
                else alert("Ошибка при удалении");
            } catch (err) { alert("Ошибка соединения"); }
        };
    }
}

async function changeRole(userId, newRole) {
    try {
        const res = await fetch('/api/update-user-role', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: userId, role: newRole })
        });
        if (!res.ok) throw new Error('Server error');
    } catch (err) { alert("Не удалось обновить права"); location.reload(); }
}

async function deleteRoom(code) {
    if (!confirm(`Удалить комнату ${code}?`)) return;
    try {
        const res = await fetch('/api/delete-room', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ code: code })
        });
        if (res.ok) location.reload();
        else alert("Ошибка удаления");
    } catch (err) { alert("Ошибка соединения"); }
}

function setupLoadMore() {
    const btn = document.getElementById('loadMoreBtn');
    if (btn) {
        btn.onclick = function() {
            this.disabled = true;
            this.innerText = "Загрузка...";
            setTimeout(() => { this.innerText = "Больше нет данных"; }, 600);
        };
    }
}

// Автоперезагрузка при смене лимита логов
document.getElementById('logLimitSelect')?.addEventListener('change', function() {
    const url = new URL(window.location);
    url.searchParams.set('log_limit', this.value);
    window.location.href = url.toString();
});