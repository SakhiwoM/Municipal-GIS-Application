import base64
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional


ROLE_PERMISSIONS: Dict[str, Dict[str, bool]] = {
    "administrator": {
        "view_map": True,
        "edit_spatial": True,
        "import_cadastre": True,
        "import_valuation": True,
        "link_data": True,
        "run_analysis": True,
        "generate_reports": True,
        "manage_users": True,
        "manage_licenses": True,
        "gis_admin": True,
        "view_dashboard": True,
        "data_quality": True,
        "export_data": True,
        "audit_logs": True,
    },
    "gis_specialist": {
        "view_map": True,
        "edit_spatial": True,
        "import_cadastre": True,
        "import_valuation": True,
        "link_data": True,
        "run_analysis": True,
        "generate_reports": True,
        "manage_users": False,
        "manage_licenses": False,
        "gis_admin": False,
        "view_dashboard": True,
        "data_quality": True,
        "export_data": True,
        "audit_logs": False,
    },
    "survey_officer": {
        "view_map": True,
        "edit_spatial": True,
        "import_cadastre": True,
        "import_valuation": False,
        "link_data": False,
        "run_analysis": False,
        "generate_reports": False,
        "manage_users": False,
        "manage_licenses": False,
        "gis_admin": False,
        "view_dashboard": True,
        "data_quality": False,
        "export_data": False,
        "audit_logs": False,
    },
    "viewer": {
        "view_map": True,
        "edit_spatial": False,
        "import_cadastre": False,
        "import_valuation": False,
        "link_data": False,
        "run_analysis": False,
        "generate_reports": False,
        "manage_users": False,
        "manage_licenses": False,
        "gis_admin": False,
        "view_dashboard": True,
        "data_quality": False,
        "export_data": False,
        "audit_logs": False,
    },
}

ROLE_DISPLAY = {
    "administrator": "Administrator",
    "gis_specialist": "GIS Specialist",
    "survey_officer": "Survey Officer",
    "viewer": "Viewer",
}

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
PASSWORD_SALT = "ESW_GIS_2026_SALT"


@dataclass
class UserProfile:
    username: str
    password_hash: str
    role: str
    full_name: str
    organization: str
    email: str
    last_login: Optional[str] = None
    failed_attempts: int = 0
    locked_until: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class SessionInfo:
    username: str
    full_name: str
    role: str
    organization: str
    login_time: str
    permissions: Dict[str, bool]


class AuthManager:
    def __init__(self, data_dir="."):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, ".esw_users.json")
        self.audit_file = os.path.join(data_dir, ".esw_audit.log")
        self._users: Dict[str, UserProfile] = {}
        self._session: Optional[SessionInfo] = None
        self._load_users()
        self._ensure_default_users()

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(f"{PASSWORD_SALT}{password}".encode()).hexdigest()

    def _load_users(self):
        if not os.path.exists(self.users_file):
            return

        try:
            with open(self.users_file, "rb") as f:
                raw = base64.b64decode(f.read()).decode()
            data = json.loads(raw)
            self._users = {
                key.lower(): UserProfile(**value)
                for key, value in data.items()
            }
        except Exception:
            self._users = {}

    def _save_users(self):
        os.makedirs(self.data_dir, exist_ok=True)
        data = {key: asdict(value) for key, value in self._users.items()}
        encoded = base64.b64encode(json.dumps(data, indent=2).encode())
        with open(self.users_file, "wb") as f:
            f.write(encoded)

    def _ensure_default_users(self):
        changed = False
        if "admin" not in self._users:
            self._users["admin"] = UserProfile(
                username="admin",
                password_hash=self.hash_password("Admin@2026"),
                role="administrator",
                full_name="System Administrator",
                organization="Eswatini Municipal Authority",
                email="admin@eswatini-gis.gov.sz",
            )
            changed = True
        if "gisuser" not in self._users:
            self._users["gisuser"] = UserProfile(
                username="gisuser",
                password_hash=self.hash_password("GIS@2026"),
                role="gis_specialist",
                full_name="GIS Specialist",
                organization="Eswatini Municipal Authority",
                email="gis@eswatini-gis.gov.sz",
            )
            changed = True
        if changed:
            self._save_users()

    def authenticate(self, username: str, password: str):
        username = username.strip().lower()
        if username not in self._users:
            self._audit(f"Failed login: unknown user '{username}'")
            return False, "Invalid username or password."

        user = self._users[username]
        if user.locked_until:
            locked_dt = datetime.fromisoformat(user.locked_until)
            if datetime.now() < locked_dt:
                remaining = int((locked_dt - datetime.now()).total_seconds() / 60) + 1
                return False, f"Account locked. Try again in {remaining} minute(s)."
            user.failed_attempts = 0
            user.locked_until = None

        if user.password_hash != self.hash_password(password):
            user.failed_attempts += 1
            if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = (
                    datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
                ).isoformat()
                self._audit(
                    f"Account locked: '{username}' after {MAX_FAILED_ATTEMPTS} failed attempts"
                )
                self._save_users()
                return False, f"Too many failed attempts. Account locked for {LOCKOUT_MINUTES} minutes."

            self._save_users()
            remaining = MAX_FAILED_ATTEMPTS - user.failed_attempts
            self._audit(f"Failed login: wrong password for '{username}'")
            return False, f"Invalid username or password. ({remaining} attempt(s) remaining)"

        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now().isoformat()
        self._save_users()

        self._session = SessionInfo(
            username=username,
            full_name=user.full_name,
            role=user.role,
            organization=user.organization,
            login_time=datetime.now().isoformat(),
            permissions=ROLE_PERMISSIONS.get(user.role, {}).copy(),
        )
        self._audit(f"Login success: '{username}' ({ROLE_DISPLAY.get(user.role, user.role)})")
        return True, f"Welcome, {user.full_name}!"

    def get_current_session(self) -> Optional[SessionInfo]:
        return self._session

    def logout(self):
        if self._session:
            self._audit(f"Logout: '{self._session.username}'")
        self._session = None

    def has_permission(self, permission: str) -> bool:
        if not self._session:
            return False
        return self._session.permissions.get(permission, False)

    def get_user(self, username: str) -> Optional[UserProfile]:
        return self._users.get(username.lower())

    def get_last_login(self, username: str) -> Optional[str]:
        user = self.get_user(username)
        if not user or not user.last_login:
            return None
        try:
            return datetime.fromisoformat(user.last_login).strftime("%d %b %Y  %H:%M")
        except Exception:
            return user.last_login

    def add_user(self, profile: UserProfile) -> bool:
        key = profile.username.lower()
        if key in self._users:
            return False
        self._users[key] = profile
        self._save_users()
        self._audit(f"User registered: '{key}' ({ROLE_DISPLAY.get(profile.role, profile.role)})")
        return True

    def list_users(self) -> List[UserProfile]:
        return list(self._users.values())

    def _audit(self, message: str):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    def get_audit_log(self, last_n: int = 50) -> List[str]:
        if not os.path.exists(self.audit_file):
            return []
        try:
            with open(self.audit_file, encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()[-last_n:]]
        except Exception:
            return []
