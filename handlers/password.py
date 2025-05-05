from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from utils.helpers import get_or_create_user
from services.pwned_passwords import check_password

router = Router()


class PasswordStates(StatesGroup):
    waiting_for_password = State()


@router.message(Command("check_password"))
async def cmd_check_password(message: Message, state: FSMContext):
    await state.clear()
    
    # Пытаемся удалить сообщение пользователя, чтобы скрыть команду
    try:
        await message.delete()
    except Exception:
        pass
    
    await state.set_state(PasswordStates.waiting_for_password)
    
    # Отправляем личное сообщение с инструкцией
    await message.answer(
        f"<b>Проверка пароля на утечки</b>\n\n"
        f"Отправьте пароль, который хотите проверить.\n\n"
        f"<i>Сервис проверяет только хеш пароля (SHA-1), а не сам пароль.</i>\n"
        f"<i>Мы не храним введённые пароли.</i>\n\n"
        f"Для отмены: /cancel"
    )


@router.message(PasswordStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext, session: AsyncSession):
    # Пытаемся удалить сообщение пользователя для безопасности
    try:
        await message.delete()
    except Exception:
        pass
    
    await state.clear()
    
    user = await get_or_create_user(session, message.from_user.id)
    password = message.text
    
    # Если пароль не был предоставлен или пустой
    if not password or len(password) == 0:
        await message.answer(
            f"<b>Ошибка</b>\n\n"
            f"Пароль не может быть пустым.\n"
            f"Попробуйте снова: /check_password"
        )
        return
    
    # Отправляем временное сообщение
    status_message = await message.answer(
        f"<b>Проверяю пароль...</b>"
    )
    
    # Проверяем пароль через API
    result = await check_password(password)
    
    if not result["success"]:
        await status_message.edit_text(
            f"<b>Ошибка при проверке</b>\n\n"
            f"{result['message']}\n\n"
            f"Попробуйте позже или используйте другой пароль."
        )
        return
    
    if result["found"]:
        count = result["count"]
        level = "Критическая опасность!" if count > 1000 else "Опасность!" if count > 100 else "Предупреждение"
        
        await status_message.edit_text(
            f"<b>{level}</b>\n\n"
            f"Этот пароль найден в <code>{count:,}</code> утечках данных!\n\n"
            f"<b>Рекомендации:</b>\n"
            f"• Немедленно смените этот пароль везде, где вы его используете\n"
            f"• Не используйте одинаковые пароли на разных сайтах\n"
            f"• Создавайте надёжные пароли из 12+ символов\n"
            f"• Используйте менеджер паролей\n\n"
            f"<i>Хотите проверить другой пароль? Используйте /check_password</i>"
        )
    else:
        await status_message.edit_text(
            f"<b>Пароль не найден в утечках</b>\n\n"
            f"Хорошая новость! Этот пароль не обнаружен в известных утечках данных.\n\n"
            f"<b>Помните:</b>\n"
            f"• Даже если пароль не найден, он может быть ненадёжным\n"
            f"• Используйте уникальные пароли для каждого сервиса\n"
            f"• Включите двухфакторную аутентификацию где возможно\n\n"
            f"<i>Хотите проверить другой пароль? Используйте /check_password</i>"
        )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state is None:
        return
    
    await state.clear()
    await message.answer(
        f"<b>Операция отменена</b>\n\n"
        f"Вы можете начать заново, используя соответствующую команду."
    ) 