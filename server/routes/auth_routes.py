"""
Маршруты аутентификации.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import select

from database import get_session
from models import User


def serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "createdAt": user.created_at.isoformat(),
    }


def create_auth_blueprint() -> Blueprint:
    bp = Blueprint("auth", __name__, url_prefix="/api/auth")

    @bp.route("/register", methods=["POST"])
    def register():
        payload = request.get_json() or {}
        email = (payload.get("email") or "").strip().lower()
        password = (payload.get("password") or "").strip()
        name = (payload.get("name") or "").strip() or "Пользователь"

        if not email or not password:
            return jsonify({"success": False, "error": "Укажите email и пароль"}), 400

        session = get_session()

        if session.execute(select(User).where(User.email == email)).scalar_one_or_none():
            return jsonify({"success": False, "error": "Пользователь уже существует"}), 409

        user = User(
            email=email,
            name=name,
            password_hash=generate_password_hash(password),
        )
        session.add(user)
        session.commit()

        token = create_access_token(identity=str(user.id))
        return jsonify({"success": True, "user": serialize_user(user), "token": token}), 201

    @bp.route("/login", methods=["POST"])
    def login():
        payload = request.get_json() or {}
        email = (payload.get("email") or "").strip().lower()
        password = (payload.get("password") or "").strip()

        if not email or not password:
            return jsonify({"success": False, "error": "Введите email и пароль"}), 400

        session = get_session()
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()

        if user is None or not check_password_hash(user.password_hash, password):
            return jsonify({"success": False, "error": "Неверные учетные данные"}), 401

        token = create_access_token(identity=str(user.id))
        return jsonify({"success": True, "user": serialize_user(user), "token": token}), 200

    @bp.route("/me", methods=["GET"])
    @jwt_required()
    def me():
        user_id = get_jwt_identity()
        session = get_session()
        user = session.get(User, user_id)
        if user is None:
            return jsonify({"success": False, "error": "Пользователь не найден"}), 404
        return jsonify({"success": True, "user": serialize_user(user)}), 200

    return bp

