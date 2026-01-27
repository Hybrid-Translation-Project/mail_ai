/**
 * ESKİ FONKSİYON: İstemci Taraflı Basit Filtreleme
 * (Rehber, Görevler gibi sayfalardaki tabloları anlık filtrelemek için kullanılır)
 */
function enableDynamicSearch(inputId, listContainerId, itemSelector) {
    const searchInput = document.getElementById(inputId);
    const listContainer = document.getElementById(listContainerId);

    if (!searchInput || !listContainer) return;

    searchInput.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const items = listContainer.querySelectorAll(itemSelector);

        items.forEach(item => {
            // data-search niteliği veya elementin metin içeriği üzerinden arama yapar
            const text = item.innerText.toLowerCase();
            const searchData = item.getAttribute('data-search') ? item.getAttribute('data-search').toLowerCase() : "";
            
            if (text.includes(searchTerm) || searchData.includes(searchTerm)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

/**
 * YENİ EKLENEN: AI Tabanlı Semantik Arama (Backend API)
 * (Dashboard sayfasındaki akıllı arama kutusu için)
 */
document.addEventListener('DOMContentLoaded', () => {
    // Dashboard.html'deki elementleri seçelim
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    
    // Görünüm değiştirmek için kapsayıcılar
    const defaultView = document.getElementById('default-view');
    const searchView = document.getElementById('search-view');
    const resultsContainer = document.getElementById('searchResultsContainer');

    // Eğer bu sayfada (örneğin Ayarlar sayfasında) arama kutusu yoksa, kod çalışmasın.
    if (!searchInput || !searchBtn) return;

    // --- OLAY DİNLEYİCİLERİ (Event Listeners) ---

    // 1. Arama Butonuna Tıklama
    searchBtn.addEventListener('click', performSearch);
    
    // 2. Enter Tuşuna Basma
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    // 3. Arama Kapatma / Temizleme Butonu
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', () => {
            searchInput.value = '';
            toggleView(false); // Varsayılan görünüme dön
        });
    }

    /**
     * Backend'e istek atıp sonuçları getiren ana fonksiyon
     */
    async function performSearch() {
        const query = searchInput.value.trim();
        
        // Boş arama yapılmasını engelle
        if (query.length < 2) {
            // Basit bir sarsılma efekti veya uyarı verilebilir
            searchInput.style.borderColor = 'red';
            setTimeout(() => searchInput.style.borderColor = '#333', 1000);
            return;
        }

        // UX: Butonu "Aranıyor..." moduna al
        const originalBtnText = searchBtn.innerHTML;
        searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; // Dönme ikonu varsa
        searchBtn.disabled = true;

        try {
            // Backend API'ye GET isteği at
            // encodeURIComponent: URL içinde özel karakter sorununu çözer
            const response = await fetch(`/ui/search-api?q=${encodeURIComponent(query)}`);
            
            if (!response.ok) throw new Error("API Hatası");

            const data = await response.json();

            // Gelen veriyi ekrana bas
            renderResults(data.results);
            
            // Arama ekranını aç
            toggleView(true);

        } catch (error) {
            console.error("Arama hatası:", error);
            alert("Arama sırasında bir bağlantı hatası oluştu.");
        } finally {
            // İşlem bitince butonu eski haline getir
            searchBtn.innerHTML = originalBtnText;
            searchBtn.disabled = false;
        }
    }

    /**
     * Gelen sonuçları HTML kartlarına çevirip ekrana basar
     */
    function renderResults(results) {
        resultsContainer.innerHTML = ''; // Önceki sonuçları temizle

        // Sonuç yoksa
        if (!results || results.length === 0) {
            resultsContainer.innerHTML = `
                <div style="text-align: center; padding: 60px; color: #666;">
                    <div style="font-size: 3rem; margin-bottom: 10px;">🤷‍♂️</div>
                    <h3 style="color: #fff;">Sonuç Bulunamadı</h3>
                    <p>Farklı kelimelerle aramayı deneyebilirsin.</p>
                </div>`;
            return;
        }

        // Sonuçları döngüye al
        results.forEach(mail => {
            // Tarihi güzelleştir (Örn: 27 Oca 14:30)
            const dateObj = new Date(mail.date);
            const dateStr = dateObj.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

            // Puanı yüzdelik dileme çevir (0.85 -> %85)
            const scorePercent = mail.score ? (mail.score * 100).toFixed(0) : 0;

            // HTML Kartı Oluştur
            const card = document.createElement('div');
            card.className = 'search-result-card'; // CSS'te tanımladığımız sınıf
            
            // Kart İçeriği
            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <strong style="color: #fff; font-size: 1.1rem;">${mail.subject || '(Konusuz)'}</strong>
                    <span style="color: #888; font-size: 0.85rem;">${dateStr}</span>
                </div>
                
                <div style="font-size: 0.9rem; color: #bbb; margin-bottom: 8px;">
                    <span style="color: #bb86fc;">Kimden:</span> ${mail.sender || 'Bilinmiyor'}
                </div>
                
                <div style="font-size: 0.9rem; color: #888; border-left: 3px solid #333; padding-left: 10px; margin-bottom: 12px; font-style: italic;">
                    "${mail.snippet}..."
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #333; padding-top: 8px;">
                    <span class="similarity-score" title="Yapay zeka eşleşme oranı">
                        🎯 Uyumluluk: %${scorePercent}
                    </span>
                    <a href="/ui/view/${mail._id}" class="btn btn-sm btn-primary" style="text-decoration: none; padding: 4px 12px;">
                        Görüntüle
                    </a>
                </div>
            `;
            
            resultsContainer.appendChild(card);
        });
    }

    /**
     * Görünümü değiştirir (Tablo <-> Arama Sonuçları)
     */
    function toggleView(showSearch) {
        if (showSearch) {
            // Tabloyu gizle, Arama sonuçlarını göster
            if (defaultView) defaultView.style.display = 'none';
            if (searchView) searchView.style.display = 'block';
        } else {
            // Tabloyu göster, Arama sonuçlarını gizle
            if (defaultView) defaultView.style.display = 'block';
            if (searchView) searchView.style.display = 'none';
        }
    }
});