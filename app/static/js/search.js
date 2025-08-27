function searchProducts(query) {
    $.get('/search', { query: query })  // Отправляем GET-запрос на /search?query=текст
        .done(function(data) {
            // Очищаем текущий список
            $('#search-results').empty();
            // Добавляем товары в выпадающий список
            data.forEach(function(product) {
                $('#search-results').append(
                    `<div class="col-6 p-1"><div class="list-group-item card p-2 h-100">
    <a href="/product/${product.slug}" class="align-items-center" style="text-decoration: none; color: #000">
        <div >
            <img src="/static/uploads/${product.image}" class="img-fluid rounded" alt="${product.name}">
        </div>
        <div>
            <h6 class="mb-1 fs-6" >${product.name}</h6>
            <p class="mb-0 text-muted">${product.price} р.</p>
        </div>
    </a>
</div></div>`
                );
            });
            // Показываем список
            $('#search-results').show();
        })
        .fail(function(error) {
            console.error('Ошибка:', error);
        });
}

let lastRequestTime = 0;
const throttleDelay = 500; // 500 мс для троттлинга запросов

$(document).on('input', '#search-input', function() {
    const now = Date.now();


    if (now - lastRequestTime > throttleDelay) {
        lastRequestTime = now;
        const query = $(this).val();
        if (query.length > 3) {
            searchProducts(query);
        } else {
            $('#search-results').hide(); // Скрываем, если запрос короче 3 символов
        }
    }
});

