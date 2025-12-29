// static/js/home.js

document.addEventListener('DOMContentLoaded', () => {
    // 1. Sayı Sayacı Animasyonu
    const animateStats = () => {
        const stats = document.querySelectorAll('.stat-info h3');
        stats.forEach(stat => {
            const target = +stat.innerText;
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
            if(target > 0) updateCount();
        });
    };

    // 2. AI Notları İçin Küçük Bir Giriş Animasyonu
    const animateNotes = () => {
        const notes = document.querySelectorAll('.ai-note');
        notes.forEach((note, index) => {
            note.style.opacity = '0';
            note.style.transform = 'translateX(20px)';
            note.style.transition = `all 0.5s ease ${index * 0.2}s`;
            
            setTimeout(() => {
                note.style.opacity = '1';
                note.style.transform = 'translateX(0)';
            }, 100);
        });
    };

    // Fonksiyonları çalıştır
    animateStats();
    animateNotes();
});