document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    // === ЦВЕТОВАЯ ПАЛИТРА ===
    function initColorPalette() {
        // Верхние паллетки (в карточках продуктов)
        $('.top-palletes .pallete-color').on('click keydown', function (e) {
            if (e.type === 'click' || e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const $palleteGroup = $(this).closest('.top-palletes');
                $palleteGroup.find('.pallete-color').removeClass('active').attr('aria-selected', 'false');
                $(this).addClass('active').attr('aria-selected', 'true');
            }
        });
    }

    // === ДОБАВЛЕНИЕ В КОРЗИНУ ===
    function initAddToCart() {
        $(document).on('click', '.add-to-cart-btn', function () {
            const product_id = $(this).data('product-id') || $(this).closest('.product-item').find('a').data('product-id');
            const selected_options = window.selectedOptions || {};

            // Определяем вариацию, чтобы передать точную цену и variation_id
            const matchingVariation = findMatchingVariation(selected_options);
            const variation_id = matchingVariation ? (matchingVariation.id || matchingVariation.variation_id) : null;
            const price_override = matchingVariation ? matchingVariation.price : null;

            $.ajax({
                url: '/cart/add',
                method: 'POST',
                headers: {
                    'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
                },
                data: { 
                    product_id: product_id,
                    selected_options: JSON.stringify(selected_options),
                    variation_id: variation_id,
                    price: price_override
                },
                success: function (data) {
                    console.log('Товар добавлен в корзину:', data);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.error("AJAX Error:", textStatus, errorThrown);
                }
            });
        });
    }



    // === ФИЛЬТР И СОРТИРОВКА ===
    function initFilterSidebar() {
        const openFilterBtn = document.getElementById("open-filter-btn");
        if (!openFilterBtn) return;

        const closeFilterBtn = document.getElementById("close-filter-btn");
        const filterSidebar = document.querySelector(".filter-sidebar");
        const filterOverlay = document.querySelector(".filter-overlay");
        const viewMoreButtons = document.querySelectorAll(".view-more");
        const filterOptions = document.querySelectorAll(".filter-option, .pallete-color");
        const clearFiltersBtn = document.querySelector(".clear-filters-btn");
        const showResultsBtn = document.querySelector(".show-results-btn");

        // Открытие/закрытие сайдбара (только если элементы существуют)
        const openFilterSidebar = () => {
            if (filterSidebar) {
                filterSidebar.classList.add("open");
            }
            if (filterOverlay) {
                filterOverlay.classList.add("active");
            }
            document.body.style.overflow = "hidden";
        };

        const closeFilterSidebar = () => {
            if (filterSidebar) {
                filterSidebar.classList.remove("open");
            }
            if (filterOverlay) {
                filterOverlay.classList.remove("active");
            }
            document.body.style.overflow = "";
        };

        openFilterBtn.addEventListener("click", openFilterSidebar);
        if (closeFilterBtn) closeFilterBtn.addEventListener("click", closeFilterSidebar);
        if (filterOverlay) filterOverlay.addEventListener("click", closeFilterSidebar);

        // Кнопки "Показать больше/меньше"
        if (viewMoreButtons) {
            viewMoreButtons.forEach((button) => {
                button.addEventListener("click", () => {
                    const hiddenOptions = button.previousElementSibling.querySelector(".hidden-options");
                    if (hiddenOptions) {
                        hiddenOptions.classList.toggle("visible");
                        button.textContent = hiddenOptions.classList.contains("visible") ? "Скрыть" : "Показать больше";
                    }
                });
            });
        }

        // Выбор опций фильтра (исключаем фильтры категории)
        if (filterOptions) {
            filterOptions.forEach((option) => {
                option.addEventListener("click", () => {
                    // Пропускаем фильтры категории (они обрабатываются отдельно)
                    if (option.closest('.filter-sidebar')) {
                        return;
                    }
                    
                    const parentContainer = option.closest(".filter-options");
                    if (!parentContainer) return;
                    
                    const isSingleChoice = parentContainer.dataset.type === "single-choice";

                    if (isSingleChoice) {
                        // Для радио-кнопок (выбор только одного варианта)
                        parentContainer.querySelectorAll(".filter-option, .pallete-color").forEach((el) => {
                            el.classList.remove("active");
                        });
                        option.classList.add("active");
                    } else {
                        // Для чекбоксов (множественный выбор)
                        option.classList.toggle("active");
                    }
                });
            });
        }

        // Кнопка сброса фильтров (исключаем фильтры категории)
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener("click", () => {
                document.querySelectorAll(".filter-option.active, .pallete-color.active").forEach((el) => {
                    // Пропускаем фильтры категории
                    if (el.closest('.filter-sidebar')) {
                        return;
                    }
                    
                    if (!el.closest(".filter-options") || 
                        el.closest(".filter-options").dataset.type !== "single-choice" || 
                        !el.classList.contains("active")) {
                        el.classList.remove("active");
                    }
                });
            });
        }

        // Кнопка "Показать результаты"
        if (showResultsBtn) {
            showResultsBtn.addEventListener("click", () => {
                // Здесь можно добавить логику для применения фильтров
                closeFilterSidebar();
            });
        }
    }

    // === SWIPER INIT ===
    function initSwipers() {
        if (typeof Swiper === "undefined") {
            console.warn("Swiper not found");
            return;
        }

        // Инициализация слайдера палитры цветов
        document.querySelectorAll(".pallete-slider").forEach((container) => {
            const swiperEl = container.querySelector(".swiper-container-pallete");
            if (swiperEl) {
                new Swiper(swiperEl, {
                    slidesPerView: 'auto',
                    spaceBetween: 10,
                    loop: false,
                    navigation: {
                        nextEl: container.querySelector(".custom-button-next-pallete"),
                        prevEl: container.querySelector(".custom-button-prev-pallete"),
                    },
                    breakpoints: {
                        320: { slidesPerView: 5, spaceBetween: 5 },
                        576: { slidesPerView: 7, spaceBetween: 8 },
                        992: { slidesPerView: 10, spaceBetween: 10 }
                    }
                });
            }
        });
    }

    // === HEART TOGGLE (ИЗБРАННОЕ) ===
    function initHeartToggle() {
        $(document).on('click', '.heart, .bi-heart-fill', function () {
            const $this = $(this);
            const $path = $this.find('path');
            
            if ($path.length > 0) {
                const currentFill = $path.attr('fill');
                $path.attr('fill', currentFill === 'red' ? 'none' : 'red');
            } else {
                $this.toggleClass('active');
            }
            
            // Если кнопка находится в карточке товара, то вызываем функцию добавления/удаления из избранного
            const $productItem = $this.closest('.product-item');
            if ($productItem.length > 0) {
                const productId = $productItem.find('[data-product-id]').data('product-id');
                if (productId) {
                    console.log('Переключение избранного для товара через иконку сердца:', productId);
                    // Здесь можно добавить AJAX-запрос к серверу
                }
            }
        });
    }

    // === ИНТЕРАКТИВНОСТЬ КАРТОЧЕК ТОВАРОВ ===
    function setupProductCards() {
        // Скрываем цветовые опции по умолчанию
        $('.product-item .color-options').hide();

        // Добавляем эффекты при наведении на карточки товаров
        $('.product-item').hover(
            function() {
                $(this).addClass('hover');
                // Показываем цветовые опции при наведении
                $(this).find('.color-options').fadeIn(200);
            },
            function() {
                $(this).removeClass('hover');
                // Скрываем цветовые опции при уходе курсора
                $(this).find('.color-options').fadeOut(200);
            }
        );
    }

    // === РАБОТА С ОПЦИЯМИ ТОВАРА ===
    function initProductOptions() {
        console.log('=== INIT PRODUCT OPTIONS ===');
        // Объект для хранения текущих выбранных опций
        window.selectedOptions = {};
        window.productVariations = window.variations || {};
        
        console.log('Initial window.selectedOptions:', window.selectedOptions);
        console.log('Window variations:', window.productVariations);
        console.log('Window variations type:', typeof window.productVariations);
        console.log('Window variations keys:', Object.keys(window.productVariations));
        
        // Инициализация выбранных опций по умолчанию
        $('.option-group').each(function() {
            const optionId = $(this).data('option-id');
            const $activeOption = $(this).find('.color-option.active, .radio-option.active, .other-option.active');
            const $selectOption = $(this).find('.select-option');
            
            console.log(`Option group ${optionId}:`, {
                activeOption: $activeOption.length > 0 ? $activeOption.data('value-id') : 'none',
                selectOption: $selectOption.length > 0 ? $selectOption.find('option:selected').val() : 'none'
            });
            
            if ($activeOption.length > 0) {
                window.selectedOptions[optionId] = $activeOption.data('value-id');
                updateSelectedValueText($(this), $activeOption.data('value'));
                console.log(`Set active option for ${optionId}:`, $activeOption.data('value-id'));
            } else if ($selectOption.length > 0) {
                const selectedOption = $selectOption.find('option:selected');
                window.selectedOptions[optionId] = selectedOption.val();
                updateSelectedValueText($(this), selectedOption.data('value'));
                console.log(`Set select option for ${optionId}:`, selectedOption.val());
            }
        });
        
        console.log('Final window.selectedOptions after initialization:', window.selectedOptions);
        console.log('Calling updateProductPrice after initialization...');
        updateProductPrice();
        
        console.log('Final window.selectedOptions:', window.selectedOptions);
        
        // Обработчик кликов по цветовым опциям
        $(document).on('click', '.color-option', function() {
            console.log('=== COLOR OPTION CLICKED ===');
            const $this = $(this);
            const $optionGroup = $this.closest('.option-group');
            const optionId = $this.data('option-id');
            const valueId = $this.data('value-id');
            const value = $this.data('value');
            
            console.log('Clicked option:', {
                optionId: optionId,
                valueId: valueId,
                value: value
            });
            
            // Убираем активный класс с других опций в группе
            $optionGroup.find('.color-option').removeClass('active');
            $optionGroup.find('.color-check').addClass('d-none');
            
            // Добавляем активный класс к выбранной опции
            $this.addClass('active');
            $this.find('.color-check').removeClass('d-none');
            
            // Обновляем выбранные опции
            window.selectedOptions[optionId] = valueId;
            console.log(`Updated selectedOptions for ${optionId}:`, valueId);
            console.log('Current window.selectedOptions:', window.selectedOptions);
            console.log('Window productVariations before update:', window.productVariations);
            updateSelectedValueText($optionGroup, value);
            
            // Обновляем цену и фото
            updateProductDisplay($this);
        });
        
        // Обработчик кликов по радио-опциям
        $(document).on('click', '.radio-option, .other-option', function() {
            const $this = $(this);
            const $optionGroup = $this.closest('.option-group');
            const optionId = $this.data('option-id');
            const valueId = $this.data('value-id');
            const value = $this.data('value');
            
            // Убираем активный класс с других опций в группе
            $optionGroup.find('.radio-option, .other-option').removeClass('active');
            
            // Добавляем активный класс к выбранной опции
            $this.addClass('active');
            
            // Обновляем выбранные опции
            window.selectedOptions[optionId] = valueId;
            updateSelectedValueText($optionGroup, value);
            
            // Обновляем цену и фото
            updateProductDisplay($this);
        });
        
        // Обработчик изменения селекта
        $(document).on('change', '.select-option', function() {
            const $this = $(this);
            const $optionGroup = $this.closest('.option-group');
            const optionId = $this.data('option-id');
            const $selectedOption = $this.find('option:selected');
            const valueId = $selectedOption.val();
            const value = $selectedOption.data('value');
            
            // Обновляем выбранные опции
            window.selectedOptions[optionId] = valueId;
            updateSelectedValueText($optionGroup, value);
            
            // Обновляем цену и фото
            updateProductDisplay($selectedOption);
        });
    }
    
    // Функция обновления текста выбранного значения
    function updateSelectedValueText($optionGroup, value) {
        $optionGroup.find('.option-selected-value').text(`- ${value}`);
    }
    
    // Функция обновления отображения товара (цена и фото)
    function updateProductDisplay($selectedElement) {
        console.log('updateProductDisplay called with element:', $selectedElement);
        
        const photosRaw = $selectedElement.data('photos');
        const hasPhotosStr = $selectedElement.closest('.option-group').data('has-photos');
        const hasPhotosDebug = $selectedElement.closest('.option-group').data('debug');
        const hasPhotosBool = $selectedElement.closest('.option-group').data('has-photos-bool');
        
        console.log('=== DEBUG HAS_PHOTOS ===');
        console.log('hasPhotosStr:', hasPhotosStr, '(type:', typeof hasPhotosStr, ')');
        console.log('hasPhotosDebug:', hasPhotosDebug, '(type:', typeof hasPhotosDebug, ')');
        console.log('hasPhotosBool:', hasPhotosBool, '(type:', typeof hasPhotosBool, ')');
        
        // Пробуем разные способы получения hasPhotos
        let hasPhotos = false;
        
        // Способ 1: через строку
        if (hasPhotosStr === 'true' || hasPhotosStr === true) {
            hasPhotos = true;
            console.log('✅ hasPhotos set to true via hasPhotosStr');
        }
        
        // Способ 2: через debug значение
        if (hasPhotosDebug === 'True' || hasPhotosDebug === true) {
            hasPhotos = true;
            console.log('✅ hasPhotos set to true via hasPhotosDebug');
        }
        
        // Способ 3: через bool значение
        if (hasPhotosBool === 'true' || hasPhotosBool === true) {
            hasPhotos = true;
            console.log('✅ hasPhotos set to true via hasPhotosBool');
        }
        
        console.log('hasPhotos (final):', hasPhotos);
        
        // Получаем данные о фотографиях
        let photos = photosRaw;
        if (typeof photosRaw === 'string' && photosRaw.trim() !== '') {
            try {
                photos = JSON.parse(photosRaw);
                console.log('Parsed photos from JSON string:', photos);
            } catch (e) {
                console.error('Error parsing photos JSON:', e);
                console.error('Raw photos data:', photosRaw);
                photos = null;
            }
        }
        
        console.log('Photos data:', photos);
        console.log('Has individual photos:', hasPhotos);
        console.log('Photos type:', typeof photos);
        console.log('Photos length:', photos ? photos.length : 'undefined');
        
        // Проверяем, что photos - это массив
        if (photos && Array.isArray(photos) && photos.length > 0) {
            console.log('Photos array details:', photos);
            photos.forEach((photo, index) => {
                console.log(`Photo ${index}:`, photo);
            });
        }
        
        // Обновляем фотографии, только если у опции явно есть индивидуальные фото
        if (hasPhotos === true && Array.isArray(photos) && photos.length > 0) {
            console.log('✅ UPDATING IMAGES - Conditions met!');
            console.log('hasPhotos:', hasPhotos);
            console.log('photos array:', photos);
            console.log('photos length:', photos.length);
            updateProductImages(photos);
        } else {
            console.log('❌ NOT UPDATING IMAGES - Conditions not met');
            console.log('hasPhotos === true:', hasPhotos === true);
            console.log('photos is array:', Array.isArray(photos));
            console.log('photos length:', photos ? photos.length : 'undefined');
            console.log('photos type:', typeof photos);
            // Ничего не делаем с фотогалереей, если индивидуальных фото нет
        }
        
        // Обновляем цену на основе выбранных опций
        updateProductPrice();
    }
    
    // Функция обновления фотографий товара
    function updateProductImages(photos) {
        console.log('=== UPDATING PRODUCT IMAGES ===');
        console.log('Photos to update:', photos);
        
        if (!photos || photos.length === 0) {
            console.log('No photos to update');
            return;
        }
        
        // Сортируем фото по порядку
        photos.sort((a, b) => a.order - b.order);
        console.log('Sorted photos:', photos);
        
        // Находим изображения только внутри галереи товара
        let $galleryImages = $('#product-gallery img.img-fluid.responsive-img.no-interact');
        
        // Если не нашли по классу, ищем по структуре
        if ($galleryImages.length === 0) {
            $galleryImages = $('#product-gallery .col-12 img').filter('[src*="/static/uploads/"]');
            console.log('Trying structure selector, found:', $galleryImages.length);
        }
        
        // Если все еще не нашли, ищем по более общим селекторам
        if ($galleryImages.length === 0) {
            $galleryImages = $('#product-gallery img[src*="/static/uploads/"]').filter(function() {
                const src = $(this).attr('src');
                // Исключаем изображения, которые не являются фотографиями товара
                return !src.includes('logo') && 
                       !src.includes('icon') && 
                       !src.includes('size-guide') && 
                       !src.includes('dilivBack') &&
                       !src.includes('insta-logo');
            });
            console.log('Trying general selector, found:', $galleryImages.length);
        }
        
        console.log('Found filtered gallery images:', $galleryImages.length);
        
        // Выводим информацию о найденных изображениях
        $galleryImages.each(function(index) {
            console.log(`Gallery Image ${index}:`, $(this).attr('src'));
        });
        
        if ($galleryImages.length > 0) {
            console.log('Successfully found gallery images:', $galleryImages.length);
            
            // Находим основное изображение (с флагом is_main)
            const mainPhoto = photos.find(photo => photo.is_main) || photos[0];
            
            // Заменяем изображения галереи на индивидуальные фото
            photos.forEach((photo, photoIndex) => {
                if (photoIndex < $galleryImages.length) {
                    const newSrc = `/static/uploads/${photo.path}`;
                    console.log(`Updating gallery image ${photoIndex} to:`, newSrc);
                    $galleryImages.eq(photoIndex).attr('src', newSrc);
                }
            });
            
            // Проверяем, что src действительно изменился
            setTimeout(() => {
                $galleryImages.each(function(index) {
                    if (index < photos.length) {
                        const currentSrc = $(this).attr('src');
                        console.log(`Gallery image ${index} src after update:`, currentSrc);
                    }
                });
            }, 100);
            
            // Сначала показываем все изображения
            $galleryImages.show();
            
            // Если индивидуальных фото меньше, чем изображений в галерее, 
            // скрываем лишние изображения
            if (photos.length < $galleryImages.length) {
                console.log(`Hiding ${$galleryImages.length - photos.length} extra gallery images`);
                for (let i = photos.length; i < $galleryImages.length; i++) {
                    console.log(`Hiding extra gallery image ${i}:`, $galleryImages.eq(i).attr('src'));
                    $galleryImages.eq(i).hide();
                }
            }
        } else {
            console.error('No gallery images found!');
            console.log('All images on page:', $('img').length);
            
            // Показываем все изображения для отладки
            $('img').each(function(index) {
                const src = $(this).attr('src');
                if (src && src.includes('/static/uploads/')) {
                    console.log(`Upload image ${index}:`, src);
                }
            });
            
            // Fallback: используем все изображения uploads, но с предупреждением
            console.warn('Using fallback: all upload images');
            $galleryImages = $('img[src*="/static/uploads/"]').filter(function() {
                const src = $(this).attr('src');
                return !src.includes('logo') && 
                       !src.includes('icon') && 
                       !src.includes('size-guide') && 
                       !src.includes('dilivBack') &&
                       !src.includes('insta-logo');
            });
            
            if ($galleryImages.length > 0) {
                console.log('Using fallback images:', $galleryImages.length);
            }
        }
    }
    
    // Функция восстановления всех изображений товара
    function restoreProductImages() {
        console.log('=== RESTORING PRODUCT IMAGES ===');
        
        // Находим изображения только внутри галереи товара
        let $galleryImages = $('#product-gallery img.img-fluid.responsive-img.no-interact');
        
        if ($galleryImages.length === 0) {
            $galleryImages = $('#product-gallery .col-12 img').filter('[src*="/static/uploads/"]');
        }
        
        if ($galleryImages.length === 0) {
            $galleryImages = $('#product-gallery img[src*="/static/uploads/"]').filter(function() {
                const src = $(this).attr('src');
                return !src.includes('logo') && 
                       !src.includes('icon') && 
                       !src.includes('size-guide') && 
                       !src.includes('dilivBack') &&
                       !src.includes('insta-logo');
            });
        }
        
        if ($galleryImages.length > 0) {
            console.log('Restoring all gallery images:', $galleryImages.length);
            $galleryImages.show();
        } else {
            console.log('No gallery images found to restore');
        }
    }
    
    // Функция обновления цены товара
    function updateProductPrice() {
        console.log('=== UPDATE PRODUCT PRICE ===');
        console.log('Current selected options:', window.selectedOptions);
        console.log('Window productVariations:', window.productVariations);
        console.log('Window selectedOptions type:', typeof window.selectedOptions);
        console.log('Window selectedOptions keys:', Object.keys(window.selectedOptions || {}));
        
        // Находим подходящую вариацию товара
        const matchingVariation = findMatchingVariation(window.selectedOptions);
        
        if (matchingVariation) {
            console.log('Found matching variation:', matchingVariation);
            
            // Находим элемент цены по ID
            const $priceElement = $('#product-price');
            console.log('Price element found:', $priceElement.length > 0);
            console.log('Price element text before:', $priceElement.text());
            
            if ($priceElement.length > 0) {
                $priceElement.text('$' + matchingVariation.price);
                console.log('Updated price to: $' + matchingVariation.price);
                console.log('Price element text after:', $priceElement.text());
            } else {
                console.log('Price element not found with ID #product-price');
                // Попробуем альтернативные селекторы
                const $altPriceElements = $('.product-gallery__price, .fs-4, .product-price, [class*="price"]');
                console.log('Alternative price elements found:', $altPriceElements.length);
                if ($altPriceElements.length > 0) {
                    $altPriceElements.first().text('$' + matchingVariation.price);
                    console.log('Updated price using alternative selector');
                }
            }
            
            // Можно также обновить SKU, наличие и т.д.
            if (matchingVariation.sku) {
                $('.product-sku').text(matchingVariation.sku);
            }
            
            if (matchingVariation.stock !== undefined) {
                const $stockStatus = $('.stock-status');
                if ($stockStatus.length > 0) {
                    if (matchingVariation.stock > 0) {
                        $stockStatus.text('В наличии').removeClass('out-of-stock').addClass('in-stock');
                    } else {
                        $stockStatus.text('Нет в наличии').removeClass('in-stock').addClass('out-of-stock');
                    }
                }
            }
        } else {
            console.log('No matching variation found');
        }
    }
    
    // Функция поиска подходящей вариации товара
    function findMatchingVariation(selectedOptions) {
        console.log('=== FIND MATCHING VARIATION ===');
        console.log('Selected options:', selectedOptions);
        console.log('Window productVariations:', window.productVariations);
        
        if (!window.productVariations || Object.keys(window.productVariations).length === 0) {
            console.log('No variations available');
            return null;
        }

        console.log('Looking for variation matching:', selectedOptions);
        console.log('Available variations:', window.productVariations);
        
        // Получаем массив выбранных значений опций
        const selectedValueIds = Object.values(selectedOptions).map(id => parseInt(id));
        console.log('Selected value IDs:', selectedValueIds);
        
        // Ищем вариацию, которая точно соответствует выбранным опциям
        for (const variationId in window.productVariations) {
            const variation = window.productVariations[variationId];
            
            if (variation.option_value_ids && variation.option_value_ids.length > 0) {
                // Проверяем, соответствуют ли выбранные опции этой вариации
                const variationValueIds = variation.option_value_ids.map(id => parseInt(id));
                console.log(`Variation ${variationId} has value IDs:`, variationValueIds);
                
                // Проверяем, что все выбранные значения есть в вариации и наоборот
                const selectedSet = new Set(selectedValueIds);
                const variationSet = new Set(variationValueIds);
                
                if (selectedSet.size === variationSet.size && 
                    [...selectedSet].every(id => variationSet.has(id))) {
                    console.log('Found exact matching variation:', variation);
                    return variation;
                }
            }
        }
        
        // Fallback: если у вариаций нет option_value_ids, пытаемся сопоставить по combo_html
        // Строим пары "ИмяОпции: Значение" из выбранных опций
        const selectedPairs = [];
        if (window.productOptions) {
            for (const [optIdStr, valId] of Object.entries(selectedOptions)) {
                const optId = parseInt(optIdStr);
                const option = window.productOptions.find(o => parseInt(o.id) === optId);
                if (!option) continue;
                const valueObj = (option.values || []).find(v => parseInt(v.id) === parseInt(valId));
                if (!valueObj) continue;
                selectedPairs.push({ name: (option.name || '').trim(), value: (valueObj.value || '').trim() });
            }
        }
        console.log('Selected option pairs:', selectedPairs);

        if (selectedPairs.length > 0) {
            for (const variationId in window.productVariations) {
                const variation = window.productVariations[variationId];
                const html = variation.combo_html || '';
                if (!html) continue;
                // Парсим пары из combo_html
                const pairs = [];
                const regex = /<strong>([^:<]+):<\/strong>\s*([^<]+)<br\s*\/?\>/gi;
                let m;
                while ((m = regex.exec(html)) !== null) {
                    const name = (m[1] || '').trim();
                    const value = (m[2] || '').trim();
                    pairs.push({ name, value });
                }
                if (pairs.length === 0) continue;
                const allMatch = selectedPairs.every(sp => pairs.some(p => p.name === sp.name && p.value === sp.value));
                if (allMatch) {
                    console.log('Found variation by combo_html:', variationId, variation);
                    return variation;
                }
            }
        }

        // Если точного совпадения нет, ищем частичное совпадение
        for (const variationId in window.productVariations) {
            const variation = window.productVariations[variationId];
            
            if (variation.option_value_ids && variation.option_value_ids.length > 0) {
                const variationValueIds = variation.option_value_ids.map(id => parseInt(id));
                
                // Проверяем, есть ли хотя бы одно совпадение
                const hasAnyMatch = selectedValueIds.some(selectedId => 
                    variationValueIds.includes(selectedId)
                );
                
                if (hasAnyMatch) {
                    console.log('Found partially matching variation:', variation);
                    return variation;
                }
            }
        }
        
        // Если ничего не найдено, возвращаем первую доступную вариацию
        const firstVariation = Object.values(window.productVariations)[0];
        if (firstVariation) {
            console.log('No matching variation found, using first available:', firstVariation);
            return firstVariation;
        }
        
        return null;
    }

    // === ИНИЦИАЛИЗАЦИЯ ===
    initColorPalette();
    initAddToCart();

    initFilterSidebar();
    initSwipers();
    initHeartToggle();
    setupProductCards();
    initProductOptions(); // Добавляем новую функцию

    // Экспортируем публичные хелперы для шаблонов
    window.updateProductPricePublic = updateProductPrice;
    window.setProductVariations = function(newVariations) {
        try {
            window.variations = newVariations || {};
            window.productVariations = window.variations || {};
            if (typeof window.updateProductPricePublic === 'function') {
                window.updateProductPricePublic();
            }
        } catch (e) {
            console.error('setProductVariations error:', e);
        }
    };

    // Добавляем стили для сайдбара фильтров через JavaScript, если они не определены в CSS
    const style = document.createElement('style');
    style.textContent = `
        .filter-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 998;
            display: none;
        }
        .filter-overlay.active {
            display: block;
        }
        .filter-sidebar {
            position: fixed;
            top: 0;
            right: -400px;
            width: 400px;
            height: 100%;
            background-color: white;
            z-index: 999;
            transition: right 0.3s ease;
            display: flex;
            flex-direction: column;
            max-width: 85%;
        }
        .filter-sidebar.open {
            right: 0;
        }
        .filter-sidebar-body {
            flex: 1;
            overflow-y: auto;
        }
        .hidden-options {
            display: none;
        }
        .hidden-options.visible {
            display: flex;
        }
        .filter-option {
            background-color: #f5f5f5;
            border: 1px solid transparent;
            transition: all 0.2s ease;
        }
        .filter-option.active {
            background-color: #000;
            color: white;
        }
        .pallete-color {
            width: 26px;
            height: 26px;
            border-radius: 50%;
            cursor: pointer;
            position: relative;
        }
        .pallete-color.active::after {
            content: '';
            position: absolute;
            top: -3px;
            left: -3px;
            right: -3px;
            bottom: -3px;
            border: 1px solid #000;
            border-radius: 50%;
        }
        
        /* Цвета палитры */
        .pallete-color-white { background-color: white; border: 1px solid #ccc; }
        .pallete-color-silver { background-color: silver; }
        .pallete-color-black { background-color: black; }
        .pallete-color-brown { background-color: brown; }
        .pallete-color-yellow { background-color: yellow; }
        .pallete-color-orange { background-color: orange; }
        .pallete-color-red { background-color: red; }
        .pallete-color-pink { background-color: pink; }
        .pallete-color-purple { background-color: purple; }
        .pallete-color-sky { background-color: skyblue; }
        .pallete-color-lavender { background-color: lavender; }
        .pallete-color-lime { background-color: lime; }
        .pallete-color-aqua { background-color: aqua; }
        .pallete-color-mint { background-color: #98ff98; }
        .pallete-color-cream { background-color: #fffdd0; }
        .pallete-color-taupe { background-color: #483c32; }
        .pallete-color-platinum { background-color: #e5e4e2; }
        .pallete-color-navy { background-color: navy; }
        .pallete-color-ivory { background-color: ivory; }
        
        /* Стили для промо-блоков */
        .promotional-item {
            background-size: cover;
            background-position: center;
            min-height: 300px;
            padding: 20px;
            color: white;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
        }
        
        /* Стили для карточек товаров */
        .product-item {
            position: relative;
            transition: all 0.3s ease;
        }
        .product-item .fav-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 10;
            cursor: pointer;
            color: #ccc;
        }
        .product-item .fav-btn.active {
            color: red;
        }
        .product-item .add-to-cart-btn {
            cursor: pointer;
            transition: transform 0.2s ease;
        }
        .product-item .add-to-cart-btn:hover {
            transform: scale(1.1);
        }
        .product-item.hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .product-item .color-options {
            display: none; /* Скрываем цветовые опции по умолчанию */
            position: relative;
            z-index: 5;
        }
        
        /* Стили для опций товара */
        .product-options .option-group {
            margin-bottom: 1.5rem;
        }
        
        .color-option {
            position: relative;
            transition: all 0.3s ease;
        }
        
        .color-option .pallete-color {
            border: 2px solid transparent;
            transition: border-color 0.3s ease;
        }
        
        .color-option.active .pallete-color {
            border-color: #000;
        }
        
        .color-option .color-check {
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .color-option.active .color-check {
            opacity: 1;
        }
        
        .radio-option, .other-option {
            transition: all 0.3s ease;
        }
        
        .radio-option > div, .other-option > div {
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }
        
        .radio-option.active > div, .other-option.active > div {
            border-color: #000;
            background-color: #000 !important;
            color: white;
        }
        
        .select-option {
            padding: 0.5rem;
            border: 1px solid #ccc;
            border-radius: 0.25rem;
            background-color: white;
            transition: border-color 0.3s ease;
        }
        
        .select-option:focus {
            border-color: #000;
            outline: none;
        }
        
        .option-selected-value {
            font-style: italic;
            color: #666;
        }
        
        /* Стили для статуса наличия */
        .stock-status.in-stock {
            color: green;
        }
        
        .stock-status.out-of-stock {
            color: red;
        }
    `;
    document.head.appendChild(style);
});

