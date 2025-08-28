import discord
from discord.ext import commands, tasks
import socket
import os
TOKEN = os.getenv("DISCORD_TOKEN")
from dotenv import load_dotenv
load_dotenv()

# 👉 Настройки
WELCOME_CHANNEL_ID = 123456789012345678  # ID канала для приветствий
SAMP_IP = "51.75.232.65"  # IP SAMP сервера
SAMP_PORT = 1233       # порт сервера

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


# ======== ФУНКЦИЯ ЗАПРОСА SAMP =========
def get_samp_info(ip, port):
    try:
        query = b"SAMP" + bytes([int(x) for x in ip.split('.')]) + port.to_bytes(2, 'little') + b'i'
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.sendto(query, (ip, port))
        data, _ = s.recvfrom(2048)
        players = int.from_bytes(data[11:13], 'little')
        max_players = int.from_bytes(data[13:15], 'little')
        return players, max_players
    except:
        return None


# ========== СОБЫТИЯ ==========
@bot.event
async def on_ready():
    print(f"✅ Бот запущен как {bot.user}")
    update_status.start()  # запускаем авто-обновление статуса


@bot.event
async def on_member_join(member):
    # ЛС
    try:
        await member.send(f"👋 Привет, {member.name}! Добро пожаловать на **{member.guild.name}** 🎉")
    except:
        pass

    # В канал
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Новый участник!",
            description=f"{member.mention} присоединился 🚀",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)


# ========== КОМАНДЫ ==========
@bot.command()
@commands.has_permissions(manage_roles=True)
async def role(ctx, member: discord.Member, role: discord.Role):
    """Выдать или снять роль"""
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(embed=discord.Embed(
            description=f"❌ Роль **{role.name}** снята с {member.mention}",
            color=discord.Color.red()
        ))
    else:
        await member.add_roles(role)
        await ctx.send(embed=discord.Embed(
            description=f"✅ Роль **{role.name}** выдана {member.mention}",
            color=discord.Color.green()
        ))


@bot.command()
@commands.has_permissions(manage_roles=True)
async def delrole(ctx, role: discord.Role):
    """Удалить роль с сервера"""
    try:
        await role.delete(reason=f"Удалено по команде {ctx.author}")
        await ctx.send(embed=discord.Embed(
            description=f"🗑 Роль **{role.name}** удалена.",
            color=discord.Color.orange()
        ))
    except Exception as e:
        await ctx.send(embed=discord.Embed(
            description=f"⚠️ Ошибка: {e}",
            color=discord.Color.red()
        ))


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Без причины"):
    """Кикнуть участника"""
    await member.kick(reason=reason)
    await ctx.send(embed=discord.Embed(
        description=f"👢 {member.mention} кикнут. Причина: {reason}",
        color=discord.Color.orange()
    ))


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Без причины"):
    """Забанить участника"""
    await member.ban(reason=reason)
    await ctx.send(embed=discord.Embed(
        description=f"🔨 {member.mention} забанен. Причина: {reason}",
        color=discord.Color.red()
    ))


@bot.command()
async def ping(ctx):
    """Проверка пинга"""
    await ctx.send(embed=discord.Embed(
        description=f"🏓 Pong! Задержка: {round(bot.latency * 1000)}ms",
        color=discord.Color.blue()
    ))


@bot.command()
async def online(ctx):
    """Проверка онлайна SAMP сервера"""
    info = get_samp_info(SAMP_IP, SAMP_PORT)
    if info:
        players, max_players = info
        embed = discord.Embed(
            title="🎮 Онлайн сервера",
            description=f"Игроков онлайн: **{players}/{max_players}**",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="⚠️ Сервер недоступен",
            description="Не удалось получить информацию. Проверь IP/порт.",
            color=discord.Color.red()
        )
    await ctx.send(embed=embed)


# ========== АВТО-СТАТУС ==========
@tasks.loop(seconds=60)  # обновление каждую минуту
async def update_status():
    info = get_samp_info(SAMP_IP, SAMP_PORT)
    if info:
        players, max_players = info
        status = discord.Game(f"🎮 Онлайн: {players}/{max_players}")
    else:
        status = discord.Game("⚠️ Сервер недоступен")
    await bot.change_presence(activity=status)


# Запуск
bot.run(TOKEN)
