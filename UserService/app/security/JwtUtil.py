import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.models.aggregates.root.User import User

class JwtUtil:
    def __init__(self):
        self.secret = settings.JWT_SECRET
        self.expiration_seconds = settings.JWT_EXPIRATION_SECONDS
        # Use algorithm from settings (defaults to HS256) and normalize quotes/spaces
        alg = getattr(settings, 'JWT_ALGORITHM', "HS256")
        if isinstance(alg, str):
            alg = alg.strip().strip('"').strip("'")
        self.ALGORITHM = alg or "HS256"
        # Allow decoding with multiple algorithms if configured
        allowed = getattr(settings, 'JWT_ALLOWED_ALGORITHMS', None)
        if isinstance(allowed, str) and allowed.strip():
            self.allowed_algorithms = [a.strip().strip('"').strip("'") for a in allowed.split(',') if a.strip()]
        else:
            # Default to common HS algorithms to improve compatibility
            base = (self.ALGORITHM or "HS256").upper()
            defaults = [base]
            if base != "HS512":
                defaults.append("HS512")
            if base != "HS256":
                defaults.append("HS256")
            self.allowed_algorithms = list(dict.fromkeys(defaults))  # de-dup while preserving order

    def getAllClaimsFromToken(self, token: str) -> Dict[str, Any]:
        if token.startswith("Bearer "):
            token = token[7:]
        try:
            return jwt.decode(token, self.secret, algorithms=self.allowed_algorithms)
        except jwt.PyJWTError as e:
            # Handle decoding errors (e.g., invalid signature, expired token)
            raise ValueError(f"Invalid token: {e}")

    def getExpirationDateFromToken(self, token: str) -> datetime:
        claims = self.getAllClaimsFromToken(token)
        return datetime.fromtimestamp(claims["exp"], tz=timezone.utc)

    def isTokenExpired(self, token: str) -> bool:
        try:
            exp_date = self.getExpirationDateFromToken(token)
            return exp_date < datetime.now(timezone.utc)
        except ValueError:
            return True

    def getUserEmailFromToken(self, token: str) -> str:
        claims = self.getAllClaimsFromToken(token)
        return claims.get("sub")

    def getUserIdFromToken(self, token: str) -> str:
        claims = self.getAllClaimsFromToken(token)
        return claims.get("id")

    def generate(self, user: User, token_type: str, tenantId: str, userSessionObjectId: str) -> str:
        claims = {
            "id": user.id,
            "userName": user.name.getFullName() if user.name else "",
            "suffix": user.name.suffix if user.name and user.name.suffix else "",
            "roles": ",".join([role.roleName for role in user.roles if role]),
            "userSessionObjectId": userSessionObjectId,
            "accessLevel": user.accessLevel.value if user.accessLevel else "",
            "proxyEnabled": user.isSurrogateEnabled
        }
        
        site_titles = {}
        if user.sites and user.sites.sites:
            for site in user.sites.sites:
                if site.id and site.siteResponsibility and site.siteResponsibility.id:
                    site_titles[site.id] = site.siteResponsibility.dict()
        claims["siteTitles"] = site_titles
        
        if user.title:
            claims["title"] = user.title.title
        
        if user.passwordCreatedDate:
            days_since_creation = (datetime.now(timezone.utc) - user.passwordCreatedDate).days
            claims["passwordExpiresIn(Days)"] = days_since_creation
        else:
            claims["passwordExpiresIn(Days)"] = 0
            
        return self.doGenerateToken(claims, user.ssoId.id, token_type)

    def doGenerateToken(self, claims: Dict[str, Any], username: str, token_type: str) -> str:
        if token_type == "ACCESS":
            expire_delta = timedelta(seconds=self.expiration_seconds)
        else: # REFRESH
            expire_delta = timedelta(seconds=self.expiration_seconds * 5)
        
        to_encode = claims.copy()
        issued_at = datetime.now(timezone.utc)
        expire_at = issued_at + expire_delta
        
        to_encode.update({
            "sub": username,
            "iat": issued_at,
            "exp": expire_at
        })
        return jwt.encode(to_encode, self.secret, algorithm=self.ALGORITHM)

    def getUserSessionID(self, token: str) -> str:
        claims = self.getAllClaimsFromToken(token)
        return claims.get("userSessionObjectId")

    def getUserAccessLevelFromToken(self, token: str) -> str:
        claims = self.getAllClaimsFromToken(token)
        return claims.get("accessLevel")
        
    def getNameFromToken(self, token: str) -> str:
        claims = self.getAllClaimsFromToken(token)
        return claims.get("userName")