import json
import os
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID_BRUT = os.getenv("GUILD_ID")

if not TOKEN:
    raise RuntimeError(
        "TOKEN est absent du fichier .env."
    )

if not GUILD_ID_BRUT:
    raise RuntimeError(
        "GUILD_ID est absent du fichier .env."
    )

GUILD_ID = int(
    GUILD_ID_BRUT
)


# ============================================================
# FICHIERS
# ============================================================

DOSSIER_DATA = Path("data")

FICHIER_RECETTES = (
    DOSSIER_DATA
    / "recettes.json"
)


# ============================================================
# CHARGEMENT DES RECETTES
# ============================================================

with open(
    FICHIER_RECETTES,
    "r",
    encoding="utf-8"
) as fichier:

    RECETTES = json.load(
        fichier
    )


# ============================================================
# NORMALISATION DU TEXTE
# ============================================================

def normaliser_texte(
    texte: str
) -> str:

    texte = texte.casefold()

    texte = texte.replace(
        "œ",
        "oe"
    )

    texte = texte.replace(
        "’",
        "'"
    )

    texte = unicodedata.normalize(
        "NFD",
        texte
    )

    texte = "".join(
        caractere
        for caractere in texte
        if unicodedata.category(
            caractere
        ) != "Mn"
    )

    texte = "".join(
        caractere
        if caractere.isalnum()
        else " "
        for caractere in texte
    )

    return " ".join(
        texte.split()
    )


# ============================================================
# RECHERCHE D'UNE RECETTE
# ============================================================

def trouver_recette(
    nom: str
):

    cle = normaliser_texte(
        nom
    )

    cle_json = cle.replace(
        " ",
        "_"
    )

    # Recherche directement avec la clé JSON.
    if cle_json in RECETTES:

        return RECETTES[
            cle_json
        ]

    # Recherche avec le nom affiché.
    for recette in RECETTES.values():

        nom_recette = recette.get(
            "nom",
            ""
        )

        if normaliser_texte(
            nom_recette
        ) == cle:

            return recette

    return None


# ============================================================
# FORMATAGE D'UNE RECETTE
# ============================================================

def format_recette(
    nom: str
) -> str:

    recette = trouver_recette(
        nom
    )

    if recette is None:

        return (
            "Recette introuvable."
        )

    etoiles = "⭐" * int(
        recette.get(
            "etoiles",
            0
        )
    )

    ingredients = "\n".join(
        f"- {ingredient}"
        for ingredient
        in recette.get(
            "ingredients",
            []
        )
    )

    return (
        f'**{recette["nom"]} '
        f'({recette["type"]})** '
        f'{etoiles}\n\n'
        f'{ingredients}'
        f'Si tu veux une recette, tape `/recette nom_de_ta_recette`'
    )


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()
intents.message_content = True


class DreamBot(
    commands.Bot
):

    async def setup_hook(
        self
    ) -> None:

        serveur = discord.Object(
            id=GUILD_ID
        )

        self.tree.copy_global_to(
            guild=serveur
        )

        await self.tree.sync(
            guild=serveur
        )

        print(
            "Commandes synchronisées.",
            flush=True
        )


bot = DreamBot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# BOT CONNECTÉ
# ============================================================

@bot.event
async def on_ready():

    print(
        f"Connecté en tant que "
        f"{bot.user}",
        flush=True
    )


# ============================================================
# COMMANDE /RECETTE
# ============================================================

@bot.tree.command(
    name="recette",
    description=(
        "Chercher une recette "
        "Disney Dreamlight Valley"
    )
)
@app_commands.describe(
    nom="Nom de la recette"
)
async def commande_recette(
    interaction: discord.Interaction,
    nom: str
):

    await interaction.response.send_message(
        format_recette(
            nom
        )
    )


# ============================================================
# DÉMARRAGE
# ============================================================

bot.run(
    TOKEN
)