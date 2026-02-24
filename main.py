import discord
from discord.ext import commands

import asyncio
from datetime import datetime as dt

import threading
from flask import Flask

from gtts import gTTS

import re
import random
import os
import subprocess

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="あめちゃん", intents=intents)

app = Flask(__name__)

@bot.event
async def on_ready():
    print(f"ログイン中のアカウント：{bot.user}")

class RecruitView(discord.ui.View):
    def __init__(self, max_people):
        super().__init__(timeout=None)
        self.max_people = max_people
        self.members = []

    @discord.ui.button(label="参加する", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        if user in self.members:
            self.members.remove(user)
            await interaction.response.send_message("参加を取り消しました", ephemeral=True)
        else:
            if len(self.members) >= self.max_people:
                await interaction.response.send_message("満員です！", ephemeral=True)
                return
            self.members.append(user)
            await interaction.response.send_message("参加しました！", ephemeral=True)

        embed = interaction.message.embeds[0]
        embed.set_field_at(
            1,
            name="👥 参加者",
            value="\n".join([m.mention for m in self.members]) or "まだいません",
            inline=False
        )

        embed.set_field_at(
            2,
            name="📊 状況",
            value=f"{len(self.members)}/{self.max_people}",
            inline=False
        )

        if len(self.members) >= self.max_people:
            embed.color = discord.Color.red()
            embed.title = "🔒 募集終了（満員）"
            for item in self.children:
                item.disabled = True

        await interaction.message.edit(embed=embed, view=self)


@bot.command()
async def 募集して(ctx, game: str, people: int):
    embed = discord.Embed(
        title="📢 ゲーム募集！",
        color=discord.Color.green()
    )

    embed.add_field(name="🎮 ゲーム", value=game, inline=False)
    embed.add_field(name="👥 参加者", value="まだいません", inline=False)
    embed.add_field(name="📊 状況", value=f"0/{people}", inline=False)
    embed.set_footer(text=f"募集者: {ctx.author.display_name}")

    view = RecruitView(people)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def ダイス振って(ctx, *, roll: str):
    pattern = r"(\d+)d(\d+)([+-]\d+)?"
    match = re.fullmatch(pattern, roll)

    if not match:
        await ctx.send("形式は 2d6 や 1d20+3 みたいに書いてね！")
        return

    dice_count = int(match.group(1))
    dice_sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if dice_count > 50:
        await ctx.send("ダイス振りすぎ！50個まで！")
        return

    rolls = [random.randint(1, dice_sides) for _ in range(dice_count)]
    total = sum(rolls) + modifier

    # 理論上の最大・最小
    max_total = dice_count * dice_sides + modifier
    min_total = dice_count * 1 + modifier

    roll_text = " + ".join(map(str, rolls))
    if modifier:
        roll_text += f" {'+' if modifier > 0 else ''}{modifier}"

    title = f"🎲 {roll}"
    color = discord.Color.purple()
    extra_text = ""

    if total == max_total:
        title = "🎯 クリティカル！！！"
        color = discord.Color.gold()
        extra_text = "\n\n🔥 最大合計値！"
    elif total == min_total:
        title = "💀 ファンブル…"
        color = discord.Color.red()
        extra_text = "\n\n⚠ 最小合計値…"

    embed = discord.Embed(
        title=title,
        description=f"内訳：{roll_text}\n\n🎉 合計：**{total}**{extra_text}",
        color=color
    )

    await ctx.send(embed=embed)


READ_CHANNEL_ID = 1296376638430249030

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="あめちゃん", intents=intents)

def rumor_format(user, text):
    patterns = [
        f"{user.display_name}さんが{text}だってさ",
        f"ねえねえ、{user.display_name}さんが{text}って！",
        f"{user.display_name}さん、{text}だって〜",
    ]
    return random.choice(patterns)

def ame_character(text):
    endings = ["だよ〜", "なのだよ！", "だぞっ！", "やよ〜！"]
    return text + " " + random.choice(endings)

def change_pitch(input_file, output_file, pitch=1.1):
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-af", f"asetrate=44100*{pitch},aresample=44100,atempo={1/pitch}",
        output_file
    ])

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == READ_CHANNEL_ID:
        if message.guild.voice_client is None:
            return

        vc = message.guild.voice_client
        if vc.is_playing():
            vc.stop()

        # ランダム発言＋語尾キャラ化
        text = rumor_format(message.author, message.content)
        text = ame_character(text)

        # gTTSで生成
        tts = gTTS(text=text, lang="ja")
        tts.save("read.mp3")

        # ピッチ調整
        pitch = random.uniform(1.0, 1.1)
        change_pitch("read.mp3", "read_pitch.mp3", pitch)

        # VCで再生
        vc.play(discord.FFmpegPCMAudio("read_pitch.mp3"))

    await bot.process_commands(message)


@bot.command()
async def きて(ctx):
    if ctx.author.voice is None:
        await ctx.send("先にVCに入ってね！")
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()

    await ctx.send("VCに入ったよ！")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1296118740592754711)
    if channel:
        embed = discord.Embed(
            title="new",
            description=f"{member.mention} ようこそあめのサーバーへ",
            color=discord.Color.pink()
        )
        await channel.send(embed=embed)

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# Webサーバーを別スレッドで起動
threading.Thread(target=run_web).start()

        
bot.run(os.getenv("TOKEN"))


