document.addEventListener('DOMContentLoaded', function() {
      
    const searchInput = document.getElementById('contactSearch');
    const contactCards = document.querySelectorAll('.contact-card-item');
    const noResultsMsg = document.getElementById('noResults');

    let currentSearch = '';    

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
            const cardSearchData = card.getAttribute('data-search');

            // Arama Metni Eşleşme Kontrolü
            const matchesSearch = (currentSearch === '') || (cardSearchData.includes(currentSearch));

            if (matchesSearch) {
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
  
    // --- MODAL YÖNETİMİ ---
    const deleteModal = document.getElementById('deleteModal');
    const deleteForm = document.getElementById('deleteForm');
    const deleteContactIdInput = document.getElementById('deleteContactId');
    const deleteModeInput = document.getElementById('deleteMode');

    // Modalı AÇ
    window.openDeleteModal = function(contactId) {
        if (!deleteModal) return;
        if(deleteContactIdInput) deleteContactIdInput.value = contactId;
        deleteModal.style.display = 'flex';
    };

    // Modalı KAPAT
    window.closeDeleteModal = function() {
        if (!deleteModal) return;
        deleteModal.style.display = 'none';
    };

    // Silme İşlemini ONAYLA ve GÖNDER
    window.confirmDelete = function(mode) {
        if(deleteModeInput) deleteModeInput.value = mode;
        if(deleteForm) deleteForm.submit();
    };

    // Modalın dışına tıklanırsa kapat
    window.onclick = function(event) {
        if (event.target == deleteModal) {
            window.closeDeleteModal();
        }
    };

    // --- 🚀 YENİ: AI HATIRLATICI ENTEGRASYONU ---
    /**
     * Mail içeriğini analiz eder ve gerekirse hatırlatıcı önerir.
     * Bu fonksiyonu bir mail görüntülendiğinde tetikleyebilirsin.
     */
    window.checkAiReminder = async function(mailContent) {
        if (!mailContent || mailContent.length < 5) return;

        try {
            const response = await fetch('/api/ai/analyze-reminder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: mailContent })
            });

            const data = await response.json();

            if (data.success) {
                // Kullanıcıya şık bir onay kutusu gösteriyoruz
                if (confirm(data.suggestion)) {
                    // Hatırlatıcı kurulduğunda yapılacaklar (örn: bir toast bildirimi)
                    alert("Hatırlatıcı Kaydedildi: " + data.task);
                    console.log("AI Task Created:", data.task);
                }
            }
        } catch (error) {
            console.error("AI Analiz hatası:", error);
        }
    };

});