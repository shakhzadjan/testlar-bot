from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import sqlite3
import random
import csv
import os
from openpyxl import Workbook
from config import DB_NAME, QUESTIONS_PER_QUIZ, POINTS_PER_ANSWER, ADMIN_ID
from database import get_random_questions, save_result, get_stats, get_all_results

router = Router()

class RegistrationState(StatesGroup):
    waiting_for_language = State()
    waiting_for_name = State()
    waiting_for_group = State()

class QuizState(StatesGroup):
    answering = State()

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    print(f"DEBUG: Admin command from user_id={message.from_user.id}")
    if message.from_user.id != ADMIN_ID:
        print(f"DEBUG: Access denied. Expected ADMIN_ID={ADMIN_ID}")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistika", callback_data="admin_stats")
    builder.button(text="📝 Natijalar ro'yxati", callback_data="admin_results")
    builder.button(text="📥 Natijalarni yuklash (CSV)", callback_data="admin_export")
    builder.adjust(1)
    
    await message.answer("Admin panelga xush kelibsiz:", reply_markup=builder.as_markup())

@router.callback_query(F.data == "admin_stats")
async def handle_admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
        
    unique_users, total_quizzes, avg_score = get_stats()
    text = (
        f"📊 Bot statistikasi:\n\n"
        f"👤 Noyob foydalanuvchilar: {unique_users}\n"
        f"📝 Jami topshirilgan testlar: {total_quizzes}\n"
        f"🎯 O'rtacha ball: {avg_score if avg_score else 0:.1f}"
    )
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "admin_results")
async def handle_admin_results(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
        
    results = get_all_results()
    if not results:
        await callback.message.answer("Hozircha natijalar yo'q.")
        await callback.answer()
        return
        
    # Faqat oxirgi 10 ta natijani ko'rsatamiz (xabar hajmi cheklanganligi sababli)
    top_results = results[:15]
    
    text = "📝 Oxirgi natijalar:\n\n"
    text += "👤 F.I.SH | Guruh | Ball | Sana\n"
    text += "--------------------------------\n"
    
    for res in top_results:
        # res = (full_name, group_name, score, total_questions, timestamp)
        name = res[0][:15] # Ismni qisqartirish
        group = res[1][:10]
        score = res[2]
        date = res[4].split()[0] # Faqat sana (YYYY-MM-DD)
        
        text += f"{name} | {group} | {score} | {date}\n"
        
    if len(results) > 15:
        text += "\n...(barcha natijalarni CSV orqali yuklab oling)"
        
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "admin_export")
async def handle_admin_export(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
        
    results = get_all_results()
    if not results:
        await callback.message.answer("Hozircha natijalar yo'q.")
        await callback.answer()
        return
        
    file_path = "results.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Natijalar"
    
    # Sarlavhalar
    headers = ["F.I.SH", "Guruh", "Ball", "Jami savol", "Sana"]
    ws.append(headers)
    
    # Ma'lumotlarni yozish
    for row in results:
        ws.append(list(row))
        
    # Ustun kengliklarini moslash (ixtiyoriy, lekin chiroyli chiqadi)
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = length + 2

    wb.save(file_path)
        
    file = types.FSInputFile(file_path)
    await callback.message.answer_document(file, caption="Barcha natijalar (Excel formatida)")
    os.remove(file_path)
    await callback.answer()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Assalomu alaykum! Quiz botga xush kelibsiz.\n"
        f"Iltimos, testni boshlash uchun /quiz buyrug'ini bering.\n\n"
        f"Здравствуйте! Добро пожаловать в Quiz бот.\n"
        f"Пожалуйста, введите команду /quiz, чтобы начать тест."
    )

