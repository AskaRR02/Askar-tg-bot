from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from utils.helpers import get_or_create_user

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    
    await message.answer(
        f"Это бот для обучения кибербезопасности.\n\n"
        f"<b>Что умеет бот:</b>\n"
        f"• Тесты по основам безопасности\n"
        f"• Проверка файлов на вирусы\n"
        f"• Проверка паролей на утечки\n"
        f"• Симуляция фишинг-атак\n"
        f"• Отслеживание прогресса\n\n"
        f"<b>Команды:</b>\n"
        f"/test — пройти тест\n"
        f"/upload — проверить файл\n"
        f"/check_password — проверить пароль\n"
        f"/phishing — симуляция фишинга\n"
        f"/progress — ваш прогресс\n"
        f"/help — справка"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        f"<b>Справка по боту</b>\n\n"
        f"<b>/start</b> — начало работы\n"
        f"<b>/test</b> — тесты по темам:\n"
        f"  • Пароли\n"
        f"  • Фишинг\n"
        f"  • Сетевая безопасность\n\n"
        f"<b>/upload</b> — проверка файла через VirusTotal\n\n"
        f"<b>/check_password</b> — безопасная проверка пароля на утечки\n\n"
        f"<b>/phishing</b> — учимся распознавать фишинг\n\n"
        f"<b>/progress</b> — ваша статистика и рекомендации\n\n"
        f"<i>Практические тренировки — лучший способ научиться защищаться</i>"
    ) 