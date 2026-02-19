"""
Main bot file - Calculator Telegram Bot
Handles all commands and callback queries
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import (
    BOT_TOKEN, 
    WELCOME_MESSAGE, 
    HELP_MESSAGE,
    ERROR_MESSAGES,
    MAX_EXPRESSION_LENGTH
)
from keyboards import get_calculator_keyboard, get_home_keyboard
from calculator import get_user_session, clear_user_session
from parser import safe_evaluate, validate_expression

# Set up logging (minimal, just for errors)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)
logger = logging.getLogger(__name__)

# ========== COMMAND HANDLERS ==========

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode='Markdown',
        reply_markup=get_home_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode='Markdown'
    )

async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /calc command - open calculator"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    await update.message.reply_text(
        f"🧮 *Calculator*\n\n{session.get_display_text()}",
        parse_mode='Markdown',
        reply_markup=get_calculator_keyboard()
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - reset expression"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    session.clear_all()
    
    await update.message.reply_text(
        f"✅ Expression cleared!\n\n{session.get_display_text()}",
        parse_mode='Markdown'
    )

# ========== CALLBACK HANDLERS ==========

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    data = query.data
    
    # Handle different button types
    if data.startswith('num_'):
        # Number buttons
        number = data.split('_')[1]
        if number == 'dot':
            session.add_to_expression('.')
        else:
            session.add_to_expression(number)
    
    elif data.startswith('op_'):
        # Operator buttons
        op = data.split('_')[1]
        session.handle_operator(op)
    
    elif data.startswith('func_'):
        # Function buttons
        func = data.split('_')[1]
        session.handle_function(func)
    
    elif data.startswith('const_'):
        # Constant buttons
        const = data.split('_')[1]
        session.handle_constant(const)
    
    elif data.startswith('paren_'):
        # Parentheses
        paren = data.split('_')[1]
        session.add_to_expression('(' if paren == 'open' else ')')
    
    elif data == 'clear_entry':
        # Clear last entry (C)
        session.clear_entry()
    
    elif data == 'clear_all':
        # Clear all (AC)
        session.clear_all()
    
    elif data == 'backspace':
        # Backspace (⌫)
        session.backspace()
    
    elif data == 'calculate':
        # Calculate result (=)
        await calculate_result(update, context)
        return
    
    elif data == 'home':
        # Home button
        await query.edit_message_text(
            WELCOME_MESSAGE,
            parse_mode='Markdown',
            reply_markup=get_home_keyboard()
        )
        return
    
    elif data == 'help':
        # Help button
        await query.edit_message_text(
            HELP_MESSAGE,
            parse_mode='Markdown'
        )
        return
    
    elif data == 'open_calc':
        # Open calculator from home
        await query.edit_message_text(
            f"🧮 *Calculator*\n\n{session.get_display_text()}",
            parse_mode='Markdown',
            reply_markup=get_calculator_keyboard()
        )
        return
    
    # Update the display
    await query.edit_message_text(
        f"🧮 *Calculator*\n\n{session.get_display_text()}",
        parse_mode='Markdown',
        reply_markup=get_calculator_keyboard()
    )

async def calculate_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calculate the current expression"""
    query = update.callback_query
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Get current expression
    expression = session.expression
    
    # Validate expression
    is_valid, error_msg = validate_expression(expression)
    if not is_valid:
        await query.edit_message_text(
            f"🧮 *Calculator*\n\n{error_msg}",
            parse_mode='Markdown',
            reply_markup=get_calculator_keyboard()
        )
        return
    
    # Calculate result
    success, result = safe_evaluate(expression)
    
    if success:
        session.set_result(result)
        await query.edit_message_text(
            f"🧮 *Calculator*\n\n`{expression} = {result}`",
            parse_mode='Markdown',
            reply_markup=get_calculator_keyboard()
        )
    else:
        await query.edit_message_text(
            f"🧮 *Calculator*\n\n{result}",
            parse_mode='Markdown',
            reply_markup=get_calculator_keyboard()
        )

# ========== MESSAGE HANDLERS ==========

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (direct input)"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    text = update.message.text
    
    # Validate input length
    if len(text) > MAX_EXPRESSION_LENGTH:
        await update.message.reply_text(ERROR_MESSAGES['too_long'])
        return
    
    # Try to calculate directly
    success, result = safe_evaluate(text)
    
    if success:
        session.set_result(result)
        await update.message.reply_text(
            f"`{text} = {result}`",
            parse_mode='Markdown',
            reply_markup=get_calculator_keyboard()
        )
    else:
        # If not a valid expression, treat as input
        session.expression = text
        await update.message.reply_text(
            f"🧮 *Calculator*\n\n{session.get_display_text()}",
            parse_mode='Markdown',
            reply_markup=get_calculator_keyboard()
        )

# ========== ERROR HANDLER ==========

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.callback_query:
        await update.callback_query.message.reply_text(
            "❌ An error occurred. Please try again."
        )

# ========== MAIN ==========

def main():
    """Main function to run the bot"""
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('calc', calc_command))
    application.add_handler(CommandHandler('clear', clear_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("🤖 Calculator Bot is running...")
    print(f"Bot token: {BOT_TOKEN[:10]}...")
    print("Press Ctrl+C to stop")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
