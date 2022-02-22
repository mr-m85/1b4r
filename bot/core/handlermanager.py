# -*- coding: utf-8 -*-
# (c) YashDK [yash-dk@github]

from datetime import datetime
from telethon import TelegramClient, events
from telethon import __version__ as telever
from pyrogram import __version__ as pyrover
from telethon.tl.types import KeyboardButtonCallback
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.get_file_id import get_message_type
from bot.utils.get_size_p import get_size
from .. import SessionVars, uptime
from pyrogram.types import ForceReply
from telethon.errors.rpcerrorlist import MessageNotModifiedError
from bot.utils.list_selected_drive import get_list_drive_results, list_drive
from .get_commands import get_command, get_command_p
from .get_vars import get_val
from ..utils.speedtest import get_speed
from ..utils import human_format
from ..utils.misc_utils import clear_stuff
from ..utils.admin_check import is_admin
from .. import SessionVars, uptime
from pyrogram import filters
from pyrogram.handlers import MessageHandler
from .settings import handle_settings, handle_setting_callback
from bot.downloaders.telegram_download import LOGGER, down_load_media_pyro
import asyncio as aio
import re, logging, time, os, psutil, shutil, signal
from bot import __version__

torlog = logging.getLogger(__name__)


def add_handlers(bot: TelegramClient):


    #pyro handler
    download_handler = MessageHandler(
        handle_download_command,
        filters=filters.command([get_command_p("LEECH")])
        #filters=filters.media
    )
    bot.pyro.add_handler(download_handler)


    test_handler = MessageHandler(
        handle_test_command,
        filters=filters.command([get_command_p("TEST")])
    )
    bot.pyro.add_handler(test_handler)

   # telethon handlers

    bot.add_event_handler(
        handle_copy_command,
        events.NewMessage(pattern=command_process(get_command("COPY")))
    )
    

    bot.add_event_handler(
        handle_exec_message_f,
        events.NewMessage(pattern=command_process(get_command("EXEC")))
    )

    bot.add_event_handler(
        about_me,
        events.NewMessage(pattern=command_process(get_command("ABOUT")))
    )

    bot.add_event_handler(
        get_logs_f,
        events.NewMessage(pattern=command_process(get_command("GETLOGS")))
    )


    bot.add_event_handler(
        handle_server_command,
        events.NewMessage(pattern=command_process(get_command("SERVER")))
    )

    bot.add_event_handler(
        start_handler,
        events.NewMessage(pattern=command_process(get_command("START")))
    )

    bot.add_event_handler(
        speed_handler,
        events.NewMessage(pattern=command_process(get_command("SPEEDTEST")))
    )

    bot.add_event_handler(
        cleardata_handler,
        events.NewMessage(pattern=command_process(get_command("CRLDATA")))
    )

    bot.add_event_handler(
        handle_settings_command,
        events.NewMessage(pattern=command_process(get_command("SETTINGS")))
    )

    bot.loop.run_until_complete(booted(bot))

   
    # *********** Callback Handlers ***********  

    #@bot.pyro.on_callback_query(filters="renaming")
    async def handle_download_cb(client, query):
        data= query.data
        list = data.split(" ")
        message= query.message
        #messageid= query.message.message_id
        message_type= get_val("MESSAGE_TYPE")

        if "default" in list[1]:
            await down_load_media_pyro(client, message, message_type)

        if "rename" in list[1]: 
            question= await message.reply(
                 text= "Envíe el nuevo nombre para el archivo /ignorar para cancelar", 
                 #reply_to_message_id= messageid, 
                 #reply_markup= ForceReply()
             )
            reply_message = await client.listen.Message(filters.text, id='1', timeout= 30)
            if "/ignorar" in reply_message.text:
                await question.delete()
                await message.delete()
                await client.listen.Cancel("1")
            else:
                await question.delete()
                await down_load_media_pyro(client, message, message_type, reply_message.text, True)

    #telethon

    bot.add_event_handler(
        next_page,
        events.CallbackQuery(pattern="next")
        )

    bot.add_event_handler(
        handle_cancel,
        events.CallbackQuery(pattern="upcancel")
    )

    bot.add_event_handler(
        handle_server_command,
        events.CallbackQuery(pattern="fullserver")
    )
    bot.add_event_handler(
        cleardata_handler,
        events.CallbackQuery(pattern="cleardata")
    )

    bot.add_event_handler(
        handle_settings_cb,
        events.CallbackQuery(pattern="setting")
    )


