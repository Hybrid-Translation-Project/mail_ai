document.addEventListener('DOMContentLoaded', function() {
    
    // Elementleri Seçelim
    const searchInput = document.getElementById('contactSearch');
    const tabButtons = document.querySelectorAll('#accountTabs button');
    const contactCards = document.querySelectorAll('.contact-card-item');
    const noResultsMsg = document.getElementById('noResults');

    let currentFilter = 'all'; // Varsayılan sekme: Tümü
    let currentSearch = '';    // Varsayılan arama: Boş

    // --- 1. SEKME (TAB) DEĞİŞTİRME ---
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Aktif sınıfını güncelle
            tabButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // Filtreyi güncelle
            currentFilter = this.getAttribute('data-filter');
            
            // Listeyi Yenile
            filterContacts();
        });
    });

    // --- 2. ARAMA YAPMA ---
    searchInput.addEventListener('keyup', function() {
        currentSearch = this.value.toLowerCase().trim();
        filterContacts();
    });

    // --- 3. ANA FİLTRELEME MANTIĞI ---
    function filterContacts() {
        let visibleCount = 0;

        contactCards.forEach(card => {
            const cardOwner = card.getAttribute('data-owner');
            const cardSearchData = card.getAttribute('data-search');

            // Kural 1: Hesap Filtresi Uyuyor mu?
            // (Eğer sekme 'all' ise YA DA kartın sahibi seçili sekmeye eşitse)
            const matchesAccount = (currentFilter === 'all') || (cardOwner === currentFilter);

            // Kural 2: Arama Metni Uyuyor mu?
            // (Eğer arama boşsa YA DA kartın verisi aranan kelimeyi içeriyorsa)
            const matchesSearch = (currentSearch === '') || (cardSearchData.includes(currentSearch));

            // Karar Anı: İkisi de tutuyorsa göster, yoksa gizle
            if (matchesAccount && matchesSearch) {
                card.style.display = 'block'; // veya 'initial'
                // Animasyonlu görünüm için opacity eklenebilir ama basit tutuyoruz
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        // Hiç sonuç yoksa mesaj göster
        if (visibleCount === 0) {
            noResultsMsg.classList.remove('d-none');
        } else {
            noResultsMsg.classList.add('d-none');
        }
    }

});