// Disabilita il tasto per evitare doppi invii e mostra un testo di attesa
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('review-form');
    if (form) {
        form.addEventListener('submit', function () {
            const btn = document.getElementById('btn-conferma');
            if (btn) {
                btn.disabled = true;
                btn.innerText = 'Aggiornamento in corso...';
            }
        });
    }

    // Se esiste uno spinner nella pagina, nascondilo dopo un attimo
    const spinner = document.getElementById('spinner');
    if (spinner) {
        spinner.style.display = 'flex';
        setTimeout(() => { spinner.style.display = 'none'; }, 1000);
    }

    // Se in futuro aggiungi un "seleziona tutto"
    const toggleAll = document.getElementById('toggleSelectAll');
    if (toggleAll) {
        toggleAll.addEventListener('change', function () {
            document.querySelectorAll('.row-check,input.form-check-input[type="checkbox"][name="apply_fields"]').forEach(function (c) {
                c.checked = toggleAll.checked;
            });
        });
    }
});