// === ИНИЦИАЛИЗАЦИЯ КНОПОК ОПЦИЙ ДЛЯ ОТФИЛЬТРОВАННЫХ ТОВАРОВ ===
function initFilteredProductOptions() {
    console.log('=== ИНИЦИАЛИЗАЦИЯ КНОПОК ОПЦИЙ ДЛЯ ОТФИЛЬТРОВАННЫХ ТОВАРОВ ===');
    
    // Обработчик кликов по цветовым опциям в отфильтрованных товарах
    $(document).on('click', '.product-item .color-options .pallete-color', function() {
        console.log('=== КЛИК ПО ЦВЕТОВОЙ ОПЦИИ В ОТФИЛЬТРОВАННОМ ТОВАРЕ ===');
        const $this = $(this);
        const $productItem = $this.closest('.product-item');
        const productId = $productItem.find('a').data('product-id');
        const colorName = $this.data('color-name');
        
        console.log('Клик по цвету:', {
            productId: productId,
            colorName: colorName
        });
        
        // Убираем активный класс с других цветов в этом товаре
        $productItem.find('.color-options .pallete-color').removeClass('active');
        
        // Добавляем активный класс к выбранному цвету
        $this.addClass('active');
        
        console.log(`Цвет ${colorName} выбран для товара ${productId}`);
    });
    
    // Обработчик наведения на товар для показа цветовых опций
    $(document).on('mouseenter', '.product-item', function() {
        const $this = $(this);
        const $colorOptions = $this.find('.color-options');
        
        if ($colorOptions.length > 0) {
            $colorOptions.fadeIn(200);
        }
    });
    
    // Обработчик ухода мыши с товара для скрытия цветовых опций
    $(document).on('mouseleave', '.product-item', function() {
        const $this = $(this);
        const $colorOptions = $this.find('.color-options');
        
        if ($colorOptions.length > 0) {
            $colorOptions.fadeOut(200);
        }
    });
}

