import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional

from config import VIRUSTOTAL_API_KEY


async def scan_file(file_content: bytes, filename: str) -> Dict[str, Any]:
    if not VIRUSTOTAL_API_KEY:
        return {
            "error": True,
            "message": "API ключ VirusTotal не настроен.",
            "data": None
        }
    
    try:
        url = "https://www.virustotal.com/api/v3/files"
        headers = {
            "x-apikey": VIRUSTOTAL_API_KEY,
            "accept": "application/json"
        }
        
        # Используем FormData для корректной передачи файла
        form_data = aiohttp.FormData()
        form_data.add_field('file', file_content, filename=filename)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=form_data) as response:
                if response.status == 200:
                    result = await response.json()
                    analysis_id = result.get("data", {}).get("id")
                    if analysis_id:
                        return await get_analysis_result(analysis_id)
                    else:
                        return {
                            "error": True,
                            "message": "Не удалось получить ID анализа.",
                            "data": None
                        }
                else:
                    response_text = await response.text()
                    return {
                        "error": True,
                        "message": f"Ошибка при сканировании файла: {response.status}. Ответ: {response_text[:100]}",
                        "data": None
                    }
    except Exception as e:
        return {
            "error": True,
            "message": f"Произошла ошибка при сканировании файла: {str(e)}",
            "data": None
        }


async def get_analysis_result(analysis_id: str) -> Dict[str, Any]:
    attempts = 0
    max_attempts = 10
    
    while attempts < max_attempts:
        try:
            url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
            headers = {
                "x-apikey": VIRUSTOTAL_API_KEY
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        status = result.get("data", {}).get("attributes", {}).get("status")
                        
                        if status == "completed":
                            return process_completed_analysis(result)
                        elif status == "queued" or status == "in-progress":
                            attempts += 1
                            await asyncio.sleep(10)  # Wait 10 seconds before next attempt
                            continue
                        else:
                            return {
                                "error": True,
                                "message": f"Неизвестный статус анализа: {status}",
                                "data": None
                            }
                    else:
                        return {
                            "error": True,
                            "message": f"Ошибка при получении результатов анализа: {response.status}",
                            "data": None
                        }
        except Exception as e:
            return {
                "error": True,
                "message": f"Произошла ошибка при получении результатов анализа: {str(e)}",
                "data": None
            }
    
    return {
        "error": True,
        "message": "Истекло время ожидания результатов анализа.",
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
                "detection_engines": detection_engines[:5]  # Return top 5 detections
            }
        }
    except Exception as e:
        return {
            "error": True,
            "message": f"Ошибка при обработке результатов анализа: {str(e)}",
            "data": None
        } 