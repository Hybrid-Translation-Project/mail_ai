    // static/js/search.js
function enableDynamicSearch(inputId, listContainerId, itemSelector) {
    const searchInput = document.getElementById(inputId);
    const listContainer = document.getElementById(listContainerId);

    if (!searchInput || !listContainer) return;

    searchInput.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const items = listContainer.querySelectorAll(itemSelector);

        items.forEach(item => {
            // data-search niteliği veya elementin metin içeriği üzerinden arama yapar
            const text = item.innerText.toLowerCase();
            const searchData = item.getAttribute('data-search') ? item.getAttribute('data-search').toLowerCase() : "";
            
            if (text.includes(searchTerm) || searchData.includes(searchTerm)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}