import aiohttp
import asyncio
import logging
import json
from typing import Dict, Any, Optional

from config import VIRUSTOTAL_API_KEY


async def scan_file(file_content: bytes, filename: str) -> Dict[str, Any]:
    if not VIRUSTOTAL_API_KEY:
        logging.error("API ключ VirusTotal не настроен")
        return {
            "error": True,
            "message": "API ключ VirusTotal не настроен.",
            "data": None
        }
    
    try:
        logging.info(f"Начало сканирования файла: {filename} (размер: {len(file_content)} байт)")
        url = "https://www.virustotal.com/api/v3/files"
        headers = {
            "x-apikey": VIRUSTOTAL_API_KEY,
            "accept": "application/json"
        }
        
        form_data = aiohttp.FormData()
        form_data.add_field('file', file_content, filename=filename)
        
        timeout = aiohttp.ClientTimeout(total=300)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logging.info(f"Отправка файла {filename} на сервер VirusTotal...")
            async with session.post(url, headers=headers, data=form_data) as response:
                logging.info(f"Получен ответ от VirusTotal: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    logging.info("Успешно получен ответ от VirusTotal API")
                    analysis_id = result.get("data", {}).get("id")
                    
                    if analysis_id:
                        logging.info(f"Получен ID анализа: {analysis_id}")
                        return await get_analysis_result(analysis_id)
                    else:
                        logging.error("Не удалось получить ID анализа в ответе API")
                        return {
                            "error": True,
                            "message": "Не удалось получить ID анализа.",
                            "data": None
                        }
                else:
                    response_text = await response.text()
                    logging.error(f"Ошибка при сканировании файла: {response.status}, ответ: {response_text[:200]}")
                    return {
                        "error": True,
                        "message": f"Ошибка при сканировании файла: {response.status}. Ответ: {response_text[:100]}",
                        "data": None
                    }
    except asyncio.TimeoutError:
        logging.error(f"Превышено время ожидания ответа от VirusTotal при сканировании файла {filename}")
        return {
            "error": True,
            "message": "Превышено время ожидания ответа от сервера. Возможно, файл слишком большой.",
            "data": None
        }
    except Exception as e:
        logging.exception(f"Исключение при сканировании файла: {str(e)}")
        return {
            "error": True,
            "message": f"Произошла ошибка при сканировании файла: {str(e)}",
            "data": None
        }


async def get_analysis_result(analysis_id: str) -> Dict[str, Any]:
    attempts = 0
    max_attempts = 15
    retry_delay = 10
    
    logging.info(f"Запрашиваем результат анализа {analysis_id}, макс. попыток: {max_attempts}")
    
    while attempts < max_attempts:
        try:
            url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
            headers = {
                "x-apikey": VIRUSTOTAL_API_KEY,
                "accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                logging.info(f"Попытка {attempts+1}/{max_attempts} получения результата анализа")
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        status = result.get("data", {}).get("attributes", {}).get("status")
                        logging.info(f"Статус анализа: {status}")
                        
                        if status == "completed":
                            logging.info("Анализ завершен успешно")
                            return process_completed_analysis(result)
                        elif status == "queued" or status == "in-progress":
                            attempts += 1
                            wait_time = min(retry_delay * attempts, 30)
                            logging.info(f"Анализ еще в процессе ({status}), ожидаем {wait_time} секунд")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logging.error(f"Неизвестный статус анализа: {status}")
                            return {
                                "error": True,
                                "message": f"Неизвестный статус анализа: {status}",
                                "data": None
                            }
                    else:
                        response_text = await response.text()
                        logging.error(f"Ошибка при получении результатов анализа: {response.status}, ответ: {response_text[:200]}")
                        return {
                            "error": True,
                            "message": f"Ошибка при получении результатов анализа: {response.status}",
                            "data": None
                        }
        except Exception as e:
            logging.exception(f"Исключение при получении результатов анализа: {str(e)}")
            return {
                "error": True,
                "message": f"Произошла ошибка при получении результатов анализа: {str(e)}",
                "data": None
            }
    
    logging.warning(f"Превышено максимальное количество попыток ({max_attempts}) для получения результата анализа")
    return {
        "error": True,
        "message": "Истекло время ожидания результатов анализа. Файл слишком большой или сервис перегружен.",
        "data": None
    }


def process_completed_analysis(result: Dict[str, Any]) -> Dict[str, Any]:
    try:
        attributes = result.get("data", {}).get("attributes", {})
        stats = attributes.get("stats", {})
        results = attributes.get("results", {})
        
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        total = stats.get("undetected", 0) + malicious + suspicious
        
        logging.info(f"Анализ обнаружил: malicious={malicious}, suspicious={suspicious}, total={total}")
        
        detection_engines = []
        for engine, detection in results.items():
            if detection.get("category") in ["malicious", "suspicious"]:
                detection_engines.append({
                    "name": engine,
                    "result": detection.get("result", "Неизвестно")
                })
        
        threat_level = "Безопасно"
        if malicious > 0:
            threat_level = "Вредоносно"
        elif suspicious > 0:
            threat_level = "Подозрительно"
        
        detection_ratio = f"{malicious + suspicious}/{total}" if total > 0 else "0/0"
        
        return {
            "error": False,
            "message": "Анализ файла успешно завершен.",
            "data": {
                "threat_level": threat_level,
                "detection_ratio": detection_ratio,
                "malicious": malicious,
                "suspicious": suspicious,
                "detection_engines": detection_engines[:5]
            }
        }
    except Exception as e:
        logging.exception(f"Ошибка при обработке результатов анализа: {str(e)}")
        return {
            "error": True,
            "message": f"Ошибка при обработке результатов анализа: {str(e)}",
            "data": None
        } 