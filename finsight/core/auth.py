"""
FinSight — Firebase Admin Authentication & Firestore Usage Manager
Handles Firebase ID token verification middleware, Firestore user doc auto-creation,
and usage limit enforcement (free plan: 1 report max).
"""

import os
import logging
from functools import wraps
from flask import request, jsonify, g
import firebase_admin
from firebase_admin import credentials, auth, firestore

logger = logging.getLogger("FinSightAuth")

_firestore_db = None


def init_firebase_admin():
    """
    Initialize Firebase Admin SDK using key path from environment variable
    FIREBASE_SERVICE_ACCOUNT_PATH or local gitignored default path.
    """
    global _firestore_db
    if _firestore_db is not None:
        return _firestore_db

    if not firebase_admin._apps:
        key_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
        if not key_path or not os.path.exists(key_path):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            candidate1 = os.path.join(base_dir, "finsight-fa6ee-firebase-adminsdk-fbsvc-74f11c5a98.json")
            candidate2 = os.path.join(os.path.dirname(base_dir), "finsight", "finsight-fa6ee-firebase-adminsdk-fbsvc-74f11c5a98.json")
            if os.path.exists(candidate1):
                key_path = candidate1
            elif os.path.exists(candidate2):
                key_path = candidate2

        if key_path and os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin SDK initialized with service account key: {key_path}")
        else:
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized using default application credentials.")

    # Firestore (default) database instance — do not specify custom database_id
    _firestore_db = firestore.client()
    return _firestore_db


def get_firestore_db():
    global _firestore_db
    if _firestore_db is None:
        return init_firebase_admin()
    return _firestore_db


def get_or_create_user(uid: str, email: str = ""):
    """
    Get or create a document in 'users' collection keyed by uid with fields:
      - email: string
      - reports_used: int (default 0)
      - plan: string (default "free")
      - created_at: server timestamp
    """
    db = get_firestore_db()
    user_ref = db.collection("users").document(uid)
    doc = user_ref.get()

    if doc.exists:
        data = doc.to_dict() or {}
        if email and not data.get("email"):
            user_ref.update({"email": email})
            data["email"] = email
        return data

    new_data = {
        "email": email or "",
        "reports_used": 0,
        "plan": "free",
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    user_ref.set(new_data)
    logger.info(f"Created new Firestore user document for UID={uid}, Email={email}")
    return new_data


def check_user_usage_limit(uid: str):
    """
    Reads user document from Firestore.
    Returns (allowed: bool, user_data: dict, error_message: str|None).
    Rule: if plan == "free" and reports_used >= 2: allowed = False
    """
    db = get_firestore_db()
    user_ref = db.collection("users").document(uid)
    doc = user_ref.get()

    if not doc.exists:
        user_data = get_or_create_user(uid)
    else:
        user_data = doc.to_dict() or {}

    plan = user_data.get("plan", "free")
    reports_used = user_data.get("reports_used", 0)

    if plan == "free" and reports_used >= 2:
        return False, user_data, "Usage limit reached. Free trial accounts are limited to 2 document report analyses."

    return True, user_data, None


def increment_user_usage(uid: str):
    """
    Atomically increments reports_used by 1 via Firestore's Increment(1).
    Must only be executed after a successful pipeline run.
    """
    try:
        db = get_firestore_db()
        user_ref = db.collection("users").document(uid)
        user_ref.update({
            "reports_used": firestore.Increment(1)
        })
        logger.info(f"Atomically incremented reports_used for user UID={uid}")
    except Exception as e:
        logger.error(f"Failed to increment reports_used for user UID={uid}: {e}")


def require_firebase_auth(f):
    """
    Middleware decorator for Flask routes requiring authenticated Firebase user.
    Extracts Bearer token from 'Authorization' header, verifies with firebase_admin.auth.
    Attaches verified uid and email to Flask 'g' context (g.uid, g.user_email).
    Rejects with 401 Unauthorized if missing, invalid, or expired.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing or malformed Authorization header on request.")
            return jsonify({
                "error": "Unauthorized",
                "message": "Missing or malformed Authorization Bearer token header."
            }), 401

        id_token = auth_header.split("Bearer ")[1].strip()
        if not id_token:
            return jsonify({
                "error": "Unauthorized",
                "message": "Empty Bearer token provided."
            }), 401

        try:
            init_firebase_admin()
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token.get("uid")
            email = decoded_token.get("email", "")

            if not uid:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Firebase ID token payload missing uid."
                }), 401

            g.uid = uid
            g.user_email = email
            g.decoded_token = decoded_token

            # Get or create user record in Firestore
            user_data = get_or_create_user(uid, email=email)
            g.user_data = user_data

        except auth.ExpiredIdTokenError:
            logger.warning("Firebase ID Token expired.")
            return jsonify({
                "error": "Unauthorized",
                "message": "Firebase ID token has expired. Please sign in again."
            }), 401
        except auth.InvalidIdTokenError as e:
            logger.warning(f"Invalid Firebase ID Token: {e}")
            return jsonify({
                "error": "Unauthorized",
                "message": f"Invalid Firebase ID token: {e}"
            }), 401
        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            return jsonify({
                "error": "Unauthorized",
                "message": f"Authentication failed: {str(e)}"
            }), 401

        return f(*args, **kwargs)

    return decorated_function
