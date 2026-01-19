from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields, validate

from .. import db

blp = Blueprint(
    "Booking API",
    "booking",
    url_prefix="/api",
    description="Customer booking flow endpoints",
)


class BrandSchema(Schema):
    id = fields.Int(required=True)
    name = fields.Str(required=True)


class ModelSchema(Schema):
    id = fields.Int(required=True)
    brand_id = fields.Int(required=True)
    name = fields.Str(required=True)


class ProblemSchema(Schema):
    id = fields.Int(required=True)
    name = fields.Str(required=True)


class BookingCreateSchema(Schema):
    customer_name = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    phone = fields.Str(required=True, validate=validate.Length(min=5, max=40))
    email = fields.Email(required=True)
    brand_id = fields.Int(required=True, strict=True)
    model_id = fields.Int(required=True, strict=True)
    problem_id = fields.Int(required=True, strict=True)
    notes = fields.Str(required=False, allow_none=True, validate=validate.Length(max=2000))


class BookingCreateResponseSchema(Schema):
    booking_id = fields.Int(required=True)


class BookingSchema(Schema):
    id = fields.Int(required=True)
    customer_name = fields.Str(required=True)
    phone = fields.Str(required=True)
    email = fields.Email(required=True)
    brand_id = fields.Int(required=True)
    brand_name = fields.Str(required=True)
    model_id = fields.Int(required=True)
    model_name = fields.Str(required=True)
    problem_id = fields.Int(required=True)
    problem_name = fields.Str(required=True)
    notes = fields.Str(allow_none=True)
    status = fields.Str(required=True)
    created_at = fields.Str(required=True)


@blp.route("/brands")
class Brands(MethodView):
    @blp.response(200, BrandSchema(many=True))
    def get(self):
        """List supported device brands."""
        return db.list_brands()


@blp.route("/models")
class Models(MethodView):
    @blp.response(200, ModelSchema(many=True))
    def get(self):
        """List models for a brand.

        Query params:
          - brand: integer brand id
        """
        from flask import request

        brand = request.args.get("brand")
        if not brand:
            abort(400, message="Missing required query parameter: brand")
        try:
            brand_id = int(brand)
        except ValueError:
            abort(400, message="Invalid brand id")

        return db.list_models(brand_id)


@blp.route("/problems")
class Problems(MethodView):
    @blp.response(200, ProblemSchema(many=True))
    def get(self):
        """List common repair problems."""
        return db.list_problems()


@blp.route("/booking")
class Booking(MethodView):
    @blp.arguments(BookingCreateSchema)
    @blp.response(201, BookingCreateResponseSchema)
    def post(self, booking_data):
        """Create a new booking.

        Returns:
          - booking_id: integer
        """
        # Verify model belongs to brand (basic referential validation)
        models = db.list_models(int(booking_data["brand_id"]))
        if not any(m["id"] == int(booking_data["model_id"]) for m in models):
            abort(400, message="Selected model does not belong to the selected brand")

        booking_id = db.create_booking(booking_data)
        return {"booking_id": booking_id}

    @blp.response(200, BookingSchema)
    def get(self):
        """Retrieve a booking by id.

        Query params:
          - id: booking id
        """
        from flask import request

        booking_id = request.args.get("id")
        if not booking_id:
            abort(400, message="Missing required query parameter: id")
        try:
            bid = int(booking_id)
        except ValueError:
            abort(400, message="Invalid booking id")

        booking = db.get_booking(bid)
        if not booking:
            abort(404, message="Booking not found")
        return booking


class TrackingEventSchema(Schema):
    id = fields.Int(required=True)
    booking_id = fields.Int(required=True)
    status = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    timestamp = fields.Str(required=True)


class TrackResponseSchema(Schema):
    booking_id = fields.Int(required=True)
    current_status = fields.Str(required=True)
    created_at = fields.Str(required=True)
    history = fields.List(fields.Nested(TrackingEventSchema), required=True)


