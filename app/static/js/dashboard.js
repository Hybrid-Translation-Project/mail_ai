document.addEventListener('DOMContentLoaded', function () {
    // --- Gelen Kutusu Otomatik Yenileme (Countdown) ---
    const countdownEl = document.getElementById('countdown');

    // Eğer sayfada sayaç elementi varsa çalıştır
    if (countdownEl) {
        let timeLeft = 15;

        const timerId = setInterval(() => {
            timeLeft--;
            countdownEl.innerText = timeLeft;

            if (timeLeft <= 0) {
                clearInterval(timerId);
                // Sayfayı zorla yenile
                window.location.reload();
            }
        }, 1000);
    }

    // --- İstatistik Animasyonları (Eğer bu sayfada istatistik varsa çalışır) ---
    const animateStats = () => {
        const stats = document.querySelectorAll('.stat-info h3');
        if (stats.length === 0) return;

        stats.forEach(stat => {
            const target = +stat.innerText;
            if (target === 0) return;

            let count = 0;
            const speed = 2000 / target; // Animasyon hızı

            const updateCount = () => {
                if (count < target) {
                    count++;
                    stat.innerText = count;
                    setTimeout(updateCount, speed);
                } else {
                    stat.innerText = target;
                }
            };
            updateCount();
        });
    };

    // --- Dynamic Tag Colors (Linter Fix) ---
    const applyTagColors = () => {
        const tags = document.querySelectorAll('[data-bg-color]');
        tags.forEach(tag => {
            tag.style.backgroundColor = tag.getAttribute('data-bg-color');
        });
    };

    // Fonksiyonları çalıştır
    animateStats();
    applyTagColors();
});