/**
 * Ekteki dosyaların hepsini sırayla indiren fonksiyon.
 * Linkler ekranda gizli olsa bile (.d-none) bu fonksiyon onları bulup tıklar.
 */
function downloadAllFiles(btn) {
    // 1. Butona görsel geri bildirim ver (Loading modu)
    // Kullanıcıya işlemin başladığını hissettiriyoruz
    let originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> İniyor...';
    btn.disabled = true;
    btn.style.opacity = "0.7";

    try {
        // 2. İndirme linklerini kapsayıcıdan bul
        // HTML'de bu container "d-none" ile gizlenmiş olsa bile JS erişebilir.
        let container = btn.closest('.attachment-box').querySelector('.download-container');
        
        if (!container) {
            console.error("İndirme konteyneri bulunamadı.");
            resetButton(btn, originalText);
            return;
        }

        // Gizli linkleri seçiyoruz
        let links = container.querySelectorAll('.download-link');

        // 3. Linkleri sırayla tetikle
        links.forEach((link, index) => {
            setTimeout(() => {
                // Burada sihir gerçekleşiyor: Link görünmez olsa bile tıklanır
                link.click(); 
            }, index * 500); // Her dosya arasında yarım saniye bekle (Tarayıcı engeline takılmamak için)
        });
        
        // 4. İşlem bitince butonu eski haline getir
        // (Toplam süre = dosya sayısı * 500ms + 1 saniye bekleme payı)
        let totalTime = (links.length * 500) + 1000;

        setTimeout(() => {
            btn.innerHTML = '<i class="fas fa-check"></i> Tamamlandı';
            
            // 2 saniye "Tamamlandı" yazısı kalsın, sonra normale dönsün
            setTimeout(() => {
                resetButton(btn, originalText);
            }, 2000);
            
        }, totalTime);

    } catch (e) {
        console.error("İndirme sırasında hata:", e);
        resetButton(btn, originalText);
    }
}

// Butonu eski haline getiren yardımcı fonksiyon
function resetButton(btn, text) {
    btn.innerHTML = text;
    btn.disabled = false;
    btn.style.opacity = "1";
}