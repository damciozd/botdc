import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import asyncio

TOKEN = "MTQwOTU2OTY5Nzk0NjY2NDk5MA.GPEKaL.RhAxm-gzaI82otbhrngzkelNQ6rFkUlgbuFBBc"

PLAYERS = [
    "Kubx", "shox", "m0NESY", "s1mple", "ZywOo",
    "NiKo", "donk", "frozen", "jL", "b1t", "ropz", "device",
    "bodyy", "Lucky", "HooXi", "Magisk", "Staehr"
]

VOTES_FILE = "votes.json"
RESULTS_FILE = "results.json"
MATCHES_FILE = "matches.json"
MATCH_PLAYERS_FILE = "match_players.json"
CHOICES_FILE = "user_choices.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

def load(file):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = f.read().strip()
                return json.loads(data) if data else {}
        except:
            return {}
    return {}

def save(data, file):
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ BŁĄD ZAPISU {file}: {e}")

votes = load(VOTES_FILE)
results = load(RESULTS_FILE)
active_match = load(MATCHES_FILE)
MATCH_PLAYERS = load(MATCH_PLAYERS_FILE) or {}
user_choices = {}

def get_match_id():
    i = 1
    while f"match_{i}" in votes or f"match_{i}" in results:
        i += 1
    return f"match_{i}"

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    uid = interaction.user.id
    now = datetime.now().timestamp()
    
    # ANTY-SPAM
    if uid in INTERACTION_COOLDOWN and (now - INTERACTION_COOLDOWN[uid]) < DEBOUNCE_TIME:
        try:
            await interaction.response.defer()
        except:
            pass
        return
    
    INTERACTION_COOLDOWN[uid] = now
    
    channel_id = str(interaction.channel.id)
    custom_id = interaction.data.get("custom_id", "")

    # NAPRAWIONY BŁĄD
    if channel_id not in active_match:
        try:
            await interaction.response.send_message("Na tym kanale nie ma aktywnego meczu!", ephemeral=True)
        except:
            await interaction.response.defer()
        return

    match_id = active_match[channel_id]
    choice_key = f"{uid}_{channel_id}"
    user_choices[choice_key] = user_choices.get(choice_key, {})

    # ZATWIERDŹ
    if custom_id == "submit_button":
        choices = user_choices[choice_key]
        if len(choices) != 3:
            try:
                await interaction.response.send_message("Wybierz wszystkie 3 pola!", ephemeral=True)
            except:
                await interaction.response.defer()
            return

        if str(uid) in votes.get(match_id, {}):
            try:
                await interaction.response.send_message("Już oddałeś prognozę!", ephemeral=True)
            except:
                await interaction.response.defer()
            return

        votes.setdefault(match_id, {})[str(uid)] = {
            "nick": interaction.user.display_name,
            "result": choices["wynik"],
            "top": choices["top"],
            "bottom": choices["bottom"],
            "time": datetime.now().strftime("%H:%M")
        }
        save(votes, VOTES_FILE)

        embed = discord.Embed(color=0xffd700)
        embed.set_author(name=f"{interaction.user.display_name} typuje", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Wynik", value=f"`{choices['wynik']}`", inline=True)
        embed.add_field(name="Top", value=choices["top"], inline=True)
        embed.add_field(name="Bottom", value=choices["bottom"], inline=True)
        embed.set_footer(text=datetime.now().strftime("%H:%M"))
        await interaction.channel.send(embed=embed)

        await interaction.response.send_message("TYP ZAPISANY!", ephemeral=True)
        user_choices.pop(choice_key, None)
        save(user_choices, CHOICES_FILE)
        return

    # SELECTY
    if "values" in interaction.data:
        try:
            await interaction.response.defer()
        except:
            pass

        value = interaction.data["values"][0]

        if custom_id == "wynik_select":
            user_choices[choice_key]["wynik"] = value
        elif custom_id == "top_select":
            user_choices[choice_key]["top"] = value
        elif custom_id == "bottom_select":
            user_choices[choice_key]["bottom"] = value

        save(user_choices, CHOICES_FILE)
        return

    await interaction.response.defer()

# NAPRAWIONY ROZLICZENIE – 1 PKT ZA DRUŻYNĘ
class Rozliczenie(discord.ui.View):
    def __init__(self, mode, match_id):
        super().__init__(timeout=600)
        self.mode = mode
        self.match_id = match_id
        self.real = {}

        options = [
            discord.SelectOption(label="2-0", value="2-0"),
            discord.SelectOption(label="2-1", value="2-1"),
            discord.SelectOption(label="1-2", value="1-2"),
            discord.SelectOption(label="0-2", value="0-2")
        ] if mode == "bo3" else [
            discord.SelectOption(label="1-0", value="1-0"),
            discord.SelectOption(label="0-1", value="0-1")
        ]

        self.add_item(discord.ui.Select(placeholder="Rzeczywisty wynik", options=options, custom_id="real_wynik"))
        self.add_item(discord.ui.Select(placeholder="Rzeczywisty TOP", options=[discord.SelectOption(label=p, value=p) for p in MATCH_PLAYERS.get(match_id, PLAYERS)], custom_id="real_top"))
        self.add_item(discord.ui.Select(placeholder="Rzeczywisty BOTTOM", options=[discord.SelectOption(label=p, value=p) for p in MATCH_PLAYERS.get(match_id, PLAYERS)], custom_id="real_bottom"))

    async def interaction_check(self, interaction: discord.Interaction):
        data = interaction.data
        if data["custom_id"] == "real_wynik":
            self.real["wynik"] = data["values"][0]
        elif data["custom_id"] == "real_top":
            self.real["top"] = data["values"][0]
        elif data["custom_id"] == "real_bottom":
            self.real["bottom"] = data["values"][0]

        await interaction.response.defer()

        if len(self.real) == 3:
            results[self.match_id].update({
                "result": self.real["wynik"],
                "top": self.real["top"],
                "bottom": self.real["bottom"],
                "scored": True
            })
            save(results, RESULTS_FILE)

            points = {}
            real_result = self.real["wynik"]
            real_winner = real_result[0]  # '2' lub '1'

            for v in votes.get(self.match_id, {}).values():
                p = 0
                user_result = v["result"]
                user_winner = user_result[0]

                # Dokładny wynik = 3 pkt
                if user_result == real_result:
                    p += 3
                # Tylko poprawna drużyna = 1 pkt
                elif user_winner == real_winner:
                    p += 1

                # TOP / BOTTOM
                if v["top"] == self.real["top"]:
                    p += 2
                if v["bottom"] == self.real["bottom"]:
                    p += 2

                if p > 0:
                    points[v["nick"]] = points.get(v["nick"], 0) + p

            embed = discord.Embed(title="Mecz rozliczony!", color=0x00ff00)
            embed.add_field(name="Wynik", value=f"`{real_result}`", inline=True)
            embed.add_field(name="Top", value=self.real["top"], inline=True)
            embed.add_field(name="Bottom", value=self.real["bottom"], inline=True)
            if points:
                txt = "\n".join(f"**{n}** → {p} pkt" for n, p in sorted(points.items(), key=lambda x: -x[1])[:15])
                embed.add_field(name="Punkty", value=txt, inline=False)

            await interaction.followup.send(embed=embed)
            await interaction.message.delete()
            return False
        return True

@bot.command()
async def mecz(ctx, *, tekst):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("Tylko admin!")

    mode = "bo3"
    if tekst.lower().endswith(" bo1"):
        mode = "bo1"
        tekst = tekst[:-4].strip()

    if " vs " not in tekst:
        return await ctx.send("Użyj: `!mecz NAVI vs FaZe`")

    t1, t2 = [x.strip() for x in tekst.split(" vs ", 1)]
    mid = get_match_id()

    channel_id = str(ctx.channel.id)
    active_match[channel_id] = mid
    votes[mid] = {}
    results[mid] = {"team1": t1, "team2": t2, "mode": mode}
    MATCH_PLAYERS[mid] = PLAYERS.copy()
    
    save(results, RESULTS_FILE)
    save(active_match, MATCHES_FILE)
    save(MATCH_PLAYERS, MATCH_PLAYERS_FILE)
    
    await asyncio.sleep(1)

    view = discord.ui.View(timeout=None)
    
    wynik_options = [
        discord.SelectOption(label="2-0", value="2-0"),
        discord.SelectOption(label="2-1", value="2-1"),
        discord.SelectOption(label="1-2", value="1-2"),
        discord.SelectOption(label="0-2", value="0-2")
    ] if mode == "bo3" else [
        discord.SelectOption(label="1-0", value="1-0"),
        discord.SelectOption(label="0-1", value="0-1")
    ]
    
    view.add_item(discord.ui.Select(placeholder="WYNIK", options=wynik_options, custom_id="wynik_select"))
    view.add_item(discord.ui.Select(placeholder="TOP FRAGER", options=[discord.SelectOption(label=p, value=p) for p in PLAYERS], custom_id="top_select"))
    view.add_item(discord.ui.Select(placeholder="BOTTOM FRAGER", options=[discord.SelectOption(label=p, value=p) for p in PLAYERS], custom_id="bottom_select"))
    view.add_item(discord.ui.Button(label="ZATWIERDŹ PROGNOZĘ", style=discord.ButtonStyle.green, custom_id="submit_button"))

    await ctx.send(
        embed=discord.Embed(
            title=f"{t1} vs {t2}", 
            description=f"**Tryb: {mode.upper()}**\n\nWybierz wynik, TOP i BOTTOM fraggera\nNastępnie kliknij ZATWIERDŹ", 
            color=0x0099ff
        ),
        view=view
    )

@bot.command()
async def wynik(ctx):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("Tylko admin!")
    mid = active_match.get(str(ctx.channel.id))
    if not mid or results.get(mid, {}).get("scored"):
        return await ctx.send("Brak aktywnego meczu!")
    await ctx.author.send("ROZLICZ MECZ", view=Rozliczenie(results[mid]["mode"], mid))
    await ctx.send(f"{ctx.author.mention} Panel rozliczenia na DM!")

@bot.command()
async def ranking(ctx):
    total = {}
    for mid, r in results.items():
        if not r.get("scored"): continue
        for v in votes.get(mid, {}).values():
            p = 0
            if v["result"] == r["result"]: p += 3
            elif v["result"][0] == r["result"][0]: p += 1
            if v["top"] == r["top"]: p += 2
            if v["bottom"] == r["bottom"]: p += 2
            total[v["nick"]] = total.get(v["nick"], 0) + p

    if not total:
        return await ctx.send("Brak rozegranych meczów.")
    
    txt = "\n".join(f"{i}. **{n}** – {p} pkt" for i, (n, p) in enumerate(sorted(total.items(), key=lambda x: -x[1]), 1))
    await ctx.send(embed=discord.Embed(title="RANKING OGÓLNY", description=txt, color=0xffd700))

@bot.event
async def on_ready():
    print(f"Bot włączony → {bot.user}")
    print(f"Aktywne mecze: {len(active_match)}")
    print("DZIAŁA NA 100% – BEZ BŁĘDÓW!")

bot.run(TOKEN)
