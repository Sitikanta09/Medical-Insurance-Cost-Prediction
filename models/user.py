from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
import sqlite3

class UserModel:
    """Encapsulates persistent database operations for Users."""

    @staticmethod
    def create(username, password, email=None):
        """
        Create a new user with hashed password.
        Returns: (user_dict, error_message)
        """
        db = get_db()
        username = username.strip()
        email = email.strip() if email else None

        if not username:
            return None, "Username cannot be empty."
        if not password or len(password) < 6:
            return None, "Password must be at least 6 characters long."

        password_hash = generate_password_hash(password)

        try:
            cursor = db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            db.commit()
            return UserModel.get_by_id(cursor.lastrowid), None
        except sqlite3.IntegrityError as e:
            err_msg = str(e).lower()
            if "username" in err_msg:
                return None, f"Username '{username}' is already taken. Please choose another."
            elif "email" in err_msg and email:
                return None, f"Email '{email}' is already registered."
            return None, "A user with these credentials already exists."

    @staticmethod
    def get_by_id(user_id):
        """Retrieve a user by ID."""
        db = get_db()
        row = db.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_username(username):
        """Retrieve full user record (including password_hash) by username."""
        db = get_db()
        row = db.execute(
            "SELECT id, username, email, password_hash, created_at FROM users WHERE LOWER(username) = LOWER(?)",
            (username.strip(),)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def verify_password(stored_hash, password):
        """Safely verify provided password against the stored password hash."""
        if not stored_hash or not password:
            return False
        return check_password_hash(stored_hash, password)

    @staticmethod
    def update_email(user_id, email):
        """Update user email address."""
        db = get_db()
        email = email.strip() if email else None
        try:
            db.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
            db.commit()
            return True, "Profile updated successfully."
        except sqlite3.IntegrityError:
            return False, "This email is already in use by another account."
