#!/usr/bin/env python3
"""
Скрипт для исправления связей вариаций с опциями
Запускать: python fix_variations.py
"""

from app import create_app
from app.extensions import db
from app.models.productOptions import ProductVariation, ProductVariationOptionValue, ProductOptionValue

def fix_variations():
    """Исправляем связи вариаций с опциями"""
    app = create_app()
    
    with app.app_context():
        print("=== FIXING VARIATIONS ===")
        
        # Получаем все вариации для товара с ID 6
        product_id = 6
        variations = ProductVariation.query.filter_by(product_id=product_id).all()
        
        print(f"Found {len(variations)} variations for product {product_id}")
        
        # Получаем все значения опций
        option_values = ProductOptionValue.query.all()
        option_values_dict = {ov.value: ov.id for ov in option_values}
        print(f"Available option values: {option_values_dict}")
        
        # Определяем правильные связи для каждой вариации
        # Это нужно настроить вручную на основе ваших данных
        variation_links = {
            287: ['Красный', 'XS'],  # Вариация 287: Цвет=Красный, Размер=XS
            288: ['Красный', 'XL'],  # Вариация 288: Цвет=Красный, Размер=XL
            289: ['Белый', 'XS'],    # Вариация 289: Цвет=Белый, Размер=XS
            290: ['Белый', 'XL'],    # Вариация 290: Цвет=Белый, Размер=XL
        }
        
        for variation in variations:
            print(f"\n--- Fixing Variation {variation.id} ---")
            
            # Удаляем существующие связи
            existing_pvovs = ProductVariationOptionValue.query.filter_by(variation_id=variation.id).all()
            for pvov in existing_pvovs:
                db.session.delete(pvov)
                print(f"  Deleted existing link: {pvov.option_value_id}")
            
            # Создаем новые связи
            if variation.id in variation_links:
                option_value_names = variation_links[variation.id]
                for option_value_name in option_value_names:
                    if option_value_name in option_values_dict:
                        option_value_id = option_values_dict[option_value_name]
                        
                        # Создаем новую связь
                        pvov = ProductVariationOptionValue(
                            variation_id=variation.id,
                            option_value_id=option_value_id
                        )
                        db.session.add(pvov)
                        print(f"  Created link: {option_value_name} (ID: {option_value_id})")
                    else:
                        print(f"  Warning: Option value '{option_value_name}' not found!")
            else:
                print(f"  Warning: No links defined for variation {variation.id}")
        
        # Сохраняем изменения
        try:
            db.session.commit()
            print("\n=== CHANGES SAVED SUCCESSFULLY ===")
        except Exception as e:
            db.session.rollback()
            print(f"\n=== ERROR SAVING CHANGES: {e} ===")
        
        # Проверяем результат
        print("\n=== VERIFICATION ===")
        for variation in variations:
            pvovs = ProductVariationOptionValue.query.filter_by(variation_id=variation.id).all()
            print(f"Variation {variation.id}: {len(pvovs)} option values")
            for pvov in pvovs:
                option_value = ProductOptionValue.query.get(pvov.option_value_id)
                if option_value:
                    print(f"  - {option_value.value}")

if __name__ == "__main__":
    fix_variations() 