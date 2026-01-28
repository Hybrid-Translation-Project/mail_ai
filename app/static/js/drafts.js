async function deleteDraft(mailId) {
    // Kullanıcıya son bir şans verelim
    const confirmation = confirm("Bu taslağı silmek istediğinize emin misiniz? (Bu işlem geri alınamaz)");
    
    if (!confirmation) {
        return; // Vazgeçti
    }

    try {
        // Backend'e silme isteği gönder
        const response = await fetch(`/delete-draft/${mailId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Başarılıysa sayfayı yenile ki liste güncellensin
            window.location.reload();
        } else {
            // Backend'den hata dönerse
            const data = await response.json();
            alert(data.error || "Silinirken bir hata oluştu.");
        }
    } catch (error) {
        console.error('Hata:', error);
        alert("Sunucuyla iletişim kurulamadı. İnternet bağlantınızı kontrol edin.");
    }
}