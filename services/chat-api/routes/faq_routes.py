"""
Маршруты для FAQ.
"""

from flask import Blueprint, jsonify

from faq_data import FAQ_ITEMS


def create_faq_blueprint() -> Blueprint:
    bp = Blueprint("faq", __name__, url_prefix="/api/faq")

    @bp.route("", methods=["GET"])
    def list_faq():
        return jsonify({"success": True, "items": FAQ_ITEMS}), 200

    return bp

