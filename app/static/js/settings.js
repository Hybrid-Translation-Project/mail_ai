/* =================================
   TAB (SEKME) GEÇİŞ SİSTEMİ
   ================================= */
function openTab(evt, tabName) {
    // 1. Tüm tab içeriklerini gizle
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
        tabcontent[i].classList.remove("active");
    }

    // 2. Tüm butonların 'active' sınıfını kaldır
    tablinks = document.getElementsByClassName("tab-btn");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    // 3. Seçilen tabı göster
    var selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.style.display = "block";
        
        // Animasyonun tetiklenmesi için minik bir gecikme
        setTimeout(function() {
            selectedTab.classList.add("active");
        }, 10);
    }
    
    // 4. Tıklanan butonu aktif yap
    evt.currentTarget.classList.add("active");
}

/* =================================
   ETİKET DÜZENLEME MODALI
   ================================= */
function openEditModal(id, name, color, desc) {
    // Formun action URL'sini güncelle (Hangi etiketin güncelleneceğini belirtir)
    var form = document.getElementById('editTagForm');
    if (form) {
        form.action = "/ui/settings/tags/update/" + id;
    }

    // Inputları mevcut verilerle doldur
    var nameInput = document.getElementById('editName');
    var colorInput = document.getElementById('editColor');
    var descInput = document.getElementById('editDesc');

    if (nameInput) nameInput.value = name;
    if (colorInput) colorInput.value = color;
    if (descInput) descInput.value = desc;

    // Bootstrap Modal'ı aç
    var modalEl = document.getElementById('editTagModal');
    if (modalEl) {
        var modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

// Sayfa yüklendiğinde varsayılan olarak ilk tab açık gelsin (Opsiyonel Güvenlik)
document.addEventListener('DOMContentLoaded', function() {
    // Eğer HTML'de 'active' class'ı unutulursa JS ile ilkini aç
    if (!document.querySelector('.tab-content.active')) {
        document.querySelector('.tab-content').style.display = 'block';
        document.querySelector('.tab-content').classList.add('active');
    }
});