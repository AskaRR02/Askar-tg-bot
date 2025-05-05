import os
import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import MAX_FILE_SIZE
from utils.helpers import get_or_create_user, sanitize_filename
from services.virus_total import scan_file

router = Router()


class UploadStates(StatesGroup):
    waiting_for_file = State()
    processing = State()


@router.message(Command("upload"))
async def cmd_upload(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UploadStates.waiting_for_file)
    
    await message.answer(
        f"<b>Проверка файла на вирусы</b>\n\n"
        f"Отправьте файл для проверки через VirusTotal.\n"
        f"Максимальный размер: {MAX_FILE_SIZE // (1024 * 1024)} МБ"
    )


@router.message(UploadStates.waiting_for_file, F.document)
async def process_file(message: Message, state: FSMContext, session: AsyncSession):
    user = await get_or_create_user(session, message.from_user.id)
    
    if message.document.file_size > MAX_FILE_SIZE:
        await message.answer(
            f"<b>Файл слишком большой</b>\n\n"
            f"Лимит размера: {MAX_FILE_SIZE // (1024 * 1024)} МБ\n"
            f"Размер вашего файла: {message.document.file_size // (1024 * 1024)} МБ"
        )
        return
    
    await state.set_state(UploadStates.processing)
    
    await state.update_data(
        file_id=message.document.file_id,
        file_name=message.document.file_name,
        file_size=message.document.file_size
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Отменить сканирование", callback_data="cancel_scan")
    
    status_message = await message.answer(
        f"<b>Загружаю файл... (0%)</b>\n\n"
        f"Размер файла: {message.document.file_size // 1024} КБ\n"
        f"Файл: {message.document.file_name}\n\n"
        f"<i>Сканирование больших файлов может занять несколько минут.</i>",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(status_message_id=status_message.message_id)
    
    try:
        file = await message.bot.get_file(message.document.file_id)
        file_path = file.file_path
        
        await status_message.edit_text(
            f"<b>Загружаю файл... (50%)</b>\n\n"
            f"Размер файла: {message.document.file_size // 1024} КБ\n"
            f"Файл: {message.document.file_name}\n\n"
            f"<i>Сканирование больших файлов может занять несколько минут.</i>",
            reply_markup=builder.as_markup()
        )
        
        file_content = await message.bot.download_file(file_path)
        filename = sanitize_filename(message.document.file_name)
        
        await status_message.edit_text(
            f"<b>Анализирую файл...</b>\n\n"
            f"Файл загружен и отправлен на анализ в VirusTotal.\n"
            f"Ожидаем результаты сканирования...\n\n"
            f"<i>Это может занять несколько минут для больших файлов.</i>",
            reply_markup=builder.as_markup()
        )
        
        scan_task = asyncio.create_task(scan_file(file_content.read(), filename))
        
        dots = 0
        for i in range(30):
            if scan_task.done():
                break
                
            dots = (dots + 1) % 4
            dot_text = "." * dots
            
            current_state = await state.get_state()
            if current_state != UploadStates.processing:
                scan_task.cancel()
                logging.info(f"Сканирование отменено пользователем: {message.from_user.id}")
                return
                
            try:
                await status_message.edit_text(
                    f"<b>Анализирую файл{dot_text}</b>\n\n"
                    f"Файл загружен и отправлен на анализ в VirusTotal.\n"
                    f"Ожидаем результаты сканирования... ({i+1}/30)\n\n"
                    f"<i>Это может занять несколько минут для больших файлов.</i>",
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                logging.error(f"Ошибка при обновлении статуса: {e}")
            
            await asyncio.sleep(10)
        
        if not scan_task.done():
            scan_task.cancel()
            await status_message.edit_text(
                f"<b>Превышено время ожидания</b>\n\n"
                f"Сканирование файла заняло слишком много времени.\n"
                f"Попробуйте файл меньшего размера или повторите позже с помощью команды /upload"
            )
            return
            
        result = await scan_task
        
        if result["error"]:
            await status_message.edit_text(
                f"<b>Ошибка при сканировании</b>\n\n"
                f"{result['message']}\n\n"
                f"Попробуйте другой файл или повторите позже с помощью команды /upload"
            )
        else:
            threat_level = result["data"]["threat_level"]
            detection_ratio = result["data"]["detection_ratio"]
            
            status_emoji = "🟢"
            if threat_level == "Вредоносно":
                status_emoji = "🔴"
            elif threat_level == "Подозрительно":
                status_emoji = "🟠"
            
            detections = ""
            if result["data"]["malicious"] > 0 or result["data"]["suspicious"] > 0:
                detections = f"\n\n<b>Обнаружения:</b>\n"
                for engine in result["data"]["detection_engines"]:
                    detections += f"• {engine['name']}: {engine['result']}\n"
            
            await status_message.edit_text(
                f"<b>Отчёт по файлу: {filename}</b>\n\n"
                f"{status_emoji} <b>Статус:</b> {threat_level}\n"
                f"Обнаружен: {detection_ratio} антивирусами\n"
                f"{detections}\n"
                f"Для проверки другого файла используйте /upload"
            )
    
    except Exception as e:
        logging.exception(f"Ошибка при обработке файла: {str(e)}")
        await status_message.edit_text(
            f"<b>Произошла ошибка при обработке файла</b>\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"Попробуйте снова с командой /upload"
        )
    
    finally:
        await state.clear()


@router.callback_query(UploadStates.processing, F.data == "cancel_scan")
async def cancel_scan(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Операция отменена")
    await state.clear()
    
    await callback.message.edit_text(
        f"<b>Сканирование отменено</b>\n\n"
        f"Вы можете попробовать снова с командой /upload"
    )


@router.message(UploadStates.waiting_for_file)
async def wrong_upload(message: Message):
    await message.answer(
        f"<b>Нужен файл</b>\n\n"
        f"Пожалуйста, отправьте файл для проверки.\n"
        f"Для отмены используйте /cancel"
    ) 