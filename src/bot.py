import logging
import os
from enum import Enum, auto

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .db import Database
from .wallet_provider import SUPPORTED_CHAINS, get_wallet_provider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SellState(Enum):
    PAYOUT_CURRENCY = auto()
    PAYOUT_ADDRESS = auto()
    ACCOUNT_EMAIL = auto()
    ACCOUNT_PASSWORD = auto()
    CONTACT_PHONE = auto()


def get_admin_chat_id() -> int | None:
    admin_id = os.getenv("ADMIN_CHAT_ID")
    return int(admin_id) if admin_id else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    db = context.bot_data["db"]
    db.ensure_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(
        "Merhaba! Bu bot ile kripto yatırabilir, hesap alıp satabilirsiniz.\n"
        "Komutlar: /deposit, /balance, /buy, /sell"
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    db = context.bot_data["db"]
    account = db.ensure_user(user.id, user.username, user.first_name, user.last_name)
    amount = db.get_balance(account.id, "USDT")
    await update.message.reply_text(f"Bakiyeniz: {amount:.2f} USDT")


def deposit_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(chain, callback_data=f"deposit:{chain}")]
        for chain in SUPPORTED_CHAINS
    ]
    return InlineKeyboardMarkup(buttons)


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Lütfen yatırma ağı seçin:",
        reply_markup=deposit_keyboard(),
    )


async def deposit_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    chain = query.data.split(":", 1)[1]
    user = query.from_user
    db = context.bot_data["db"]
    account = db.ensure_user(user.id, user.username, user.first_name, user.last_name)

    existing = db.get_deposit_address(account.id, chain)
    if existing:
        address = existing
    else:
        provider = context.bot_data["wallet_provider"]
        address = provider.generate_address(account.id, chain)
        db.set_deposit_address(account.id, chain, address)

    await query.edit_message_text(
        f"{chain} için yatırma adresiniz:\n`{address}`\n"
        "Transferden sonra onaylar otomatik olarak kontrol edilir.",
        parse_mode="Markdown",
    )


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hesap almak için önce /deposit ile bakiye yükleyin.\n"
        "Aktif hesap listesi hazır olduğunda buradan paylaşılacaktır."
    )


async def sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Hangi para biriminde ödeme almak istiyorsunuz? (USDT, BTC, ETH)")
    return SellState.PAYOUT_CURRENCY


async def sell_payout_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["payout_currency"] = update.message.text.strip()
    await update.message.reply_text("Ödeme adresinizi yazın:")
    return SellState.PAYOUT_ADDRESS


async def sell_payout_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["payout_address"] = update.message.text.strip()
    await update.message.reply_text("Satılacak hesabın e-posta adresi:")
    return SellState.ACCOUNT_EMAIL


async def sell_account_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["account_email"] = update.message.text.strip()
    await update.message.reply_text("Hesap şifresi:")
    return SellState.ACCOUNT_PASSWORD


async def sell_account_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["account_password"] = update.message.text.strip()
    await update.message.reply_text("İletişim numarası:")
    return SellState.CONTACT_PHONE


async def sell_contact_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    contact_phone = update.message.text.strip()
    db = context.bot_data["db"]
    account = db.ensure_user(user.id, user.username, user.first_name, user.last_name)

    payout_currency = context.user_data.get("payout_currency", "")
    payout_address = context.user_data.get("payout_address", "")
    account_email = context.user_data.get("account_email", "")
    account_password = context.user_data.get("account_password", "")

    request_id = db.create_sell_request(
        account.id,
        payout_currency,
        payout_address,
        account_email,
        account_password,
        contact_phone,
    )

    admin_chat_id = get_admin_chat_id()
    if admin_chat_id:
        message = (
            "Yeni hesap satış talebi:\n"
            f"ID: {request_id}\n"
            f"Kullanıcı: @{user.username or user.id}\n"
            f"Ödeme birimi: {payout_currency}\n"
            f"Ödeme adresi: {payout_address}\n"
            f"Hesap e-posta: {account_email}\n"
            f"Hesap şifre: {account_password}\n"
            f"İletişim: {contact_phone}"
        )
        await context.bot.send_message(chat_id=admin_chat_id, text=message)

    await update.message.reply_text(
        "Satış talebiniz alındı. Ekibimiz sizinle iletişime geçecek."
    )
    context.user_data.clear()
    return ConversationHandler.END


async def sell_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Satış işlemi iptal edildi.")
    return ConversationHandler.END


async def poll_deposits(context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.bot_data["db"]
    provider = context.bot_data["wallet_provider"]
    addresses = db.list_deposit_addresses()
    deposits = provider.fetch_new_deposits(addresses)
    for deposit in deposits:
        recorded = db.record_deposit(
            deposit.user_id,
            deposit.chain,
            deposit.address,
            deposit.tx_id,
            deposit.amount,
            deposit.currency,
        )
        if recorded:
            db.add_balance(deposit.user_id, deposit.currency, deposit.amount)


def build_application() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    db_path = os.getenv("BOT_DB_PATH", "data/bot.db")
    application = Application.builder().token(token).build()
    application.bot_data["db"] = Database(db_path)
    application.bot_data["wallet_provider"] = get_wallet_provider()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deposit", deposit))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("buy", buy))

    sell_handler = ConversationHandler(
        entry_points=[CommandHandler("sell", sell_start)],
        states={
            SellState.PAYOUT_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_payout_currency)],
            SellState.PAYOUT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_payout_address)],
            SellState.ACCOUNT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_account_email)],
            SellState.ACCOUNT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_account_password)],
            SellState.CONTACT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_contact_phone)],
        },
        fallbacks=[CommandHandler("cancel", sell_cancel)],
    )
    application.add_handler(sell_handler)
    application.add_handler(CallbackQueryHandler(deposit_selected, pattern=r"^deposit:"))

    application.job_queue.run_repeating(poll_deposits, interval=60, first=10)
    return application


def main() -> None:
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    main()
