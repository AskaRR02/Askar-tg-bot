from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import bold, italic, code
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.models import User, TestResult, PhishingLog
from utils.helpers import get_or_create_user, get_user_progress
from services.test_engine import get_themes, get_recommendations

router = Router()


@router.message(Command("progress"))
async def cmd_progress(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    # Получаем прогресс пользователя
    progress = await get_user_progress(session, message.from_user.id)
    
    # Получаем статистику по фишингу
    phishing_query = select(PhishingLog).where(PhishingLog.user_id == message.from_user.id)
    phishing_result = await session.execute(phishing_query)
    phishing_logs = phishing_result.scalars().all()
    
    total_phishing = len(phishing_logs)
    clicked_phishing = sum(1 for log in phishing_logs if log.clicked)
    
    # Формируем текст сообщения
    themes = get_themes()
    theme_names = {theme["id"]: theme["name"] for theme in themes}
    
    completed_themes_text = ""
    if progress["completed_themes"]:
        for theme_id in progress["completed_themes"]:
            theme_name = theme_names.get(theme_id, theme_id)
            score = progress["scores"][theme_id]
            completed_themes_text += f"• {theme_name}: {score:.1f}%\n"
    else:
        completed_themes_text = "Вы еще не прошли ни одного теста\n"
    
    # Формируем текст по фишингу
    phishing_text = ""
    if total_phishing > 0:
        success_rate = 100 - (clicked_phishing / total_phishing * 100)
        phishing_text = (
            f"Симуляции: {total_phishing}\n"
            f"Распознано: {total_phishing - clicked_phishing} ({success_rate:.1f}%)\n"
        )
    else:
        phishing_text = "Вы еще не проходили симуляции фишинга\n"
    
    # Формируем рекомендации
    recommendations = get_recommendations(progress["scores"])
    recommendations_text = "\n".join([f"• {rec}" for rec in recommendations])
    
    # Итоговое сообщение
    username = message.from_user.username or f"ID{message.from_user.id}"
    
    await message.answer(
        f"{bold('Ваш прогресс')}\n\n"
        f"{bold('Пройденные тесты:')}\n{completed_themes_text}\n"
        f"{bold('Фишинг:')}\n{phishing_text}\n"
        f"{bold('Рекомендации:')}\n{recommendations_text}\n\n"
        f"{italic('Используйте /test для прохождения тестов по разным темам')}",
        parse_mode="HTML"
    ) 