@blp.route("/track/<int:booking_id>")
class TrackBooking(MethodView):
    @blp.response(200, TrackResponseSchema)
    def get(self, booking_id: int):
        """Track a booking by id.

        Returns the booking's current status + an ordered tracking timeline.

        Path params:
          - booking_id: integer

        Response:
          - booking_id
          - current_status
          - created_at
          - history: [{id, booking_id, status, description, timestamp}, ...]
        """
        booking = db.get_booking(int(booking_id))
        if not booking:
            abort(404, message="Invalid booking ID. Booking not found.")

        # Ensure legacy bookings have at least an initial tracking row.
        db.ensure_initial_tracking_event_for_booking(int(booking_id))

        history = db.list_tracking_history(int(booking_id))
        current_status = (
            history[-1]["status"] if history else booking.get("status") or "new"
        )

        return {
            "booking_id": int(booking_id),
            "current_status": current_status,
            "created_at": booking["created_at"],
            "history": history,
        }


admin_blp = Blueprint(
    "Admin API",
    "admin",
    url_prefix="/api/admin",
    description="Admin endpoints for listing and updating bookings",
)


class AdminBookingListSchema(Schema):
    id = fields.Int(required=True)
    customer_name = fields.Str(required=True)
    phone = fields.Str(required=True)
    email = fields.Email(required=True)
    status = fields.Str(required=True)
    created_at = fields.Str(required=True)
    brand_name = fields.Str(required=True)
    model_name = fields.Str(required=True)
    problem_name = fields.Str(required=True)


class AdminBookingsResponseSchema(Schema):
    total = fields.Int(required=True)
    items = fields.List(fields.Nested(AdminBookingListSchema), required=True)


class AdminUpdateStatusSchema(Schema):
    booking_id = fields.Int(required=True, strict=True)
    status = fields.Str(
        required=True,
        validate=validate.OneOf(["new", "in_progress", "completed", "cancelled"]),
    )


class AdminUpdateStatusResponseSchema(Schema):
    updated = fields.Bool(required=True)


@admin_blp.route("/bookings")
class AdminBookings(MethodView):
    @admin_blp.response(200, AdminBookingsResponseSchema)
    def get(self):
        """List bookings for admin dashboard.

        Optional query params:
          - status
          - brand_id
          - model_id
          - problem_id
          - search (matches name/email/phone)
          - limit (default 100, max 200)
          - offset (default 0)
        """
        from flask import request

        def _int_or_none(v):
            if v is None or v == "":
                return None
            try:
                return int(v)
            except ValueError:
                abort(400, message=f"Invalid integer value: {v}")

        status = request.args.get("status") or None
        brand_id = _int_or_none(request.args.get("brand_id"))
        model_id = _int_or_none(request.args.get("model_id"))
        problem_id = _int_or_none(request.args.get("problem_id"))
        search = request.args.get("search") or None

        limit = request.args.get("limit", "100")
        offset = request.args.get("offset", "0")
        try:
            limit_i = int(limit)
            offset_i = int(offset)
        except ValueError:
            abort(400, message="limit and offset must be integers")

        if limit_i < 1:
            abort(400, message="limit must be >= 1")
        if limit_i > 200:
            limit_i = 200
        if offset_i < 0:
            abort(400, message="offset must be >= 0")

        items, total = db.list_admin_bookings(
            status=status,
            brand_id=brand_id,
            model_id=model_id,
            problem_id=problem_id,
            search=search,
            limit=limit_i,
            offset=offset_i,
        )
        return {"total": total, "items": items}


@admin_blp.route("/update_status")
class AdminUpdateStatus(MethodView):
    @admin_blp.arguments(AdminUpdateStatusSchema)
    @admin_blp.response(200, AdminUpdateStatusResponseSchema)
    def post(self, payload):
        """Update a booking status.

        Body:
          - booking_id: int
          - status: one of new|in_progress|completed|cancelled

        Side effects:
          - Inserts a tracking_history row for the timeline.
        """
        updated = db.update_booking_status_with_history(
            int(payload["booking_id"]), payload["status"]
        )
        if not updated:
            abort(404, message="Booking not found")
        return {"updated": True}
