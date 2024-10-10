import importlib
import re
import time
from sys import argv, version_info
from Abg.helpers.human_read import get_readable_time
from pyrogram import __version__ as pver
from telegram import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram import __version__ as lver
from telegram.error import (
    BadRequest,
    ChatMigrated,
    NetworkError,
    TelegramError,
    TimedOut,
    Unauthorized,
)
from telegram.ext import CallbackContext,  CallbackQueryHandler, Filters
from telegram.ext.dispatcher import DispatcherHandlerStop
from telegram.utils.helpers import escape_markdown
from telethon import __version__ as tver

import Ava.modules.no_sql.users_db as sql
from Ava import BOT_USERNAME
from Ava import LOGGER as log
from Ava import OWNER_ID, OWNER_USERNAME, SUPPORT_CHAT, TOKEN
from Ava import Jarvis as pbot
from Ava import StartTime, dispatcher, telethn, updater

# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from Ava.modules import ALL_MODULES
from Ava.modules.helper_funcs.chat_status import is_user_admin
from Ava.modules.helper_funcs.decorators import Avacallback, Avacmd, Avamsg
from Ava.modules.helper_funcs.misc import paginate_modules
from Ava.modules.language import gs


PM_START_TEX = """
merhaba `{}`, nasılsın \nbekle biraz. . . 
"""

START_IMG = "https://graph.org/file/6ba0dd5938fe68613b3ac.jpg"
HELP_IMG = "https://graph.org/file/869297aef3b5dd030ea33.jpg"

buttons = [
    [
        InlineKeyboardButton(text="❣ BENİ EKLE ❣︎", url=f"t.me/{BOT_USERNAME}?startgroup=new"),
    ],
    [
        InlineKeyboardButton(text="ʜᴇʟᴩ & ᴄᴏᴍᴍᴀɴᴅs", callback_data="help_back"),
        InlineKeyboardButton(text="🥀 STAT 🥀", callback_data="stats_callback"),
    ],
    [
        InlineKeyboardButton(text="❄ HAKKINDA ❄", callback_data="Jarvis_"),
        InlineKeyboardButton(text="🥀 SAHİBİ 🥀", url=f"tg://user?id={OWNER_ID}"),
    ],
]


IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []


CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module(f"Ava.modules.{module_name}")
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if imported_module.__mod_name__.lower() not in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("ᴄᴀɴ'ᴛ ʜᴀᴠᴇ ᴛᴡᴏ ᴍᴏᴅᴜʟᴇs ᴡɪᴛʜ ᴛʜᴇ sᴀᴍᴇ ɴᴀᴍᴇ! ᴘʟᴇᴀsᴇ ᴄʜᴀɴɢᴇ ᴏɴᴇ")

    if hasattr(imported_module, "get_help") and imported_module.get_help:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        kb = paginate_modules(0, HELPABLE, "help")
        keyboard = InlineKeyboardMarkup(kb)
    dispatcher.bot.send_photo(
        chat_id=chat_id,
        photo=HELP_IMG,
        caption=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )

@Avacmd(command="text")
def test(update: Update, context: CallbackContext):
    update.effective_message.reply_text("ᴛʜɪs ᴘᴇʀsᴏɴ ᴇᴅɪᴛᴇᴅ ᴀ ᴍᴇssᴀɢᴇ")
    print(update.effective_message)


