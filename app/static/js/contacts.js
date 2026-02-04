document.addEventListener('DOMContentLoaded', function() {
      
    const searchInput = document.getElementById('contactSearch');
    const tabButtons = document.querySelectorAll('#accountTabs button'); // Eğer buton kullanıyorsan
    // NOT: Eğer yeni HTML'de <a> tagi kullandıysan burası çalışmayabilir ama 
    // şimdilik mevcut kodunu bozmuyorum.
    
    const contactCards = document.querySelectorAll('.contact-card-item');
    const noResultsMsg = document.getElementById('noResults');

    let currentFilter = 'all'; 
    let currentSearch = '';    

    // --- SEKME (TAB) DEĞİŞTİRME ---
    if(tabButtons.length > 0) {
        tabButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                tabButtons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                currentFilter = this.getAttribute('data-filter');
                filterContacts();
            });
        });
    }

    // --- ARAMA YAPMA ---
    if(searchInput) {
        searchInput.addEventListener('keyup', function() {
            currentSearch = this.value.toLowerCase().trim();
            filterContacts();
        });
    }

    // --- ANA FİLTRELEME FONKSİYONU ---
    function filterContacts() {
        let visibleCount = 0;

        contactCards.forEach(card => {
            const cardOwner = card.getAttribute('data-owner');
            const cardSearchData = card.getAttribute('data-search');

            // Kural 1: Hesap Filtresi
            const matchesAccount = (currentFilter === 'all') || (cardOwner === currentFilter);

            // Kural 2: Arama Metni
            const matchesSearch = (currentSearch === '') || (cardSearchData.includes(currentSearch));

            if (matchesAccount && matchesSearch) {
                card.style.display = 'block'; 
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        // Sonuç yok mesajı
        if(noResultsMsg) {
            if (visibleCount === 0) {
                noResultsMsg.classList.remove('d-none');
            } else {
                noResultsMsg.classList.add('d-none');
            }
        }
    }
  
    const deleteModal = document.getElementById('deleteModal');
    const deleteForm = document.getElementById('deleteForm');
    const deleteContactIdInput = document.getElementById('deleteContactId');
    const deleteModeInput = document.getElementById('deleteMode');

    // HTML'deki onclick="openDeleteModal(...)" fonksiyonunun çalışması için
    // bu fonksiyonları 'window' nesnesine (global alana) atıyoruz.

    // Modalı AÇ
    window.openDeleteModal = function(contactId) {
        if (!deleteModal) return;
        
        // Silinecek kişinin ID'sini gizli input'a yaz
        if(deleteContactIdInput) deleteContactIdInput.value = contactId;
        
        // Modalı görünür yap
        deleteModal.classList.add('is-open');
    };

    // Modalı KAPAT
    window.closeDeleteModal = function() {
        if (!deleteModal) return;
        deleteModal.classList.remove('is-open');
    };

    // Silme İşlemini ONAYLA ve GÖNDER
    window.confirmDelete = function(mode) {
        // Mode: 'only_contact' veya 'with_history'
        if(deleteModeInput) deleteModeInput.value = mode;
        
        // Formu sunucuya gönder (ui.py karşılayacak)
        if(deleteForm) deleteForm.submit();
    };

    // Modalın dışına (gri alana) tıklanırsa kapat
    window.addEventListener('click', function(event) {
        if (event.target === deleteModal) {
            window.closeDeleteModal();
        }
    });

    window.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            window.closeDeleteModal();
        }
    });

});
