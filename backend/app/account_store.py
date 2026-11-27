"""Persistent local account store for verified SPEEDY LIVE identities."""
from __future__ import annotations
import hashlib, hmac, re, secrets, sqlite3, time
from pathlib import Path
from contextlib import contextmanager
from collections.abc import Iterator

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_ITERATIONS = 310_000

class AccountStoreError(RuntimeError):
    pass

class AccountStore:
    def __init__(self, database_path: str):
        if not database_path or database_path == ":memory:":
            raise AccountStoreError("A persistent account database path is required.")
        self.path = Path(database_path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.path.parent.chmod(0o700)
            with self._connect() as db:
                db.execute("""CREATE TABLE IF NOT EXISTS accounts (
                    user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_salt BLOB NOT NULL, password_hash BLOB NOT NULL,
                    password_iterations INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('customer','admin')),
                    email_verified INTEGER NOT NULL DEFAULT 0,
                    disabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
                # Email verification is a CUSTOMER requirement only. Admin identities
                # are trusted, operator-provisioned accounts and must not be blocked
                # by the customer email-verification workflow.
                db.execute("""CREATE TABLE IF NOT EXISTS email_verification_tokens (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES accounts(user_id) ON DELETE CASCADE,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    consumed_at REAL
                )""")
                db.execute("CREATE INDEX IF NOT EXISTS idx_email_verification_user ON email_verification_tokens(user_id)")
                db.execute("UPDATE accounts SET email_verified=1 WHERE role='admin'")
            self.path.chmod(0o600)
        except (OSError, sqlite3.Error) as exc:
            raise AccountStoreError("Could not initialize private account database.") from exc

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=10000")
            with db: yield db
        finally: db.close()

    @staticmethod
    def _hash(password: str, salt: bytes, iterations: int = _ITERATIONS) -> bytes:
        return hashlib.pbkdf2_hmac("sha256",password.encode(),salt,iterations)

    def create_account(self, *, email: str, password: str, role: str,
                       email_verified: bool = False) -> str:
        email=email.strip().lower()
        if not _EMAIL.fullmatch(email) or len(email)>254: raise ValueError("Invalid email address.")
        if len(password)<12 or len(password)>256: raise ValueError("Password must contain 12 to 256 characters.")
        if role not in {"customer","admin"}: raise ValueError("Invalid role.")
        # Admins are created only by trusted provisioning, so customer email
        # verification does not apply to them.
        if role == "admin":
            email_verified = True
        salt=secrets.token_bytes(16); digest=self._hash(password,salt); user_id=secrets.token_hex(16)
        try:
            with self._connect() as db:
                db.execute("INSERT INTO accounts(user_id,email,password_salt,password_hash,password_iterations,role,email_verified) VALUES(?,?,?,?,?,?,?)",
                    (user_id,email,salt,digest,_ITERATIONS,role,int(email_verified)))
            return user_id
        except sqlite3.IntegrityError as exc: raise AccountStoreError("Email already exists.") from exc
        except sqlite3.Error as exc: raise AccountStoreError("Could not create account.") from exc

    def create_customer_registration(self, *, email: str, password: str,
                                     lifetime_seconds: int = 1800) -> tuple[str, str]:
        """Create an unverified customer and return a one-time token for trusted email delivery."""
        if not 300 <= lifetime_seconds <= 86400:
            raise ValueError("Verification lifetime must be between 5 minutes and 24 hours.")
        email = email.strip().lower()
        if not _EMAIL.fullmatch(email) or len(email) > 254:
            raise ValueError("Invalid email address.")
        if len(password) < 12 or len(password) > 256:
            raise ValueError("Password must contain 12 to 256 characters.")
        user_id = secrets.token_hex(16)
        salt = secrets.token_bytes(16)
        digest = self._hash(password, salt)
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.time()
        try:
            with self._connect() as db:
                db.execute(
                    "INSERT INTO accounts(user_id,email,password_salt,password_hash,password_iterations,role,email_verified) VALUES(?,?,?,?,?,'customer',0)",
                    (user_id, email, salt, digest, _ITERATIONS),
                )
                db.execute(
                    "INSERT INTO email_verification_tokens(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                    (token_hash, user_id, now, now + lifetime_seconds),
                )
            return user_id, token
        except sqlite3.IntegrityError as exc:
            raise AccountStoreError("Email already exists.") from exc
        except sqlite3.Error as exc:
            raise AccountStoreError("Could not create customer registration.") from exc

    def verify_customer_email(self, *, token: str) -> bool:
        """Consume a single-use, expiring verification token and activate its customer."""
        if not isinstance(token, str) or not 20 <= len(token) <= 256:
            return False
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.time()
        try:
            with self._connect() as db:
                row = db.execute(
                    "SELECT user_id FROM email_verification_tokens "
                    "WHERE token_hash=? AND consumed_at IS NULL AND expires_at>?",
                    (token_hash, now),
                ).fetchone()
                if row is None:
                    return False
                updated = db.execute(
                    "UPDATE email_verification_tokens SET consumed_at=? "
                    "WHERE token_hash=? AND consumed_at IS NULL AND expires_at>?",
                    (now, token_hash, now),
                )
                if updated.rowcount != 1:
                    return False
                db.execute(
                    "UPDATE accounts SET email_verified=1 WHERE user_id=? AND role='customer' AND disabled=0",
                    (row["user_id"],),
                )
                # Invalidate every other outstanding token for this customer.
                db.execute(
                    "UPDATE email_verification_tokens SET consumed_at=? "
                    "WHERE user_id=? AND consumed_at IS NULL",
                    (now, row["user_id"]),
                )
                return True
        except sqlite3.Error as exc:
            raise AccountStoreError("Could not verify customer email.") from exc

    def authenticate(self, *, email: str, password: str) -> dict[str,str] | None:
        try:
            with self._connect() as db:
                row=db.execute("SELECT * FROM accounts WHERE email=? COLLATE NOCASE",(email.strip().lower(),)).fetchone()
        except sqlite3.Error as exc: raise AccountStoreError("Could not authenticate account.") from exc
        if row is None:
            self._hash(password,b"speedy-live-dummy")
            return None
        candidate=self._hash(password,row["password_salt"],row["password_iterations"])
        if (not hmac.compare_digest(candidate,row["password_hash"]) or row["disabled"]
                or (row["role"] == "customer" and not row["email_verified"])):
            return None
        return {"user_id":row["user_id"],"role":row["role"],"email":row["email"]}

    def identity_is_active(self, *, user_id: str, role: str) -> bool:
        try:
            with self._connect() as db:
                row=db.execute("SELECT role,disabled,email_verified FROM accounts WHERE user_id=?",(user_id,)).fetchone()
            return bool(row and row["role"]==role and not row["disabled"]
                        and (role == "admin" or row["email_verified"]))
        except sqlite3.Error as exc: raise AccountStoreError("Could not verify account status.") from exc
