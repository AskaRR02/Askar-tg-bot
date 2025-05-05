import hashlib
import aiohttp
from typing import Dict, Any, Tuple


async def check_password(password: str) -> Dict[str, Any]:
    """
    Проверяет пароль через Pwned Passwords API, используя k-анонимность
    
    Args:
        password: Пароль для проверки
        
    Returns:
        Dict с информацией о безопасности пароля
    """
    try:
        # Преобразуем пароль в SHA-1 хеш (верхний регистр)
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        
        # Разделяем хеш на первые 5 символов и остаток
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        # Запрашиваем данные с API
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.pwnedpasswords.com/range/{prefix}', 
                                  headers={'User-Agent': 'CyberSecurityBot'}) as response:
                
                if response.status != 200:
                    return {
                        "success": False,
                        "message": "Не удалось подключиться к API. Попробуйте позже.",
                        "found": False,
                        "count": 0
                    }
                
                # Получаем текстовый ответ
                hashes_data = await response.text()
                
                # Ищем соответствие в возвращенных хешах
                for line in hashes_data.splitlines():
                    # Строки имеют формат SUFFIX:COUNT
                    parts = line.split(':')
                    
                    if len(parts) != 2:
                        continue
                        
                    hash_suffix, count = parts[0], int(parts[1])
                    
                    if hash_suffix == suffix:
                        return {
                            "success": True,
                            "message": f"Пароль найден в {count:,} утечках!",
                            "found": True,
                            "count": count
                        }
                
                # Если соответствие не найдено
                return {
                    "success": True,
                    "message": "Пароль не найден в известных утечках данных.",
                    "found": False,
                    "count": 0
                }
                
    except Exception as e:
        return {
            "success": False,
            "message": "Произошла ошибка при проверке пароля. Попробуйте позже.",
            "found": False,
            "count": 0,
            "error": str(e)
        } 