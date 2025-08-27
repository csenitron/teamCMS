$(document).ready(function() {
    // Инициализация избранного
    initFavorites();
    
    // Загружаем состояние избранного при загрузке страницы
    loadFavoriteState();
});

function initFavorites() {
    // Убираем предыдущие обработчики, чтобы избежать дублирования
    $(document).off('click', '.fav-btn');
    
    $(document).on('click', '.fav-btn', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const $btn = $(this);
        const product_id = $btn.data('product-id');
        
        if (!product_id) {
            console.error('Product ID not found');
            return;
        }
        
        console.log('Переключение избранного для товара:', product_id);
        
        // Защита от двойных кликов
        if ($btn.hasClass('processing')) {
            console.log('Запрос уже обрабатывается');
            return;
        }
        
        $btn.addClass('processing');
        
        // Добавляем CSRF токен
        const csrfToken = $('meta[name="csrf-token"]').attr('content');
        
        $.ajax({
            url: '/favorites/toggle',
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            data: { product_id: product_id },
            success: function(response) {
                console.log('Избранное обновлено:', response);
                
                if (response.is_favorite) {
                    // Товар добавлен в избранное
                    $btn.addClass('active');
                    $btn.find('svg').removeClass('bi-heart').addClass('bi-heart-fill');
                    
                    // Показываем уведомление
                    showNotification(response.message, 'success');
                } else {
                    // Товар удален из избранного
                    $btn.removeClass('active');
                    $btn.find('svg').removeClass('bi-heart-fill').addClass('bi-heart');
                    
                    // Показываем уведомление
                    showNotification(response.message, 'info');
                    
                    // Если мы на странице избранного, удаляем элемент
                    if (window.location.pathname === '/favorites') {
                        $btn.closest('.product-item').fadeOut(300, function() {
                            $(this).remove();
                            if ($('.product-item').length === 0) {
                                window.location.href = '/';
                            }
                        });
                    }
                }
            },
            error: function(xhr, status, error) {
                console.error("AJAX Error:", status, error);
                
                if (xhr.status === 401) {
                    showNotification('Необходима авторизация для добавления в избранное', 'error');
                } else {
                    showNotification('Ошибка при обновлении избранного', 'error');
                }
            },
            complete: function() {
                // Снимаем класс processing в любом случае
                $btn.removeClass('processing');
            }
        });
    });
}

function showNotification(message, type) {
    // Создаем уведомление
    const notification = $(`
        <div class="alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    
    $('body').append(notification);
    
    // Автоматически скрываем через 3 секунды
    setTimeout(function() {
        notification.fadeOut(300, function() {
            $(this).remove();
        });
    }, 3000);
}

// Функция для загрузки состояния избранного с сервера
function loadFavoriteState() {
    $.ajax({
        url: '/favorites/list',
        method: 'GET',
        success: function(response) {
            console.log('Загружено состояние избранного:', response.favorites);
            updateFavoriteButtons(response.favorites);
        },
        error: function(xhr, status, error) {
            console.error("Ошибка загрузки состояния избранного:", error);
        }
    });
}

// Функция для обновления состояния кнопок избранного на основе данных с сервера
function updateFavoriteButtons(favoriteProductIds) {
    $('.fav-btn').each(function() {
        const $btn = $(this);
        const productId = $btn.data('product-id');
        
        if (favoriteProductIds.includes(productId)) {
            $btn.addClass('active');
            $btn.find('svg').removeClass('bi-heart').addClass('bi-heart-fill');
        } else {
            $btn.removeClass('active');
            $btn.find('svg').removeClass('bi-heart-fill').addClass('bi-heart');
        }
    });
}