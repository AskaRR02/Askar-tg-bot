from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from utils.helpers import get_or_create_user, get_or_create_session, update_session, save_test_result
from services.test_engine import (
    get_themes, get_theme_questions, get_question, check_answer, 
    get_explanation, calculate_score, get_recommendations
)

router = Router()


class TestStates(StatesGroup):
    selecting_theme = State()
    answering = State()
    summary = State()


@router.message(Command("test"))
async def cmd_test(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    themes = get_themes()
    builder = InlineKeyboardBuilder()
    
    for theme in themes:
        builder.button(text=theme["name"], callback_data=f"theme:{theme['id']}")
    
    await state.set_state(TestStates.selecting_theme)
    await message.answer(
        f"<b>Выберите тему теста:</b>", 
        reply_markup=builder.as_markup()
    )


@router.callback_query(TestStates.selecting_theme, F.data.startswith("theme:"))
async def select_theme(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    theme_id = callback.data.split(":", 1)[1]
    
    await state.update_data(
        theme_id=theme_id,
        current_question=0,
        correct_answers=0,
        total_questions=len(get_theme_questions(theme_id))
    )
    
    user_session = await get_or_create_session(session, callback.from_user.id)
    await update_session(session, callback.from_user.id, current_theme=theme_id, current_question=0, score=0)
    
    await state.set_state(TestStates.answering)
    await callback.answer()
    
    await send_question(callback.message, state)


async def send_question(message: Message, state: FSMContext):
    data = await state.get_data()
    
    theme_id = data["theme_id"]
    question_index = data["current_question"]
    total_questions = data["total_questions"]
    
    if question_index >= total_questions:
        return
    
    question = get_question(theme_id, question_index)
    
    if not question:
        return
    
    builder = InlineKeyboardBuilder()
    
    for idx, option in enumerate(question["options"]):
        builder.button(text=option, callback_data=f"answer:{idx}")
    
    builder.adjust(1)
    
    await message.answer(
        f"<b>Вопрос {question_index + 1} из {total_questions}</b>\n\n"
        f"{question['text']}",
        reply_markup=builder.as_markup()
    )


@router.callback_query(TestStates.answering, F.data.startswith("answer:"))
async def process_answer(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    answer_idx = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    
    theme_id = data["theme_id"]
    question_index = data["current_question"]
    correct_answers = data["correct_answers"]
    
    is_correct = check_answer(theme_id, question_index, answer_idx)
    explanation = get_explanation(theme_id, question_index)
    
    if is_correct:
        correct_answers += 1
        await callback.answer("Верно!")
        response = f"<b>✓ Правильно!</b> "
    else:
        await callback.answer("Неверно")
        response = f"<b>✗ Неправильно!</b> "
    
    await state.update_data(
        current_question=question_index + 1,
        correct_answers=correct_answers
    )
    
    await update_session(
        session, 
        callback.from_user.id, 
        current_question=question_index + 1, 
        score=correct_answers
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Далее →", callback_data="next_question")
    
    await callback.message.answer(
        f"{response}{explanation}", 
        reply_markup=builder.as_markup()
    )


@router.callback_query(TestStates.answering, F.data == "next_question")
async def next_question(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    
    question_index = data["current_question"]
    total_questions = data["total_questions"]
    
    if question_index >= total_questions:
        await finish_test(callback.message, state, session)
        return
        
    await send_question(callback.message, state)


async def finish_test(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    
    theme_id = data["theme_id"]
    correct_answers = data["correct_answers"]
    total_questions = data["total_questions"]
    
    score = calculate_score(theme_id, correct_answers)
    
    user_id = message.chat.id
    await save_test_result(session, user_id, theme_id, score)
    
    theme_name = next((t["name"] for t in get_themes() if t["id"] == theme_id), "Неизвестная тема")
    
    await state.set_state(TestStates.summary)
    
    result_text = ""
    if score >= 80:
        result_text = f"<b>Отличный результат!</b> Вы хорошо разбираетесь в этой теме."
    elif score >= 50:
        result_text = f"<b>Неплохой результат.</b> Есть некоторые пробелы в знаниях."
    else:
        result_text = f"<b>Стоит подучить эту тему.</b> Ознакомьтесь с материалами по кибербезопасности."
    
    await message.answer(
        f"<b>Результаты теста: {theme_name}</b>\n\n"
        f"Правильных ответов: {correct_answers} из {total_questions}\n"
        f"Ваш результат: {score:.1f}%\n\n"
        f"{result_text}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Пройти ещё тест", callback_data="restart_test")
    builder.button(text="Вернуться в главное меню", callback_data="back_to_start")
    builder.adjust(1)
    
    await message.answer(
        "Что дальше?",
        reply_markup=builder.as_markup()
    )


@router.callback_query(TestStates.summary, F.data == "restart_test")
async def restart_test(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    await cmd_test(callback.message, state, session)


@router.callback_query(TestStates.summary, F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        f"<b>Главное меню</b>\n\n"
        f"Команды:\n"
        f"/test - пройти тест\n"
        f"/phishing - симулятор фишинга\n"
        f"/upload - проверить файл на вирусы\n"
        f"/password - проверить надежность пароля\n"
        f"/progress - ваш прогресс"
    ) 