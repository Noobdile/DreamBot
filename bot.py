import json
import os
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

# Compatible avec TOKEN=... ou DISCORD_TOKEN=...
TOKEN = os.getenv("TOKEN") or os.getenv("DISCORD_TOKEN")
GUILD_ID_BRUT = os.getenv("GUILD_ID")

if not TOKEN:
    raise RuntimeError("TOKEN / DISCORD_TOKEN est absent du fichier .env.")

if not GUILD_ID_BRUT:
    raise RuntimeError("GUILD_ID est absent du fichier .env.")

GUILD_ID = int(GUILD_ID_BRUT)

FICHIER_RECETTES = BASE_DIR / "data" / "recettes.json"

with open(FICHIER_RECETTES, "r", encoding="utf-8") as fichier:
    RECETTES = json.load(fichier)


def normaliser_texte(texte: str) -> str:
    texte = texte.casefold()
    texte = texte.replace("œ", "oe")
    texte = texte.replace("’", "'")
    texte = unicodedata.normalize("NFD", texte)

    texte = "".join(
        caractere
        for caractere in texte
        if unicodedata.category(caractere) != "Mn"
    )

    texte = "".join(
        caractere if caractere.isalnum() else " "
        for caractere in texte
    )

    return " ".join(texte.split())


def trouver_recettes(nom: str):
    cle = normaliser_texte(nom)
    cle_json = cle.replace(" ", "_")

    if cle_json in RECETTES:
        return [RECETTES[cle_json]]

    exactes = []

    for recette in RECETTES.values():
        nom_recette = recette.get("nom", "")
        nom_fichier = recette.get("nomFichier", "")

        if (
            normaliser_texte(nom_recette) == cle
            or normaliser_texte(nom_fichier) == cle
        ):
            exactes.append(recette)

    if exactes:
        return exactes

    partielles = []

    for recette in RECETTES.values():
        nom_recette = normaliser_texte(recette.get("nom", ""))
        nom_fichier = normaliser_texte(recette.get("nomFichier", ""))

        if cle in nom_recette or cle in nom_fichier:
            partielles.append(recette)

    return partielles


def construire_message_recette(recette: dict):
    etoiles = "⭐" * int(recette.get("etoiles", 0))

    fichiers = []
    embeds = []

    # --------------------------------------------------------
    # RECETTE : petite image devant le nom du plat
    # --------------------------------------------------------

    embed_plat = discord.Embed()

    titre = (
        f'{recette["nom"]} '
        f'({recette["type"]}) '
        f'{etoiles}'
    )

    image_recette = recette.get("image")

    if image_recette:
        chemin = BASE_DIR / image_recette

        if chemin.is_file():
            filename = "recette.png"

            fichiers.append(
                discord.File(
                    str(chemin),
                    filename=filename
                )
            )

            embed_plat.set_author(
                name=titre,
                icon_url=f"attachment://{filename}"
            )
        else:
            embed_plat.set_author(name=titre)
    else:
        embed_plat.set_author(name=titre)

    embeds.append(embed_plat)

    # --------------------------------------------------------
    # INGRÉDIENTS : petite image devant chaque ingrédient
    # --------------------------------------------------------

    ingredients = recette.get("ingredients", [])
    images_ingredients = recette.get("imagesIngredients", [])

    for index, ingredient in enumerate(ingredients):
        embed_ingredient = discord.Embed()

        image_relative = (
            images_ingredients[index]
            if index < len(images_ingredients)
            else None
        )

        if image_relative:
            chemin = BASE_DIR / image_relative

            if chemin.is_file():
                filename = f"ingredient_{index + 1}.png"

                fichiers.append(
                    discord.File(
                        str(chemin),
                        filename=filename
                    )
                )

                embed_ingredient.set_author(
                    name=f"• {ingredient}",
                    icon_url=f"attachment://{filename}"
                )
            else:
                embed_ingredient.set_author(
                    name=f"• {ingredient}"
                )
        else:
            # Catégorie générique ou image absente.
            embed_ingredient.set_author(
                name=f"• {ingredient}"
            )

        embeds.append(embed_ingredient)

    # Phrase finale identique à ton bot actuel.
    embeds.append(
        discord.Embed(
            description=(
                "💡 Si tu veux une autre recette, "
                "tape `/recette nom_de_ta_recette`."
            )
        )
    )

    return embeds, fichiers


intents = discord.Intents.default()
intents.message_content = True


class DreamBot(commands.Bot):

    async def setup_hook(self) -> None:
        serveur = discord.Object(id=GUILD_ID)

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


@bot.event
async def on_ready():
    print(
        f"Connecté en tant que {bot.user}",
        flush=True
    )


async def autocomplete_recette(
    interaction: discord.Interaction,
    current: str
):
    recherche = normaliser_texte(current)
    suggestions = []

    for cle, recette in RECETTES.items():
        nom = recette.get("nom", "")

        if (
            not recherche
            or recherche in normaliser_texte(nom)
            or recherche in normaliser_texte(cle)
        ):
            suggestions.append(
                app_commands.Choice(
                    name=(
                        f"{nom} "
                        f"({recette.get('type', '')})"
                    )[:100],
                    value=cle[:100]
                )
            )

        if len(suggestions) >= 25:
            break

    return suggestions


@bot.tree.command(
    name="recette",
    description="Chercher une recette Disney Dreamlight Valley"
)
@app_commands.describe(
    nom="Nom de la recette"
)
@app_commands.autocomplete(
    nom=autocomplete_recette
)
async def commande_recette(
    interaction: discord.Interaction,
    nom: str
):
    resultats = trouver_recettes(nom)

    if not resultats:
        await interaction.response.send_message(
            "Recette introuvable.",
            ephemeral=True
        )
        return

    if len(resultats) > 1:
        liste = "\n".join(
            f"• {recette['nom']} ({recette['type']})"
            for recette in resultats[:10]
        )

        await interaction.response.send_message(
            (
                f"Plusieurs recettes correspondent à **{nom}** :\n\n"
                f"{liste}\n\n"
                "💡 Précise le nom de la recette."
            ),
            ephemeral=True
        )
        return

    recette = resultats[0]

    embeds, fichiers = construire_message_recette(
        recette
    )

    await interaction.response.send_message(
        embeds=embeds,
        files=fichiers
    )


bot.run(TOKEN)