@Avacallback(pattern=r"start_back")
@Avacmd(command="start", pass_args=True)
def start(update: Update, context: CallbackContext):    # sourcery no-metrics
    chat = update.effective_chat
    update.effective_user
    uptime = get_readable_time((time.time() - StartTime))
    args = context.args
    usr = update.effective_user

    if hasattr(update, "callback_query"):
        query = update.callback_query
        if hasattr(query, "id"):
            first_name = update.effective_user.first_name
            query.message.edit_media(
                media=InputMediaPhoto(
                    START_IMG,
                    caption=gs(chat.id, "pm_start_text").format(
                        escape_markdown(first_name),
                        escape_markdown(context.bot.first_name),
                        escape_markdown(uptime),
                        sql.num_chat_users(),
                        sql.num_chats(),
                        OWNER_ID,
                    ),
                    parse_mode=ParseMode.MARKDOWN
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )

            context.bot.answer_callback_query(query.id)
            return

    update.effective_user
    uptime = get_readable_time((time.time() - StartTime))
    if update.effective_chat.type == "private":
        if args and len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, (gs(chat.id, "pm_help_text")))
            elif args[0].lower().startswith("ghelp_"):
                query = update.callback_query
                mod = args[0].lower().split("_", 1)[1]
                if not HELPABLE.get(mod, False):
                    return
                help_list = HELPABLE[mod].get_help(chat.id)
                help_text = []
                help_buttons = []
                if isinstance(help_list, list):
                    help_text = help_list[0]
                    help_buttons = help_list[1:]
                elif isinstance(help_list, str):
                    help_text = help_list
                text = f"ʜᴇʀᴇ ɪs ᴛʜᴇ ʜᴇʟᴘ ғᴏʀ ᴛʜᴇ *{HELPABLE[mod].__mod_name__}* ᴍᴏᴅᴜʟᴇ:\n{help_text}"
                help_buttons.append(
                    [
                        InlineKeyboardButton(text="geri", callback_data="help_back"),
                        InlineKeyboardButton(
                            text="sᴜᴘᴘᴏʀᴛ",
                            callback_data="Jarvis_support",
                        ),
                    ]
                )
                send_help(
                    chat.id,
                    text,
                    InlineKeyboardMarkup(help_buttons),
                )

                if hasattr(query, "id"):
                    context.bot.answer_callback_query(query.id)
            elif args[0].lower() == "markdownhelp":
                IMPORTED["𝐄xtras"].markdown_help_sender(update)
            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match[1])

                if is_user_admin(update, update.effective_user.id):
                    send_settings(match[1], update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "𝐑ᴜʟᴇs" in IMPORTED:
                IMPORTED["𝐑ᴜʟᴇs"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            usr = update.effective_user
            lol = update.effective_message.reply_text(
                PM_START_TEX.format(usr.first_name), parse_mode=ParseMode.MARKDOWN
            )
            time.sleep(1.25)
            lol.edit_text("💻")
            time.sleep(1.0)
            lol.edit_text("ꜱᴛᴀʀ.. ")
            time.sleep(0.5)
            lol.delete()
            update.effective_message.reply_photo(
                START_IMG,
                caption=gs(chat.id, "pm_start_text").format(
                    escape_markdown(first_name),
                    escape_markdown(context.bot.first_name),
                    escape_markdown(uptime),
                    sql.num_chat_users(),
                    sql.num_chats(),
                    OWNER_ID,
                ),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN
            )

    else:
        update.effective_message.reply_text(gs(chat.id, "grp_start_text"))

    if hasattr(update, "callback_query"):
        query = update.callback_query
        if hasattr(query, "id"):
            context.bot.answer_callback_query(query.id)


# for test purposes
def error_callback(_, context: CallbackContext):

    try:
        raise context.error
    except (Unauthorized, BadRequest):
        pass
        # remove update.message.chat_id from conversation list
    except TimedOut:
        pass
        # handle slow connection problems
    except NetworkError:
        pass
        # handle other connection problems
    except ChatMigrated:
        pass
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        pass
        # handle all other telegram related errors


@Avacallback(pattern=r"help_")
def help_button(update: Update, context: CallbackContext):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    chat = update.effective_chat

    try:
        if mod_match:
            module = mod_match[1]
            module = module.replace("_", " ")
            help_list = HELPABLE[module].get_help(update.effective_chat.id)
            if isinstance(help_list, list):
                help_text = help_list[0]
                help_buttons = help_list[1:]
            elif isinstance(help_list, str):
                help_text = help_list
                help_buttons = []
            text = f"ʜᴇʀᴇ ɪs ᴛʜᴇ ʜᴇʟᴘ ғᴏʀ ᴛʜᴇ *{HELPABLE[module].__mod_name__}* ᴍᴏᴅᴜʟᴇ:\n{help_text}"
            help_buttons.append(
                [
                    InlineKeyboardButton(text="geri", callback_data="help_back"),
                    InlineKeyboardButton(text="destek", callback_data="Jarvis_support"),
                ]
            )
            query.message.edit_caption(
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(help_buttons),
            )

        elif prev_match:
            curr_page = int(prev_match[1])
            kb = paginate_modules(curr_page - 1, HELPABLE, "help")
            query.message.edit_caption(
                caption=gs(chat.id, "pm_help_text"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb),
            )

        elif next_match:
            next_page = int(next_match[1])
            kb = paginate_modules(next_page + 1, HELPABLE, "help")
            query.message.edit_caption(
                caption=gs(chat.id, "pm_help_text"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb),
            )

        elif back_match:
            kb = paginate_modules(0, HELPABLE, "help")
            query.message.edit_caption(
                caption=gs(chat.id, "pm_help_text"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb),
            )

        # ensure no spinny white circle
        context.bot.answer_callback_query(query.id)

    except BadRequest:
        pass


@Avacmd(command="help")
def get_help(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:
        if len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
            module = args[1].lower()
            update.effective_message.reply_photo(
                HELP_IMG,
                caption=f"ᴄᴏɴᴛᴀᴄᴛ ᴍᴇ ɪɴ ᴘᴍ ᴛᴏ ɢᴇᴛ ʜᴇʟᴘ ᴏғ {module.capitalize()}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="• ʜᴇʟᴘ •​",
                                url=f"t.me/{context.bot.username}?start=ghelp_{module}",
                            )
                        ]
                    ]
                ),
            )
            return
        update.effective_message.reply_photo(
            HELP_IMG,
            caption="» ᴄʜᴏᴏsᴇ ᴀɴ ᴏᴩᴛɪᴏɴ ғᴏʀ ɢᴇᴛᴛɪɴɢ ʜᴇʟᴩ.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="• ᴏᴩᴇɴ ɪɴ ᴩʀɪᴠᴀᴛᴇ •",
                            url=f"https://t.me/{context.bot.username}?start=help",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="• link tıkla•",
                            callback_data="help_back",
                        )
                    ],
                ]
            ),
        )
        return

    if len(args) >= 2:
        if any(args[1].lower() == x for x in HELPABLE):
            module = args[1].lower()
            help_list = HELPABLE[module].get_help(chat.id)
            help_text = []
            help_buttons = []
            if isinstance(help_list, list):
                help_text = help_list[0]
                help_buttons = help_list[1:]
            elif isinstance(help_list, str):
                help_text = help_list
            text = f"ʜᴇʀᴇ ɪs ᴛʜᴇ ᴀᴠᴀɪʟᴀʙʟᴇ ʜᴇʟᴘ ғᴏʀ ᴛʜᴇ *{HELPABLE[module].__mod_name__}* ᴍᴏᴅᴜʟᴇ:\n{help_text}"
            help_buttons.append(
                [
                    InlineKeyboardButton(text="ʙᴀᴄᴋ", callback_data="help_back"),
                    InlineKeyboardButton(text="sᴜᴘᴘᴏʀᴛ", callback_data="Jarvis_support"),
                ]
            )
            send_help(
                chat.id,
                text,
                InlineKeyboardMarkup(help_buttons),
            )
        else:
            update.effective_message.reply_text(
                f"<code>{args[1].lower()}</code> is not a module",
                parse_mode=ParseMode.HTML,
            )
    else:
        send_help(chat.id, (gs(chat.id, "pm_help_text")))



