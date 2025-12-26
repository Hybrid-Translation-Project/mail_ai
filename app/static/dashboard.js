// Gelen Kutusu Otomatik Yenileme Scripti

// 15 saniyede bir sayfayı yeniler
var timeLeft = 15;
var elem = document.getElementById('countdown');

// Eğer sayfada sayaç elementi varsa çalıştır
if (elem) {
    var timerId = setInterval(countdown, 1000);
}

function countdown() {
    if (timeLeft <= 0) {
        // Süre bittiğinde durdur ve yenile
        if(timerId) clearTimeout(timerId);
        window.location.reload();
    } else {
        // Süreyi güncelle
        if(elem) {
            elem.innerHTML = timeLeft;
            timeLeft--;
        }
    }
}