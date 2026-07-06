"""Cœur du chatbot : API Claude (SDK officiel anthropic) + outils catalogue/commande."""
import json
import os
from collections.abc import Iterator

import anthropic

from . import catalog

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")

SYSTEM_PROMPT = """Tu es ShopBot, l'assistant de vente de la boutique. Ton rôle :
- Accueillir chaleureusement les clients et répondre à leurs questions sur les produits.
- Utiliser l'outil search_products pour présenter les produits (nom, prix en Ariary, stock).
- Quand un client veut commander, demander son nom et son numéro de téléphone, puis utiliser create_order.
- Confirmer la commande avec le récapitulatif (produit, quantité, total) et préciser qu'un vendeur va le contacter.
- Rester concis (c'est une conversation type WhatsApp), amical, et répondre dans la langue du client (français ou malgache).
- Ne jamais inventer de produits ou de prix : utilise toujours les outils.
- Si la question sort du cadre de la boutique, ramener poliment la conversation aux produits."""

TOOLS = [
    {
        "name": "search_products",
        "description": "Recherche des produits dans le catalogue de la boutique. Appelle cet outil dès qu'un client demande ce qui est disponible, un prix, ou un type de produit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Mot-clé du produit recherché (vide = tout le catalogue)"},
                "category": {"type": "string", "description": "Catégorie : vêtements, artisanat, alimentation, bien-être"},
            },
            "required": [],
        },
    },
    {
        "name": "create_order",
        "description": "Enregistre une commande client. Appelle cet outil uniquement quand le client a confirmé le produit, la quantité, et donné son nom et son téléphone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "quantity": {"type": "integer"},
                "customer_name": {"type": "string"},
                "customer_phone": {"type": "string"},
            },
            "required": ["product_id", "quantity", "customer_name", "customer_phone"],
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> str:
    """Exécute un outil et retourne le résultat en JSON."""
    try:
        if name == "search_products":
            return json.dumps(catalog.search_products(
                tool_input.get("query", ""), tool_input.get("category", "")
            ), ensure_ascii=False)
        if name == "create_order":
            return json.dumps(catalog.create_order(**tool_input), ensure_ascii=False)
        return json.dumps({"error": f"Outil inconnu : {name}"})
    except (ValueError, TypeError) as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


class ShopBot:
    """Gère une conversation multi-tours avec streaming et boucle d'outils."""

    def __init__(self, client: anthropic.Anthropic | None = None):
        self.client = client or anthropic.Anthropic()
        self.sessions: dict[str, list] = {}

    def reply_stream(self, session_id: str, user_message: str) -> Iterator[str]:
        """Répond au client en streaming (texte token par token)."""
        messages = self.sessions.setdefault(session_id, [])
        messages.append({"role": "user", "content": user_message})

        while True:
            with self.client.messages.stream(
                model=MODEL,
                max_tokens=2048,
                system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                tools=TOOLS,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text
                response = stream.get_final_message()

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})

    def reply(self, session_id: str, user_message: str) -> str:
        """Réponse complète (pour le webhook WhatsApp, qui n'est pas streamé)."""
        return "".join(self.reply_stream(session_id, user_message))