def send_settings(chat_id: int, user_id: int, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                f"*{mod.__mod_name__}*:\n{mod.__user_settings__(user_id)}"
                for mod in USER_SETTINGS.values()
            )
            dispatcher.bot.send_message(
                user_id,
                "ᴛʜᴇsᴇ ᴀʀᴇ ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ sᴇᴛᴛɪɴɢs:" + "\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            dispatcher.bot.send_message(
                user_id,
                "sᴇᴇᴍs ʟɪᴋᴇ ᴛʜᴇʀᴇ ᴀʀᴇɴ'ᴛ ᴀɴʏ ᴜsᴇʀ sᴘᴇᴄɪғɪᴄ sᴇᴛᴛɪɴɢs ᴀᴠᴀɪʟᴀʙʟᴇ :'(",
                parse_mode=ParseMode.MARKDOWN,
            )

    elif CHAT_SETTINGS:
        chat_name = dispatcher.bot.getChat(chat_id).title
        dispatcher.bot.send_message(
            user_id,
            text=f"ᴡʜɪᴄʜ ᴍᴏᴅᴜʟᴇ ᴡᴏᴜʟᴅ ʏᴏᴜ ʟɪᴋᴇ ᴛᴏ ᴄʜᴇᴄᴋ {chat_name}'s sᴇᴛᴛɪɴɢs ғᴏʀ?",
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
            ),
        )
    else:
        dispatcher.bot.send_message(
            user_id,
            "sᴇᴇᴍs ʟɪᴋᴇ ᴛʜᴇʀᴇ ᴀʀᴇɴ'ᴛ ᴀɴʏ ᴄʜᴀᴛ sᴇᴛᴛɪɴɢs ᴀᴠᴀɪʟᴀʙʟᴇ :'(\nsᴇɴᴅ ᴛʜɪs "
            "ɪɴ ᴀ ɢʀᴏᴜᴘ ᴄʜᴀᴛ ʏᴏᴜ'ʀᴇ ᴀᴅᴍɪɴ ɪɴ ᴛᴏ ғɪɴᴅ ɪᴛs ᴄᴜʀʀᴇɴᴛ sᴇᴛᴛɪɴɢs!",
            parse_mode=ParseMode.MARKDOWN,
        )