# *********** Handlers Below ***********

async def handle_download_command(client, message):
    header_m = "Que nombre quieres usar?\n\n"
   
    #LOGGER.info(message)
    replied_message= message.reply_to_message

    default= "📄"
    rename= "📝"

    if replied_message is not None :
            if replied_message.text is None:

                message_type = get_message_type(replied_message)

                name= message_type.file_name
                size= get_size(message_type.file_size)
                #file_id= message_type.file_id

                msg= f"Nombre: `{name}`\n\nTamano: `{size}`"
                
                SessionVars.update_var("MESSAGE_TYPE", message_type)
                    
                keyboard = [[InlineKeyboardButton(f"{default} Por Defecto", callback_data= f'renaming default'),
                            InlineKeyboardButton(f"{rename} Renombrar", callback_data='renaming rename')],
                            [InlineKeyboardButton("Cerrar", callback_data= f"settings selfdest".encode("UTF-8"))]
                            ]

                reply_markup = InlineKeyboardMarkup(inline_keyboard= keyboard)

                await message.reply_text(header_m + msg, reply_markup= reply_markup)
            else:
               await message.reply("Responda a un archivo de Telegram para subir a la nube")          
    else:
        await message.reply("Responda a un archivo de Telegram para subir a la nube") 

async def handle_copy_command(e):
    if await is_admin(e.sender_id):
            await handle_settings(e, msg= "Seleccione unidad origen", submenu= "rclone_menu_copy", data_cb= "list_drive_origin_cb", is_main_m=False)
    else:
       await e.delete()

async def next_page(callback_query):
    _, offset = callback_query.data.decode().split(" ")
    logging.info(f"NEXT_OFFSET: {offset}")
    data = SessionVars.get_var("JSON_RESULT_DATA")
    btn= []
    offset = int(offset)
    
    result, next_offset, total = await get_list_drive_results(data, offset=offset)

    btn.append([KeyboardButtonCallback(f" ✅ Seleccione esta Carpeta", f"settings selfdest")])

    list_drive(result, menu=btn, data_cb= "list_dir_main_menu")
        
    n_offset = int(next_offset)
    off_set = offset - 10 

    logging.info(f"OFF_SET: {off_set}")
    logging.info(f"OFFSET: {offset}")
    logging.info(f"total: {total}")

    if offset == 0:
        btn.append(
            [KeyboardButtonCallback(f"🗓 {round(int(offset) / 10) + 1} / {round(total / 10)}", data="setting pages"),
             KeyboardButtonCallback("NEXT ⏩", data= f"next {next_offset}".encode("UTF-8"))
            ])

    elif offset + 10 >= total:
        btn.append(
             [KeyboardButtonCallback("⏪ BACK", data=f"next {off_set}"),
              KeyboardButtonCallback(f"🗓 {round(int(offset) / 10) + 1} / {round(total / 10)}",
                                   data="setting pages")])
    else:
        btn.append([KeyboardButtonCallback("⏪ BACK", data=f"next {off_set}"),
             KeyboardButtonCallback(f"🗓 {round(int(offset) / 10) + 1} / {round(total / 10)}", data="setting pages"),
             KeyboardButtonCallback("NEXT ⏩", data=f"next {n_offset}")
            ])
    try:
        mmes= await callback_query.get_message()
        await mmes.edit("dfdf", buttons=btn)
    except MessageNotModifiedError as e:
        logging.info(e)
        pass

async def speed_handler(e):
    if await is_admin(e.sender_id):
        await get_speed(e)
    else:
        await e.delete()    

async def handle_test_command(client, message):
    pass

async def handle_cancel_all(e):
    try:
        # iterating through each instance of the process
        for line in os.popen("ps ax | grep " + "rclone" + " | grep -v grep"):
            fields = line.split()

            # extracting Process ID from the output
            pid = fields[0]

            # terminating process
            os.kill(int(pid), signal.SIGKILL)

            await e.answer("Upload has been canceled ", alert=True)
    except:
        print("Error Encountered while running script")


