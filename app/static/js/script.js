document.addEventListener('DOMContentLoaded', function() {
    let timerSpan = document.querySelector('.timer-count'); // HTML'deki 15 yazan yer
    if (timerSpan) {
        let count = 15;
        setInterval(() => {
            count--;
            if (count <= 0) {
                window.location.reload();
            } else {
                timerSpan.textContent = count + " sn";
            }
        }, 1000);
    }
});