@Avacallback(pattern=r"stngs_")
def settings_button(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    bot = context.bot
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match[1]
            module = mod_match[2]
            chat = bot.get_chat(chat_id)
            text = f"*{escape_markdown(chat.title)}* ʜᴀs ᴛʜᴇ ғᴏʟʟᴏᴡɪɴɢ sᴇᴛᴛɪɴɢs ғᴏʀ ᴛʜᴇ *{CHAT_SETTINGS[module].__mod_name__}* ᴍᴏᴅᴜʟᴇ:\n\n{CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)}"
            query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="geri",
                                callback_data=f"stngs_back({chat_id})",
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match[1]
            curr_page = int(prev_match[2])
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                f"ʜɪ ᴛʜᴇʀᴇ! ᴛʜᴇʀᴇ ᴀʀᴇ ǫᴜɪᴛᴇ ᴀ ғᴇᴡ sᴇᴛᴛɪɴɢs ғᴏʀ {chat.title} - ɢᴏ ᴀʜᴇᴀᴅ ᴀɴᴅ ᴘɪᴄᴋ ᴡʜᴀᴛ ʏᴏᴜ'ʀᴇ ɪɴᴛᴇʀᴇsᴛᴇᴅ ɪɴ.",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif next_match:
            chat_id = next_match[1]
            next_page = int(next_match[2])
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                f"ʜɪ ᴛʜᴇʀᴇ! ᴛʜᴇʀᴇ ᴀʀᴇ ǫᴜɪᴛᴇ ᴀ ғᴇᴡ sᴇᴛᴛɪɴɢs ғᴏʀ {chat.title} - ɢᴏ ᴀʜᴇᴀᴅ ᴀɴᴅ ᴘɪᴄᴋ ᴡʜᴀᴛ ʏᴏᴜ'ʀᴇ ɪɴᴛᴇʀᴇsᴛᴇᴅ ɪɴ.",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif back_match:
            chat_id = back_match[1]
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                text=f"ʜɪ ᴛʜᴇʀᴇ! ᴛʜᴇʀᴇ ᴀʀᴇ ǫᴜɪᴛᴇ ᴀ ғᴇᴡ sᴇᴛᴛɪɴɢs ғᴏʀ {escape_markdown(chat.title)} - ɢᴏ ᴀʜᴇᴀᴅ ᴀɴᴅ ᴘɪᴄᴋ ᴡʜᴀᴛ ʏᴏᴜ'ʀᴇ ɪɴᴛᴇʀᴇsᴛᴇᴅ ɪɴ.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message not in [
            "ᴍᴇssᴀɢᴇ ɪs ɴᴏᴛ ᴍᴏᴅɪғɪᴇᴅ",
            "Query_id_invalid",
            "ᴍᴇssᴀɢᴇ ᴄᴀɴ'ᴛ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ",
        ]:
            log.exception("ᴇxᴄᴇᴘᴛɪᴏɴ ɪɴ sᴇᴛᴛɪɴɢs ʙᴜᴛᴛᴏɴs. %s", str(query.data))


