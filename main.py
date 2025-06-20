import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, ALLOWED_USERS
from handlers import upload, delete, rename, search, stats, preview

user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized access.")
        return

    keyboard = [
        [InlineKeyboardButton("🔍 Search", callback_data="search")],
        [InlineKeyboardButton("📤 Upload", callback_data="upload")],
        [InlineKeyboardButton("✏️ Rename", callback_data="rename")],
        [InlineKeyboardButton("❌ Delete", callback_data="delete")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📁 Welcome to your secure document bot:", reply_markup=reply_markup)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await upload.handle_upload(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ALLOWED_USERS:
        await query.edit_message_text("❌ Unauthorized access.")
        return

    action = query.data
    if action in ["delete", "rename"]:
        user_states[user_id] = {"action": action}
        await query.message.reply_text("🔒 Enter password to proceed:")
    elif action == "upload":
        await query.message.reply_text("📤 Send the document you want to upload.")
    elif action == "search":
        user_states[user_id] = {"action": "search"}
        await query.message.reply_text("🔎 Enter filename to search.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return

    state = user_states.get(user_id)
    if state and "action" in state and "authenticated" not in state and state["action"] in ["delete", "rename"]:
        if update.message.text == os.getenv("DOCBOT_PASSWORD"):
            user_states[user_id]["authenticated"] = True
            await update.message.reply_text("✅ Password accepted. Now send the file name.")
        else:
            user_states.pop(user_id)
            await update.message.reply_text("❌ Incorrect password.")
        return

    if state:
        action = state["action"]
        if action == "delete" and state.get("authenticated"):
            await delete.handle_delete(update, context)
        elif action == "rename" and state.get("authenticated"):
            await rename.handle_rename(update, context)
        elif action == "search":
            await search.handle_search(update, context)
        user_states.pop(user_id, None)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await preview.handle_preview(update, context)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats.handle_stats))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
