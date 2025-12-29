// static/js/editor.js

async function handleAction(actionType, mailId) {
    const textarea = document.querySelector('textarea[name="reply_draft"]');
    textarea.style.opacity = '0.5';
    textarea.value = "AI taslağı hazırlıyor, lütfen bekleyin...";

    try {
        const response = await fetch(`/ui/task_action/${mailId}/${actionType}`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Backend yönlendirme (303) yaptığı için tarayıcı bunu takip eder.
        // Ama biz garantici olalım:
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            window.location.reload();
        }
    } catch (error) {
        console.error("Hata:", error);
        alert("İşlem tamamlanamadı.");
        textarea.style.opacity = '1';
    }
}

// Taslağı Kaydet butonuna basıldığında "Kaydedildi" bildirimi çıkaralım
document.getElementById('replyForm')?.addEventListener('submit', function(e) {
    // Eğer submit "Onayla ve Gönder" değilse (yani sadece kaydetse)
    // burada bir 'success' animasyonu tetiklenebilir.
});

async function handleDecision(action) {
    const mailId = "{{ mail._id }}";
    // Textarea'yı bul
    const textarea = document.querySelector('textarea[name="reply_draft"]');
    
    // Yükleniyor efekti
    textarea.value = "AI kararına göre taslak hazırlanıyor, lütfen bekleyin...";
    textarea.style.opacity = "0.5";

    try {
        const response = await fetch(`/ui/task_action/${mailId}/${action}`, { method: 'POST' });
        if (response.ok) {
            // Backend RedirectResponse döndürdüğü için sayfayı yenilemek en garantisi
            window.location.reload();
        }
    } catch (err) {
        alert("Hata oluştu!");
        textarea.style.opacity = "1";
    }
}