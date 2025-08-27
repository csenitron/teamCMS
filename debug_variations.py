#!/usr/bin/env python3
"""
Скрипт для отладки вариаций в базе данных
Запускать: python debug_variations.py
"""

from app import create_app
from app.extensions import db
from app.models.productOptions import ProductVariation, ProductVariationOptionValue, ProductOptionValue

def debug_variations():
    """Отладка вариаций в базе данных"""
    app = create_app()
    
    with app.app_context():
        print("=== DEBUG VARIATIONS ===")
        
        # Получаем все вариации для товара с ID 6
        product_id = 6
        variations = ProductVariation.query.filter_by(product_id=product_id).all()
        
        print(f"Found {len(variations)} variations for product {product_id}")
        
        for variation in variations:
            print(f"\n--- Variation {variation.id} ---")
            print(f"Price: {variation.price}")
            print(f"SKU: {variation.sku}")
            print(f"Stock: {variation.stock}")
            
            # Получаем связанные значения опций
            pvovs = ProductVariationOptionValue.query.filter_by(variation_id=variation.id).all()
            print(f"Option values count: {len(pvovs)}")
            
            for pvov in pvovs:
                option_value = ProductOptionValue.query.get(pvov.option_value_id)
                if option_value:
                    print(f"  Option value: {option_value.id} -> {option_value.value}")
                else:
                    print(f"  Option value {pvov.option_value_id} not found!")
        
        # Также проверим все значения опций
        print(f"\n=== ALL OPTION VALUES ===")
        option_values = ProductOptionValue.query.all()
        for ov in option_values:
            print(f"Option value {ov.id}: {ov.value}")

if __name__ == "__main__":
    debug_variations() 