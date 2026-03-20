"""
Servicio para manejar integracion con Messenger e Instagram Messaging (Meta Graph API).
"""
import os
import hmac
import hashlib
import logging
from typing import Dict, Any, List

import aiohttp
import requests
from fastapi import HTTPException
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


class MetaMessagingService:
    def __init__(self):
        self.page_id = os.getenv("META_PAGE_ID", "").strip()
        self.page_access_token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
        self.ig_business_id = os.getenv("META_IG_BUSINESS_ID", "").strip()
        self.ig_access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
        self.verify_token = os.getenv("META_VERIFY_TOKEN", "IMPULSO_META_VERIFY_TOKEN").strip()
        self.app_secret = os.getenv("META_APP_SECRET", "").strip()
        self.graph_version = os.getenv("META_GRAPH_VERSION", "v21.0")
        self.base_url = f"https://graph.facebook.com/{self.graph_version}"

    def validate_config(self, platform: str = "messenger") -> bool:
        """Valida configuracion minima para enviar mensajes."""
        if platform == "instagram":
            if self.ig_business_id and self.ig_access_token:
                return True
            # fallback a page token
            if self.page_id and self.page_access_token:
                return True
            logger.error("Configuracion de Instagram incompleta")
            return False
        if not self.page_id or not self.page_access_token:
            logger.error("Configuracion de Meta Messaging incompleta")
            return False
        return True

    def get_headers(self, platform: str = "messenger") -> Dict[str, str]:
        """Headers para requests al Graph API."""
        if platform == "instagram" and self.ig_access_token:
            token = self.ig_access_token
        else:
            token = self.page_access_token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def normalize_platform(self, platform: str) -> str:
        """Normaliza nombres de plataforma permitidos."""
        normalized = (platform or "").strip().lower()
        if normalized in ("facebook", "messenger", "page"):
            return "messenger"
        if normalized in ("instagram", "ig"):
            return "instagram"
        raise HTTPException(status_code=400, detail="Plataforma invalida. Usa 'messenger' o 'instagram'")

    def verify_signature(self, payload: bytes, signature_header: str) -> bool:
        """
        Verifica firma X-Hub-Signature-256 del webhook.
        Si no hay APP_SECRET configurado, no bloquea.
        """
        if not self.app_secret:
            return True

        if not signature_header:
            logger.warning("Falta header X-Hub-Signature-256")
            return False

        try:
            scheme, signature = signature_header.split("=", 1)
        except ValueError:
            return False

        if scheme != "sha256":
            return False

        expected = hmac.new(
            self.app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def _token_for_platform(self, platform: str = "messenger") -> str:
        if platform == "instagram" and self.ig_access_token:
            return self.ig_access_token
        return self.page_access_token

    def _sync_graph_get(self, path: str, *, params: Dict[str, Any] = None, token: str = "") -> Dict[str, Any]:
        effective_token = token or self.page_access_token
        request_params = dict(params or {})
        request_params["access_token"] = effective_token

        response = requests.get(
            f"{self.base_url}/{path.lstrip('/')}",
            params=request_params,
            timeout=20,
        )

        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text[:500]}

        return {"status_code": response.status_code, "data": data}

    def _extract_granted_permissions(self, token: str) -> List[str]:
        response = self._sync_graph_get("me/permissions", token=token)
        if response["status_code"] != 200:
            return []

        permissions = []
        for item in response["data"].get("data", []):
            if item.get("status") == "granted":
                permissions.append(item.get("permission"))
        return permissions

    def get_diagnostics(self) -> Dict[str, Any]:
        diagnostics: Dict[str, Any] = {
            "config": {
                "graph_version": self.graph_version,
                "page_id": self.page_id or None,
                "ig_business_id": self.ig_business_id or None,
                "page_access_token_present": bool(self.page_access_token),
                "instagram_access_token_present": bool(self.ig_access_token),
                "app_secret_present": bool(self.app_secret),
            },
            "token_checks": {},
            "linked_assets": {"pages": []},
            "warnings": [],
            "recommendations": [],
        }

        token_map = {
            "page_token": self.page_access_token,
            "instagram_token": self.ig_access_token,
        }

        for label, token in token_map.items():
            if not token:
                diagnostics["token_checks"][label] = {"present": False}
                continue

            me_response = self._sync_graph_get("me", params={"fields": "id,name"}, token=token)
            ig_response = None
            if self.ig_business_id:
                ig_response = self._sync_graph_get(
                    self.ig_business_id,
                    params={"fields": "id,username,name"},
                    token=token,
                )

            granted_permissions = self._extract_granted_permissions(token)
            messaging_permissions = sorted(
                permission
                for permission in granted_permissions
                if "messaging" in permission or permission.startswith("instagram_")
            )

            diagnostics["token_checks"][label] = {
                "present": True,
                "me_status_code": me_response["status_code"],
                "me": me_response["data"],
                "ig_account_status_code": ig_response["status_code"] if ig_response else None,
                "ig_account": ig_response["data"] if ig_response else None,
                "messaging_permissions": messaging_permissions,
            }

        page_accounts_response = self._sync_graph_get(
            "me/accounts",
            params={"fields": "id,name,tasks,instagram_business_account{id,username,name}"},
            token=self.page_access_token or self.ig_access_token,
        )

        if page_accounts_response["status_code"] == 200:
            pages = page_accounts_response["data"].get("data", [])
            for page in pages:
                diagnostics["linked_assets"]["pages"].append(
                    {
                        "id": page.get("id"),
                        "name": page.get("name"),
                        "tasks": page.get("tasks", []),
                        "instagram_business_account": page.get("instagram_business_account"),
                    }
                )

            matched_page = None
            if self.ig_business_id:
                for page in pages:
                    ig_account = page.get("instagram_business_account") or {}
                    if ig_account.get("id") == self.ig_business_id:
                        matched_page = page
                        break

            diagnostics["linked_assets"]["matched_page_for_instagram"] = (
                {
                    "id": matched_page.get("id"),
                    "name": matched_page.get("name"),
                }
                if matched_page
                else None
            )

            if matched_page and self.page_id and matched_page.get("id") != self.page_id:
                diagnostics["warnings"].append(
                    "META_PAGE_ID no coincide con la pagina conectada al Instagram configurado."
                )
                diagnostics["recommendations"].append(
                    f"Actualiza META_PAGE_ID a {matched_page.get('id')}."
                )

            if not matched_page and self.ig_business_id:
                diagnostics["warnings"].append(
                    "No se encontro ninguna pagina en /me/accounts conectada al META_IG_BUSINESS_ID configurado."
                )
        else:
            diagnostics["warnings"].append("No se pudo consultar /me/accounts con el token configurado.")
            diagnostics["linked_assets"]["pages_error"] = page_accounts_response

        instagram_permissions = diagnostics["token_checks"].get("instagram_token", {}).get("messaging_permissions", [])
        if "instagram_manage_messages" not in instagram_permissions:
            diagnostics["warnings"].append(
                "El token de Instagram no reporta instagram_manage_messages como permiso otorgado."
            )

        diagnostics["recommendations"].append(
            "Si el POST /{ig_business_id}/messages sigue devolviendo code 3, revisa en Meta que la app tenga habilitada la capacidad de Instagram Messaging para esa cuenta."
        )

        return diagnostics

    async def send_text_message(self, platform: str, recipient_id: str, message: str) -> Dict[str, Any]:
        """Envia mensaje de texto a Messenger o Instagram."""
        normalized_platform = self.normalize_platform(platform)

        if not self.validate_config(normalized_platform):
            raise HTTPException(status_code=500, detail="Configuracion de Meta Messaging incompleta")

        # Graph API Explorer confirma que /me/messages funciona correctamente para Instagram.
        url = f"{self.base_url}/me/messages"
        params = None

        payload: Dict[str, Any] = {
            "recipient": {"id": recipient_id},
            "message": {"text": message},
        }

        try:
            async with aiohttp.ClientSession() as session:
                logger.info(
                    "Enviando mensaje Meta via %s a %s usando %s/messages",
                    normalized_platform,
                    recipient_id,
                    "me",
                )
                async with session.post(
                    url,
                    params=params,
                    json=payload,
                    headers=self.get_headers(normalized_platform),
                ) as response:
                    result = await response.json()

                    if response.status in (200, 201):
                        logger.info("Mensaje enviado a %s (%s)", recipient_id, normalized_platform)
                        return result

                    logger.error(
                        "Error enviando mensaje Meta: %s - %s",
                        response.status,
                        result,
                    )
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Error de Meta API: {result.get('error', {}).get('message', 'Unknown error')}",
                    )
        except aiohttp.ClientError as e:
            logger.error("Error de conexion con Meta API: %s", str(e))
            raise HTTPException(status_code=500, detail="Error de conexion con Meta API")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error inesperado enviando mensaje Meta: %s", str(e))
            raise HTTPException(status_code=500, detail="Error interno del servidor")


meta_messaging_service = MetaMessagingService()
