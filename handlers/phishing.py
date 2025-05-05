from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, URLInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import PhishingLog
from utils.helpers import get_or_create_user, generate_phishing_link
from services.phishing_scenarios import get_scenarios, get_scenario

router = Router()


class PhishingStates(StatesGroup):
    selecting_scenario = State()
    simulating = State()
    education = State()


@router.message(Command("phishing"))
async def cmd_phishing(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    await message.answer(
        f"<b>Симулятор фишинга</b>\n\n"
        f"Здесь вы научитесь распознавать опасные сообщения и ссылки.\n\n"
        f"<i>Все примеры учебные и не представляют реальной угрозы.</i>"
    )
    
    scenarios = get_scenarios()
    builder = InlineKeyboardBuilder()
    
    for scenario in scenarios:
        builder.button(text=scenario["name"], callback_data=f"scenario:{scenario['id']}")
    
    builder.adjust(1)
    
    await state.set_state(PhishingStates.selecting_scenario)
    await message.answer(
        f"<b>Выберите сценарий:</b>", 
        reply_markup=builder.as_markup()
    )


@router.callback_query(PhishingStates.selecting_scenario, F.data.startswith("scenario:"))
async def select_scenario(callback: CallbackQuery, state: FSMContext):
    scenario_id = callback.data.split(":", 1)[1]
    scenario = get_scenario(scenario_id)
    
    if not scenario:
        await callback.answer("Сценарий не найден", show_alert=True)
        return
    
    phishing_link = generate_phishing_link()
    
    await state.update_data(
        scenario_id=scenario_id,
        phishing_link=phishing_link
    )
    
    message_text = scenario["message"].format(phishing_link=phishing_link)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Перейти по ссылке", callback_data="click_phishing")
    builder.button(text="Это фишинг?", callback_data="report_phishing")
    
    await state.set_state(PhishingStates.simulating)
    await callback.message.answer(message_text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(PhishingStates.simulating, F.data == "click_phishing")
async def click_phishing(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    phishing_log = PhishingLog(user_id=callback.from_user.id, clicked=True)
    session.add(phishing_log)
    await session.commit()
    
    await callback.answer("Вы перешли по фишинговой ссылке!", show_alert=True)
    
    await callback.message.answer(
        f"<b>Внимание! Вы перешли по фишинговой ссылке!</b>\n\n"
        f"В реальной ситуации это могло привести к:\n"
        f"• Краже личных данных\n"
        f"• Заражению устройства вирусами\n"
        f"• Потере доступа к аккаунтам\n\n"
        f"Нажмите «Это фишинг?», чтобы научиться распознавать такие угрозы."
    )


@router.callback_query(PhishingStates.simulating, F.data == "report_phishing")
async def report_phishing(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    scenario_id = data["scenario_id"]
    scenario = get_scenario(scenario_id)
    
    phishing_log = PhishingLog(user_id=callback.from_user.id, clicked=False)
    session.add(phishing_log)
    await session.commit()
    
    await callback.answer("Верно! Вы распознали фишинг.", show_alert=True)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Изучить признаки фишинга", callback_data="show_education")
    
    await callback.message.answer(
        f"<b>Правильно!</b>\n\n"
        f"Вы успешно идентифицировали фишинговое сообщение.\n\n"
        f"Теперь давайте разберем, какие признаки помогают распознать подобные атаки.",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(PhishingStates.education)


@router.callback_query(PhishingStates.education, F.data == "show_education")
async def show_education(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    scenario_id = data["scenario_id"]
    scenario = get_scenario(scenario_id)
    
    signs_text = "\n".join([f"• {sign}" for sign in scenario["signs"]])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Попробовать другой сценарий", callback_data="restart_phishing")
    
    await callback.message.answer(
        f"<b>Признаки фишинга — {scenario['name']}</b>:\n\n"
        f"{signs_text}\n\n"
        f"<i>Запомните эти признаки для защиты в реальных ситуациях</i>",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data == "restart_phishing")
async def restart_phishing(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    await cmd_phishing(callback.message, state, session) 