@Avacmd(command="settings")
def get_settings(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    # ONLY send settings in PM
    if chat.type == chat.PRIVATE:
        send_settings(chat.id, user.id, True)

    elif is_user_admin(update, user.id):
        text = "ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ɢᴇᴛ ᴛʜɪs ᴄʜᴀᴛ sᴇᴛᴛɪɴɢs, ᴀs ᴡᴇʟʟ ᴀs ʏᴏᴜʀs."
        msg.reply_photo(HELP_IMG,
            text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="sᴇᴛᴛɪɴɢs",
                            url=f"t.me/{context.bot.username}?start=stngs_{chat.id}",
                        )
                    ]
                ]
            ),
        )
    else:
        text = "ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴄʜᴇᴄᴋ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs."


@Avamsg(Filters.status_update.migrate)
def migrate_chats(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    log.info("ᴍɪɢʀᴀᴛɪɴɢ ғʀᴏᴍ %s, ᴛᴏ %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    log.info("sᴜᴄᴄᴇssғᴜʟʟʏ ᴍɪɢʀᴀᴛᴇᴅ!")
    raise DispatcherHandlerStop


def send_startup_message():
    if SUPPORT_CHAT is not None and isinstance(SUPPORT_CHAT, str):
        try:
            dispatcher.bot.send_photo(
                f"@{SUPPORT_CHAT}",
                photo="https://telegra.ph/file/a945ba381327b4e7e45d3.jpg",
                caption=f"""
{dispatcher.bot.first_name} ɪs ᴀʟɪᴠᴇ ʙᴀʙʏ ✨ .....

━━━━━━━━━━━━━
⍟ ᴍʏ [ᴏᴡɴᴇʀ](https://t.me/{OWNER_USERNAME})
⍟ **ʟɪʙʀᴀʀʏ ᴠᴇʀsɪᴏɴ :** `{lver}`
⍟ **ᴛᴇʟᴇᴛʜᴏɴ ᴠᴇʀsɪᴏɴ :** `{tver}`
⍟ **ᴘʏʀᴏɢʀᴀᴍ ᴠᴇʀsɪᴏɴ :** `{pver}`
⍟ **ᴘʏᴛʜᴏɴ ᴠᴇʀsɪᴏɴ :** `{version_info[0]}.{version_info[1]}.{version_info[2]}`
⍟ **ʙᴏᴛ ᴠᴇʀsɪᴏɴ :** `2.69`
━━━━━━━━━━━━━
""",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Unauthorized:
            log.warning("ʙᴏᴛ ɪsɴᴛ ᴀʙʟᴇ ᴛᴏ sᴇɴᴅ ᴍᴇssᴀɢᴇ ᴛᴏ sᴜᴘᴘᴏʀᴛ_ᴄʜᴀᴛ, ɢᴏ ᴀɴᴅ ᴄʜᴇᴄᴋ !")
        except BadRequest as e:
            log.warning(e.message)

def main():
    send_startup_message()

    log.info(
        f"ᴜsɪɴɢ ʟᴏɴɢ ᴘᴏʟʟɪɴɢ. ........... ᴇɴᴊᴏʏ ʏᴏᴜʀ ʙᴏᴛ sᴛᴀʀᴛᴇᴅ ᴀs →  {dispatcher.bot.first_name}"
    )
    updater.start_polling(timeout=15, read_latency=4, drop_pending_updates=True)

    if len(argv) in {1, 3, 4}:
        telethn.run_until_disconnected()
    else:
        telethn.disconnect()

    updater.idle()

if __name__ == "__main__":
    log.info(f"[ᴀᴠᴀ] →  sᴜᴄᴄᴇssғᴜʟʟʏ ʟᴏᴀᴅᴇᴅ ᴍᴏᴅᴜʟᴇs: {str(ALL_MODULES)}")
    telethn.start(bot_token=TOKEN)
    pbot.start()
    main()
