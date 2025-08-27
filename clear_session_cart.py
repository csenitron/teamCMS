#!/usr/bin/env python3
"""
Скрипт для очистки сессионной корзины
Запускать: python clear_session_cart.py
"""

import os
import glob

def clear_session_cart():
    """Очистить сессионную корзину, удалив файлы сессий"""
    try:
        # Находим все файлы сессий Flask
        session_files = glob.glob('flask_session/*')
        
        if not session_files:
            print("Файлы сессий не найдены.")
            return
            
        # Удаляем файлы сессий
        for session_file in session_files:
            try:
                os.remove(session_file)
                print(f"Удален файл сессии: {session_file}")
            except Exception as e:
                print(f"Ошибка при удалении {session_file}: {e}")
        
        print(f"Сессионная корзина очищена. Удалено {len(session_files)} файлов сессий.")
        
    except Exception as e:
        print(f"Ошибка при очистке сессионной корзины: {e}")

if __name__ == "__main__":
    clear_session_cart() 