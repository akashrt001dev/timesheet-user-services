import jwt
from typing import Dict, Any


class OauthJwtDecoder:
    """
    Validates and decodes RS256 OAuth/OIDC JWTs using JWKS from the issuer.
    Compatible with Keycloak-style issuers where JWKS is at: {iss}/protocol/openid-connect/certs
    """

    def _normalize_bearer(self, token: str) -> str:
        return token[7:] if token.startswith("Bearer ") else token

    def decodeToken(self, token: str) -> Dict[str, Any]:
        """
        Decode and verify an OAuth JWT using JWKS from the issuer in the token's 'iss' claim.
        Audience verification is disabled by default to be more permissive; adjust as needed.
        """
        raw = self._normalize_bearer(token)
        try:
            # Read unverified claims to discover issuer
            unverified_claims = jwt.decode(raw, options={"verify_signature": False})
            iss = unverified_claims.get("iss")
            if not iss:
                raise Exception("Missing 'iss' in token")

            jwks_url = iss.rstrip("/") + "/protocol/openid-connect/certs"

            # Fetch signing key and verify signature
            jwks_client = jwt.PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(raw).key

            payload = jwt.decode(
                raw,
                signing_key,
                algorithms=["RS256"],
                options={
                    "verify_exp": True,
                    "verify_aud": False,  # set to True and pass audience=... if required
                },
            )
            return payload
        except jwt.PyJWTError as e:
            # Optional: fallback for local testing if JWKS not reachable
            import os
            if os.getenv("OAUTH_DECODE_FALLBACK", "false").lower() == "true":
                return jwt.decode(raw, options={"verify_signature": False})
            raise Exception(f"Token validation failed: {e}")
        except Exception as e:
            import os
            if os.getenv("OAUTH_DECODE_FALLBACK", "false").lower() == "true":
                return jwt.decode(raw, options={"verify_signature": False})
            raise Exception(f"An unexpected error occurred during token decoding: {e}")

    def getPreferredUserNameFromOauthToken(self, token: str, jwks_url: str) -> str:
        raw = self._normalize_bearer(token)
        try:
            jwks_client = jwt.PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(raw).key
            payload = jwt.decode(
                raw,
                signing_key,
                algorithms=["RS256"],
                options={"verify_exp": True, "verify_aud": False},
            )
            return payload.get("preferred_username")
        except jwt.PyJWTError as e:
            raise Exception(f"Token validation failed: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred during token decoding: {e}")