document.addEventListener('DOMContentLoaded', function () {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const body = document.body;

    // 1. LocalStorage'dan kullanıcının tercihini oku
    const isCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';

    // 2. Eğer kullanıcı daha önce kapattıysa, sayfayı kapalı başlat
    if (isCollapsed) {
        body.classList.add('sb-collapsed');
    }

    // 3. Butona tıklama olayı
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            // Sınıfı ekle/çıkar (Toggle)
            body.classList.toggle('sb-collapsed');

            // Yeni durumu kaydet
            const currentState = body.classList.contains('sb-collapsed');
            localStorage.setItem('sidebar-collapsed', currentState);
        });
    }
});