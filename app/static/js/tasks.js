document.addEventListener('DOMContentLoaded', function() {
    
    // --- ELEMENTLER ---
    const tabButtons = document.querySelectorAll('#accountTabs button');
    
    const pendingItems = document.querySelectorAll('.task-item-pending');
    const noPendingMsg = document.getElementById('noPendingMsg');
    
    const confirmedItems = document.querySelectorAll('.task-item-confirmed');
    const noConfirmedMsg = document.getElementById('noConfirmedMsg');

    // --- SEKME TIKLAMA OLAYI ---
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // 1. Butonların görselini güncelle
            tabButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // 2. Seçili filtreyi al (all veya email)
            const filterValue = this.getAttribute('data-filter');

            // 3. Listeleri Filtrele
            filterList(pendingItems, noPendingMsg, filterValue);
            filterList(confirmedItems, noConfirmedMsg, filterValue, true); // true = tablo satırı
        });
    });

    // --- FİLTRELEME FONKSİYONU ---
    function filterList(items, msgElement, filter, isTable = false) {
        let visibleCount = 0;

        items.forEach(item => {
            const owner = item.getAttribute('data-owner');
            
            if (filter === 'all' || owner === filter) {
                // Eğer tablo satırıysa 'table-row', değilse 'flex' veya 'block' yap
                item.style.display = isTable ? 'table-row' : ''; 
                // Not: '' bırakmak CSS'teki default (flex/block) değerine döndürür.
                visibleCount++;
            } else {
                item.style.display = 'none';
            }
        });

        // Hiç eleman kalmadıysa mesajı göster
        if (visibleCount === 0) {
            msgElement.classList.remove('d-none');
        } else {
            msgElement.classList.add('d-none');
        }
    }
});