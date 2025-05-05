from typing import Dict, List, Union, Optional, Any

TEST_DATA = {
    "password_security": {
        "name": "Пароли",
        "questions": [
            {
                "id": 1,
                "text": "Какой пароль надёжнее?",
                "options": [
                    "password123",
                    "P@ssw0rd!",
                    "TH3r$_1s_n0_Sp00n!",
                    "qwerty123"
                ],
                "correct": 2,
                "explanation": "Длинный пароль со специальными символами, цифрами и буквами разного регистра сложнее взломать."
            },
            {
                "id": 2,
                "text": "Как часто нужно менять пароли?",
                "options": [
                    "Каждые 30 дней",
                    "Каждые 60-90 дней",
                    "Раз в год",
                    "Только если есть подозрения на взлом"
                ],
                "correct": 1,
                "explanation": "Большинство экспертов рекомендуют обновлять пароли каждые 60-90 дней."
            },
            {
                "id": 3,
                "text": "Где безопаснее хранить пароли?",
                "options": [
                    "В текстовом файле на компьютере",
                    "В менеджере паролей с мастер-паролем",
                    "В браузере",
                    "На бумаге в ящике стола"
                ],
                "correct": 1,
                "explanation": "Менеджеры паролей шифруют данные и защищают от большинства типов атак."
            }
        ]
    },
    "phishing": {
        "name": "Фишинг",
        "questions": [
            {
                "id": 1,
                "text": "Что указывает на фишинговое письмо?",
                "options": [
                    "Отправитель — известная компания",
                    "Просьба подтвердить данные",
                    "Орфографические ошибки",
                    "Наличие ссылок"
                ],
                "correct": 2,
                "explanation": "Мошенники часто делают ошибки в тексте. Официальные компании тщательно проверяют сообщения."
            },
            {
                "id": 2,
                "text": "Что делать с подозрительным письмом?",
                "options": [
                    "Открыть в защищённой среде",
                    "Удалить не открывая",
                    "Переслать ИТ-отделу",
                    "Уточнить у отправителя"
                ],
                "correct": 1,
                "explanation": "Никогда не открывайте подозрительные вложения — это может активировать вредоносный код."
            },
            {
                "id": 3,
                "text": "Какая техника использует срочность для манипуляции?",
                "options": [
                    "Претекстинг",
                    "Квид про кво",
                    "Тейлгейтинг",
                    "Вишинг"
                ],
                "correct": 0,
                "explanation": "Претекстинг создаёт ложное чувство срочности: «Срочно подтвердите, иначе заблокируем счёт»."
            }
        ]
    },
    "network_security": {
        "name": "Сетевая безопасность",
        "questions": [
            {
                "id": 1,
                "text": "Какое соединение безопаснее для передачи данных?",
                "options": [
                    "Открытый Wi-Fi",
                    "HTTPS",
                    "HTTP",
                    "FTP"
                ],
                "correct": 1,
                "explanation": "HTTPS шифрует данные. Остальные варианты передают информацию в открытом виде."
            },
            {
                "id": 2,
                "text": "Что такое VPN?",
                "options": [
                    "Виртуальная частная сеть",
                    "Визуальная сеть программирования",
                    "Верифицированный протокол сети",
                    "Вектор постоянного нападения"
                ],
                "correct": 0,
                "explanation": "VPN создаёт зашифрованный туннель между вашим устройством и интернетом."
            },
            {
                "id": 3,
                "text": "Какая атака перегружает сервер множеством запросов?",
                "options": [
                    "Man-in-the-Middle",
                    "Фишинг",
                    "DDoS",
                    "Брутфорс"
                ],
                "correct": 2,
                "explanation": "DDoS (Distributed Denial of Service) атака перегружает систему запросами с разных устройств."
            }
        ]
    }
}


def get_themes() -> List[Dict[str, str]]:
    return [
        {"id": key, "name": value["name"]}
        for key, value in TEST_DATA.items()
    ]


def get_theme_questions(theme_id: str) -> List[Dict[str, Any]]:
    if theme_id in TEST_DATA:
        return TEST_DATA[theme_id]["questions"]
    return []


def get_question(theme_id: str, question_index: int) -> Optional[Dict[str, Any]]:
    questions = get_theme_questions(theme_id)
    if 0 <= question_index < len(questions):
        return questions[question_index]
    return None


def check_answer(theme_id: str, question_index: int, answer_index: int) -> bool:
    question = get_question(theme_id, question_index)
    if question:
        return answer_index == question["correct"]
    return False


def get_explanation(theme_id: str, question_index: int) -> str:
    question = get_question(theme_id, question_index)
    if question and "explanation" in question:
        return question["explanation"]
    return "Объяснение недоступно."


def calculate_score(theme_id: str, correct_answers: int) -> float:
    total_questions = len(get_theme_questions(theme_id))
    if total_questions > 0:
        return (correct_answers / total_questions) * 100
    return 0


def get_recommendations(scores: Dict[str, float]) -> List[str]:
    recommendations = []
    
    if "password_security" in scores and scores["password_security"] < 70:
        recommendations.append("Изучите основы управления паролями. Используйте менеджер паролей и двухфакторную аутентификацию.")
    
    if "phishing" in scores and scores["phishing"] < 70:
        recommendations.append("Тренируйтесь распознавать фишинг. Проверяйте отправителей писем и не переходите по подозрительным ссылкам.")
    
    if "network_security" in scores and scores["network_security"] < 70:
        recommendations.append("Используйте HTTPS-соединения и VPN в публичных сетях. Обновляйте программы и устройства.")
    
    if not recommendations:
        recommendations.append("У вас хороший уровень знаний. Продолжайте следить за новостями кибербезопасности.")
    
    return recommendations 