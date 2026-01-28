// --- DİL DEĞİŞTİRME MOTORU ---
function changeLanguage(lang) {
    // 1. Dili Hafızaya Kaydet
    localStorage.setItem('appLang', lang);

    // 2. Sözlüğü Seç (Eğer translations.js yüklenmediyse hata vermesin)
    if (typeof translations === 'undefined') {
        console.error("HATA: translations.js dosyası yüklenmemiş!");
        return;
    }

    // Varsayılan dil TR olsun
    const selectedLang = translations[lang] || translations['tr'];

    // 3. Sayfadaki tüm 'data-i18n' etiketli elemanları bul
    const elements = document.querySelectorAll('[data-i18n]');

    // 4. Hepsini tek tek gez ve değiştir
    elements.forEach(el => {
        const key = el.getAttribute('data-i18n'); // Örn: 'btn_send'

        if (selectedLang[key]) {
            // Placeholder değiştirme (Input/Textarea)
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = selectedLang[key];
            }
            // Normal metin değiştirme
            else {
                // Eğer butonun içinde ikon varsa (<i>) onu bozmamak için sadece metni güncelleriz.
                if (el.children.length === 0) {
                    el.innerText = selectedLang[key];
                } else {
                    // İçerikteki metni bul ve değiştir (Basit yaklaşım)
                    // Not: Daha karmaşık yapılar için data-i18n-target kullanılabilir ama şimdilik yeterli.
                    // Mevcut haliyle HTML'i bozmamak için sadece text node'u değiştirmek daha güvenli olurdu ama
                    // şimdilik eski çalışan mantığı koruyoruz.
                    el.innerHTML = el.innerHTML.replace(el.innerText.trim(), selectedLang[key]);
                }
            }
        }
    });

    // 5. Dropdown güncelle
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) {
        langSelect.value = lang;
    }

    // 6. Sayfa dilini bildir
    document.documentElement.lang = lang;
}

// --- SAYFA YÜKLENDİĞİNDE ---
document.addEventListener('DOMContentLoaded', () => {
    // Hafızada dil var mı?
    const savedLang = localStorage.getItem('appLang') || 'tr';

    // Dili uygula
    changeLanguage(savedLang);

    // Dropdown dinleyicisi
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) {
        langSelect.value = savedLang;
        langSelect.addEventListener('change', (e) => {
            changeLanguage(e.target.value);
        });
    }
});