async def handle_cancel(callback_query):
        data = callback_query.data
        #message= callback_query.message
        torlog.info("Data is {}".format(data))
        SessionVars.update_var("UP_CANCEL", True)
        # data = data.split(" ")

async def handle_settings_command(e):
    if await is_admin(e.sender_id):
        await handle_settings(e)
    else:
        await e.delete()    


async def handle_settings_cb(e):
    if await is_admin(e.sender_id):
        await handle_setting_callback(e)
    else:
        await e.answer("⚠️ WARN ⚠️ Dont Touch Admin Settings.", alert=True)


async def handle_exec_message_f(e):
    if get_val("REST11"):
        return
    message = e
    client = e.client
    if await is_admin(message.sender_id):
        PROCESS_RUN_TIME = 100
        cmd = message.text.split(" ", maxsplit=1)[1]

        reply_to_id = message.id
        if message.is_reply:
            reply_to_id = message.reply_to_msg_id

        process = await aio.create_subprocess_shell(
            cmd,
            stdout=aio.subprocess.PIPE,
            stderr=aio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        e = stderr.decode()
        if not e:
            e = "No Error"
        o = stdout.decode()
        if not o:
            o = "No Output"
        else:
            _o = o.split("\n")
            o = "`\n".join(_o)
        OUTPUT = f"**QUERY:**\n__Command:__\n`{cmd}` \n__PID:__\n`{process.pid}`\n\n**stderr:** \n`{e}`\n**Output:**\n{o}"

        if len(OUTPUT) > 3900:
            with open("exec.text", "w+", encoding="utf8") as out_file:
                out_file.write(str(OUTPUT))
            await client.send_file(
                entity=message.chat_id,
                file="exec.text",
                caption=cmd,
                reply_to=reply_to_id
            )
            os.remove("exec.text")
            await message.delete()
        else:
            await message.reply(OUTPUT)
    else:
        await message.reply("Only for owner")


async def get_logs_f(e):
    if await is_admin(e.sender_id):
        await e.client.send_file(
            entity=e.chat_id,
            file="botlog.txt",
            caption="botlog.txt",
            reply_to=e.message.id
        )
    else:
        await e.delete()


async def start_handler(e):
    if await is_admin(e.sender_id):
        msg = ''' **Hola, ¡Bienvenido a Rclone bot!**\n
Puedo ayudarte a transferir archivos de una nube a otra nube. También puedo subir archivos de telegram a su almacenamiento en la nube.\n
**Se admiten más de 40 tipos de almacenamiento en la nube.**\n
'''
        #e.client.parse_mode = 'html'
        await e.reply(msg)
    else:
        await e.delete()


def progress_bar(percentage):
    """Returns a progress bar for download
    """
    # percentage is on the scale of 0-1
    comp = get_val("COMPLETED_STR")
    ncomp = get_val("REMAINING_STR")
    pr = ""

    if isinstance(percentage, str):
        return "NaN"

    try:
        percentage = int(percentage)
    except:
        percentage = 0

    for i in range(1, 11):
        if i <= int(percentage / 10):
            pr += comp
        else:
            pr += ncomp
    return pr


async def handle_server_command(message):
    print(type(message))
    if isinstance(message, events.CallbackQuery.Event):
        callbk = True
    else:
        callbk = False

    try:
        # Memory
        mem = psutil.virtual_memory()
        memavailable = human_format.human_readable_bytes(mem.available)
        memtotal = human_format.human_readable_bytes(mem.total)
        mempercent = mem.percent
        memfree = human_format.human_readable_bytes(mem.free)
    except:
        memavailable = "N/A"
        memtotal = "N/A"
        mempercent = "N/A"
        memfree = "N/A"

    try:
        # Frequencies
        cpufreq = psutil.cpu_freq()
        freqcurrent = cpufreq.current
        freqmax = cpufreq.max
    except:
        freqcurrent = "N/A"
        freqmax = "N/A"

    try:
        # Cores
        cores = psutil.cpu_count(logical=False)
        lcores = psutil.cpu_count()
    except:
        cores = "N/A"
        lcores = "N/A"

    try:
        cpupercent = psutil.cpu_percent()
    except:
        cpupercent = "N/A"

    try:
        # Storage
        usage = shutil.disk_usage("/")
        totaldsk = human_format.human_readable_bytes(usage.total)
        useddsk = human_format.human_readable_bytes(usage.used)
        freedsk = human_format.human_readable_bytes(usage.free)
    except:
        totaldsk = "N/A"
        useddsk = "N/A"
        freedsk = "N/A"

    try:
        upb, dlb = 0, 0
        dlb = human_format.human_readable_bytes(dlb)
        upb = human_format.human_readable_bytes(upb)
    except:
        dlb = "N/A"
        upb = "N/A"

    diff = time.time() - uptime
    diff = human_format.human_readable_timedelta(diff)

    if callbk:
        msg = (
            f"<b>BOT UPTIME:-</b> {diff}\n\n"
            "<b>CPU STATS:-</b>\n"
            f"Cores: {cores} Logical: {lcores}\n"
            f"CPU Frequency: {freqcurrent}  Mhz Max: {freqmax}\n"
            f"CPU Utilization: {cpupercent}%\n"
            "\n"
            "<b>STORAGE STATS:-</b>\n"
            f"Total: {totaldsk}\n"
            f"Used: {useddsk}\n"
            f"Free: {freedsk}\n"
            "\n"
            "<b>MEMORY STATS:-</b>\n"
            f"Available: {memavailable}\n"
            f"Total: {memtotal}\n"
            f"Usage: {mempercent}%\n"
            f"Free: {memfree}\n"
            "\n"
            "<b>TRANSFER INFO:</b>\n"
            f"Download: {dlb}\n"
            f"Upload: {upb}\n"
        )
        await message.edit(msg, parse_mode="html", buttons=None)
    else:
        try:
            storage_percent = round((usage.used / usage.total) * 100, 2)
        except:
            storage_percent = 0

        msg = (
            f"<b>BOT UPTIME:-</b> {diff}\n\n"
            f"CPU Utilization: {progress_bar(cpupercent)} - {cpupercent}%\n\n"
            f"Storage used:- {progress_bar(storage_percent)} - {storage_percent}%\n"
            f"Total: {totaldsk} Free: {freedsk}\n\n"
            f"Memory used:- {progress_bar(mempercent)} - {mempercent}%\n"
            f"Total: {memtotal} Free: {memfree}\n\n"
            f"Transfer Download:- {dlb}\n"
            f"Transfer Upload:- {upb}\n"
        )
        await message.reply(msg, parse_mode="html",
                            buttons=[[KeyboardButtonCallback("Get detailed stats.", "fullserver")]])


async def about_me(message):
    diff = time.time() - uptime
    diff = human_format.human_readable_timedelta(diff)

    msg = (
        f"<b>Telethon Version</b>: {telever}\n"
        f"<b>Pyrogram Version</b>: {pyrover}\n"
        f"<b>Bot Uptime:-</b> {diff}\n"
        "<b>Upload Engine:-</b> <code>RCLONE</code> \n"
        "\n"
    )

    await message.reply(msg, parse_mode="html")


async def cleardata_handler(e):
    if await is_admin(e.sender_id):
        if isinstance(e, events.CallbackQuery.Event):
            data = e.data.decode("UTF-8").split(" ")
            if data[1] == "yes":
                await e.answer("Clearing data.")
                await e.edit("Datos Limpiados {}".format(datetime.now().strftime("%d-%B-%Y, %H:%M:%S")))
                await clear_stuff("./Downloads")
            else:
                await e.answer("Aborting.")
                await e.delete()
        else:
            buttons = [[KeyboardButtonCallback("Yes", data= "cleardata yes"),
                        KeyboardButtonCallback("No", data= "cleardata no")]]
            await e.reply("¿Estás seguro de que quieres borrar los datos?\n"
                          "Esto eliminará todos sus datos, incluidos los archivos descargados, y afectará las transferencias en curso..\n",
                          buttons= buttons)
    else:
        await e.answer("⚠️ WARN ⚠️ Dont Touch Admin Settings.", alert=True)


async def booted(client):
    id = get_val("OWNER_ID")
    try:
        await client.send_message(id, "El bot se ha iniciado y está listo para usar")
    except Exception as e:
        torlog.info(f"Not found the entity {id}")


def command_process(command):
    return re.compile(command, re.IGNORECASE)