@router.message(Command("quiz"))
async def cmd_quiz(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(2)
    
    await message.answer("Iltimos, test tilini tanlang:\nПожалуйста, выберите язык теста:", reply_markup=builder.as_markup())
    await state.set_state(RegistrationState.waiting_for_language)

@router.callback_query(RegistrationState.waiting_for_language, F.data.startswith("lang_"))
async def process_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data[5:]
    await state.update_data(language=lang)
    
    text = "Ism va familiyangizni kiriting:" if lang == 'uz' else "Введите ваше имя и фамилию:"
    await callback.message.answer(text)
    await state.set_state(RegistrationState.waiting_for_name)
    await callback.answer()

@router.message(RegistrationState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    data = await state.get_data()
    lang = data.get('language', 'uz')
    
    text = "Guruhingiz nomini kiriting:" if lang == 'uz' else "Введите название вашей группы:"
    await message.answer(text)
    await state.set_state(RegistrationState.waiting_for_group)

@router.message(RegistrationState.waiting_for_group)
async def process_group(message: types.Message, state: FSMContext):
    await state.update_data(group_name=message.text)
    data = await state.get_data()
    lang = data.get('language', 'uz')
    
    questions = get_random_questions(QUESTIONS_PER_QUIZ, language=lang)
    if not questions:
        text = "Xatolik: Ma'lumotlar bazasida savollar topilmadi." if lang == 'uz' else "Ошибка: Вопросы не найдены в базе данных."
        await message.answer(text)
        await state.clear()
        return

    await state.set_state(QuizState.answering)
    await state.update_data(
        questions=questions,
        current_index=0,
        score=0,
        user_answers=[]
    )
    
    if lang == 'uz':
        msg = (
            f"Ma'lumotlar qabul qilindi!\n"
            f"Talaba: {data['full_name']}\n"
            f"Guruh: {data['group_name']}\n\n"
            f"Test boshlanmoqda. Omad!"
        )
    else:
        msg = (
            f"Данные приняты!\n"
            f"Студент: {data['full_name']}\n"
            f"Группа: {data['group_name']}\n\n"
            f"Тест начинается. Удачи!"
        )
    await message.answer(msg)
    await send_question(message, state)

async def send_question(message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'uz')
    q_index = data.get('current_index', 0)
    questions = data.get('questions', [])
    
    if q_index >= len(questions):
        await finish_quiz(message, state)
        return
    
    q_data = questions[q_index]
    original_options = {"A": q_data[2], "B": q_data[3], "C": q_data[4], "D": q_data[5]}
    correct_text = original_options[q_data[6]]
    
    option_texts = list(original_options.values())
    random.shuffle(option_texts)
    
    await state.update_data(
        current_correct_text=correct_text, 
        current_question_text=q_data[1],
        current_options=option_texts
    )
    
    builder = InlineKeyboardBuilder()
    labels = ["A", "B", "C", "D"]
    for i, opt_text in enumerate(option_texts):
        builder.button(text=f"{labels[i]}) {opt_text}", callback_data=f"ans_{i}")
    builder.adjust(1)
    
    label = "Savol" if lang == 'uz' else "Вопрос"
    question_text = f"{label} {q_index + 1}/{len(questions)}:\n\n{q_data[1]}"
    
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(question_text, reply_markup=builder.as_markup())
    else:
        await message.answer(question_text, reply_markup=builder.as_markup())

@router.callback_query(QuizState.answering, F.data.startswith("ans_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    q_index = data['current_index']
    score = data['score']
    correct_text = data['current_correct_text']
    user_answers = data['user_answers']
    q_text = data['current_question_text']
    
    options = data.get('current_options', [])
    try:
        ans_index = int(callback.data[4:])
        user_answer_text = options[ans_index]
    except (ValueError, IndexError):
        user_answer_text = "Unknown"
        
    is_right = (user_answer_text == correct_text)
    
    if is_right:
        score += POINTS_PER_ANSWER
    
    user_answers.append({
        "q": q_text,
        "user": user_answer_text,
        "correct": correct_text,
        "is_right": is_right
    })
    
    await state.update_data(current_index=q_index + 1, score=score, user_answers=user_answers)
    await send_question(callback, state)
    await callback.answer()

async def finish_quiz(message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'uz')
    score = data['score']
    user_answers = data['user_answers']
    full_name = data['full_name']
    group_name = data['group_name']
    total_questions = len(data['questions'])
    max_score = total_questions * POINTS_PER_ANSWER
    
    if lang == 'uz':
        summary = (
            f"🏁 Quiz tugadi!\n\n"
            f"👤 Talaba: {full_name}\n"
            f"👥 Guruh: {group_name}\n"
            f"🌟 Natijangiz: {score} ball ({max_score} dan)\n"
            f"✅ To'g'ri: {score // POINTS_PER_ANSWER}\n"
            f"❌ Xato: {total_questions - (score // POINTS_PER_ANSWER)}\n\n"
            f"📋 Batafsil hisobot:\n"
        )
    else:
        summary = (
            f"🏁 Тест завершен!\n\n"
            f"👤 Студент: {full_name}\n"
            f"👥 Группа: {group_name}\n"
            f"🌟 Ваш результат: {score} баллов (из {max_score})\n"
            f"✅ Правильно: {score // POINTS_PER_ANSWER}\n"
            f"❌ Ошибка: {total_questions - (score // POINTS_PER_ANSWER)}\n\n"
            f"📋 Подробный отчет:\n"
        )
    
    report_parts = [summary]
    current_part = 0
    
    for i, ans in enumerate(user_answers):
        icon = "✅" if ans['is_right'] else "❌"
        if lang == 'uz':
            line = f"{i+1}. {icon} Savol: {ans['q'][:30]}...\n   Siz: {ans['user']}\n"
            if not ans['is_right']:
                line += f"   To'g'ri: {ans['correct']}\n"
        else:
            line = f"{i+1}. {icon} Вопрос: {ans['q'][:30]}...\n   Вы: {ans['user']}\n"
            if not ans['is_right']:
                line += f"   Правильно: {ans['correct']}\n"
        
        # Telegram xabari limiti ~4096 belgi. Biz 3800 dan oshsa yangi qismga o'tamiz.
        if len(report_parts[current_part]) + len(line) > 3800:
            report_parts.append(line)
            current_part += 1
        else:
            report_parts[current_part] += line

    # Save result to database
    save_result(message.from_user.id, full_name, group_name, score, total_questions)
    
    # Barcha qismlarni yuborish
    for i, part_text in enumerate(report_parts):
        if i == 0:
            if isinstance(message, types.CallbackQuery):
                await message.message.edit_text(part_text)
            else:
                await message.answer(part_text)
        else:
            # Keyingi qismlarni yangi xabar sifatida yuboramiz
            if isinstance(message, types.CallbackQuery):
                await message.message.answer(part_text)
            else:
                await message.answer(part_text)
        
    await state.clear()
