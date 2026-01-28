document.addEventListener('DOMContentLoaded', function () {
    // --- Dynamic Tag Colors ---
    // Bu fonksiyon data-bg-color attribute'una sahip tüm elementlerin
    // background-color stilini JS ile atar.
    // Linter hatalarını önlemek için HTML'de inline style kullanmıyoruz.
    const applyTagColors = () => {
        const tags = document.querySelectorAll('[data-bg-color]');
        tags.forEach(tag => {
            tag.style.backgroundColor = tag.getAttribute('data-bg-color');
        });
    };

    applyTagColors();
});