// === СЛАЙДЕР ИЗОБРАЖЕНИЙ ТОВАРОВ ===
function initProductImageSliders() {
    console.log('=== ИНИЦИАЛИЗАЦИЯ СЛАЙДЕРОВ ИЗОБРАЖЕНИЙ ===');
    const sliders = $('.product-image-slider');
    console.log('Найдено слайдеров:', sliders.length);
    
    sliders.each(function(index) {
        const $slider = $(this);
        const $slides = $slider.find('.product-image-slide');
        const totalSlides = $slides.length;
        const productId = $slider.data('product-id');
        
        console.log(`Слайдер ${index + 1} (товар ${productId}): ${totalSlides} изображений`);
        
        if (totalSlides <= 1) {
            console.log(`Слайдер ${index + 1}: пропускаем (${totalSlides} изображений)`);
            return;
        }
        
        let currentSlide = 0;
        let slideInterval;
        
        // Функция для показа следующего слайда
        function showNextSlide() {
            console.log(`Слайдер ${productId}: переключение слайда`);
            console.log(`  Текущий слайд: ${currentSlide + 1}`);
            console.log(`  Всего слайдов: ${totalSlides}`);
            
            $slides.removeClass('active');
            currentSlide = (currentSlide + 1) % totalSlides;
            $slides.eq(currentSlide).addClass('active');
            
            console.log(`  Новый слайд: ${currentSlide + 1}`);
            console.log(`  Активных слайдов: ${$slides.filter('.active').length}`);
        }
        
        // Обработчик наведения мыши
        $slider.closest('.product-item').on('mouseenter', function() {
            console.log(`Слайдер ${productId}: наведение мыши`);
            // Запускаем автоматическое перелистывание
            slideInterval = setInterval(showNextSlide, 1500); // 1.5 секунды между слайдами
        });
        
        // Обработчик ухода мыши
        $slider.closest('.product-item').on('mouseleave', function() {
            console.log(`Слайдер ${productId}: уход мыши`);
            // Останавливаем автоматическое перелистывание
            if (slideInterval) {
                clearInterval(slideInterval);
                slideInterval = null;
            }
            
            // Возвращаемся к первому слайду
            $slides.removeClass('active');
            currentSlide = 0;
            $slides.eq(currentSlide).addClass('active');
        });
        
        // Обработчик клика для ручного переключения
        $slider.on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log(`Слайдер ${productId}: клик`);
            
            // Останавливаем автоматическое перелистывание
            if (slideInterval) {
                clearInterval(slideInterval);
                slideInterval = null;
            }
            
            showNextSlide();
        });
    });
}