from pathlib import Path
from datetime import date
import sqlite3

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    send_file, jsonify
)

import config
from .db import get_db, get_or_create, get_or_create_brand, get_or_create_model
from .services import (
    read_csv_upload, post_distribute, update_sp_distribution_file,
    build_inventory_workbook, generate_pre_distribution, make_inventory_template
)

bp = Blueprint("main", __name__)

@bp.before_app_request
def ensure_template():
    make_inventory_template()

def rows(sql, params=()):
    conn = get_db()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()

@bp.route("/")
def dashboard():
    conn = get_db()
    stats = {
        "total": conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0],
        "distributed": conn.execute("SELECT COUNT(*) FROM devices WHERE is_distributed=1").fetchone()[0],
        "available": conn.execute("SELECT COUNT(*) FROM devices WHERE is_distributed=0").fetchone()[0],
        "recycle": conn.execute("""
            SELECT COUNT(*) FROM devices d JOIN statuses s ON s.id=d.status_id
            WHERE s.name='To recycle'
        """).fetchone()[0],
    }
    conn.close()
    return render_template("dashboard.html", stats=stats)

@bp.route("/devices")
def devices():
    q = request.args.get("q", "").strip()
    distributed = request.args.get("distributed", "")
    dtype = request.args.get("device_type", "")
    status = request.args.get("status", "")
    brand = request.args.get("brand", "")
    place = request.args.get("place", "")

    sql = """
    SELECT d.*, dt.name AS device_type, b.name AS brand, m.name AS model,
           c.name AS connection, s.name AS status, d.place AS place,
           r.national_id AS recipient_national_id, d.os AS os,
           donor.name AS donor
    FROM devices d
    JOIN device_types dt ON dt.id=d.device_type_id
    JOIN brands b ON b.id=d.brand_id
    JOIN models m ON m.id=d.model_id
    JOIN connections c ON c.id=d.connection_id
    JOIN statuses s ON s.id=d.status_id
    LEFT JOIN recipients r ON r.id=d.recipient_id
    LEFT JOIN donors donor ON donor.id=d.donor_id
    WHERE 1=1
    """
    params = []
    if q:
        sql += """ AND (
            d.internal_barcode LIKE ? OR b.name LIKE ? OR m.name LIKE ?
            OR d.serial_number LIKE ? OR d.imei_1 LIKE ? OR d.imei_2 LIKE ?
            OR r.national_id LIKE ?
        )"""
        params += [f"%{q}%"] * 7
    if distributed in ("0", "1"):
        sql += " AND d.is_distributed=?"
        params.append(int(distributed))
    if dtype:
        sql += " AND dt.name=?"; params.append(dtype)
    if status:
        sql += " AND s.name=?"; params.append(status)
    if brand:
        sql += " AND b.name=?"; params.append(brand)
    if place:
        sql += " AND l.name=?"; params.append(place)
    sql += " ORDER BY d.id DESC"

    conn = get_db()
    devices = conn.execute(sql, params).fetchall()
    filters = {
        "device_types": conn.execute("SELECT name FROM device_types ORDER BY name").fetchall(),
        "statuses": conn.execute("SELECT name FROM statuses ORDER BY name").fetchall(),
        "brands": conn.execute("SELECT name FROM brands ORDER BY name").fetchall(),
    }
    conn.close()
    return render_template("devices.html", devices=devices, filters=filters,
                           q=q, distributed=distributed, dtype=dtype,
                           status=status, brand=brand, place=place)

@bp.route("/devices/add", methods=["GET", "POST"])
def add_devices():
    conn = get_db()

    if request.method == "POST":

        # common info - entered once for all 
        common_IN_prefix = request.form.get(
            "common_IN_prefix", ""
        ).strip()
        
        common_device_type = request.form.get(
            "common_device_type", ""
        ).strip()

        common_brand = request.form.get(
            "common_brand", ""
        ).strip()

        common_model = request.form.get(
            "common_model", ""
        ).strip()

        common_connection = request.form.get(
            "common_connection", ""
        ).strip()

        common_donor_type = request.form.get(
            "common_donor_type", ""
        ).strip()

        common_entry_date = request.form.get(
            "common_entry_date", ""
        ).strip()

        common_donor = request.form.get(
            "common_donor", ""
        ).strip()

        common_place = request.form.get(
            "place", ""
        ).strip()

        rows_data = []

        # individual device info
        for i in range(1, int(request.form.get("row_count", "1")) + 1):

            internal = request.form.get(
                f"internal_barcode_{i}", ""
            ).strip()

            internal = common_IN_prefix + internal

            if not internal:
                continue

            rows_data.append({
                # common fields
                "device_type": common_device_type,
                "brand": common_brand,
                "model": common_model,
                "connection": common_connection,
                "donor_type": common_donor_type,
                "entry_date": common_entry_date,
                "donor": common_donor,
                "place": common_place,

                # individual fields
                "internal": internal,

                "status": request.form.get(
                    f"status_{i}", ""
                ).strip(),

                "capacity": request.form.get(
                    f"capacity_{i}", ""
                ).strip(),

                "os": request.form.get(
                    f"os_{i}", ""
                ).strip(),

                "serial_number": request.form.get(
                    f"serial_number_{i}", ""
                ).strip(),

                "imei_1": request.form.get(
                    f"imei_1_{i}", ""
                ).strip(),

                "imei_2": request.form.get(
                    f"imei_2_{i}", ""
                ).strip(),
            })

        try:

            for r in rows_data:

                required = [
                    "device_type",
                    "brand",
                    "model",
                    "connection",
                    "status",
                    "donor_type",
                    "donor",
                    "entry_date"

                ]

                if any(not r[k] for k in required):
                    raise ValueError(
                        f"Internal number {r['internal']}: "
                        "all required fields must be filled."
                    )

                capacity = int(r["capacity"])

                if capacity < 0:
                    raise ValueError(
                        "Capacity cannot be negative."
                    )

                # lookup tables
                dt = get_or_create(
                    conn,
                    "device_types",
                    r["device_type"]
                )

                brand = get_or_create_brand(
                    conn,
                    r["brand"]
                )

                model = get_or_create_model(
                    conn,
                    brand,
                    r["model"]
                )

                connection = get_or_create(
                    conn,
                    "connections",
                    r["connection"]
                )

                status = get_or_create(
                    conn,
                    "statuses",
                    r["status"]
                )

                donor_type = get_or_create(
                    conn,
                    "donor_types",
                    r["donor_type"]
                )

                donor = get_or_create(
                    conn,
                    "donors",
                    r["donor"]
                )

                conn.execute(
                    """INSERT INTO devices(
                        internal_barcode,
                        device_type_id,
                        brand_id,
                        model_id,
                        connection_id,
                        is_engraved,
                        engraving_date,
                        engraver_id,
                        is_distributed,
                        status_id,
                        place,
                        capacity_gb,
                        os,
                        serial_number,
                        imei_1,
                        imei_2,
                        donor_type_id,
                        entry_date,
                        donor_id
                    )
                    VALUES (
                        ?, ?, ?, ?, ?,
                        0, NULL, NULL,
                        0,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )""",
                    (
                        r["internal"],
                        dt,
                        brand,
                        model,
                        connection,
                        # is_engraved = 0,
                        # engraving_date = NULL,
                        # engraver_id = NULL,
                        # is_distributed = 0,
                        status,
                        r["place"],
                        capacity,
                        r["os"],
                        r["serial_number"],
                        r["imei_1"],
                        r["imei_2"],
                        donor_type,
                        r["entry_date"],
                        donor
                    )
                )

            conn.commit()

            flash(
                f"{len(rows_data)} device(s) added successfully.",
                "success"
            )

            return redirect(
                url_for("main.devices")
            )

        except (sqlite3.IntegrityError, ValueError) as exc:

            conn.rollback()

            flash(
                str(exc),
                "danger"
            )

    # -------------------------------------------------------------
    # Lists used by the Add Device page
    # -------------------------------------------------------------
    lists = {
        "device_types": conn.execute(
            "SELECT name FROM device_types ORDER BY name"
        ).fetchall(),

        "connections": conn.execute(
            "SELECT name FROM connections ORDER BY name"
        ).fetchall(),

        "statuses": conn.execute(
            "SELECT name FROM statuses ORDER BY name"
        ).fetchall(),

        "donor_types": conn.execute(
            "SELECT name FROM donor_types ORDER BY name"
        ).fetchall(),

        "donors": conn.execute(
            "SELECT name FROM donors ORDER BY name"
        ).fetchall(),
    }

    conn.close()

    return render_template(
        "add_devices.html",
        lists=lists,
        today=date.today().isoformat()
    )

@bp.route("/accessoires", methods=["GET", "POST"])
def accessories():
    conn = get_db()
    if request.method == "POST":
        try:
            for row in conn.execute("SELECT id FROM accessories").fetchall():
                aid = row["id"]
                value = int(request.form.get(f"quantity_{aid}", "0"))
                if value < 0:
                    raise ValueError("Accessory quantity cannot be negative.")
                conn.execute(
                    "UPDATE accessories SET quantity=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (value, aid)
                )
            conn.commit()
            flash("Accessory inventory saved.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
    items = conn.execute("SELECT * FROM accessories ORDER BY name").fetchall()
    conn.close()
    return render_template("accessories.html", accessories=items)

@bp.route("/post-distribution", methods=["GET", "POST"])
def post_distribution():
    if request.method == "POST":
        upload = request.files.get("csv_file")
        distribution_date = request.form.get("distribution_date", "").strip()
        if not upload or not upload.filename:
            flash("Please select a CSV file.", "danger")
            return redirect(request.url)
        if not distribution_date:
            flash("Please select a distribution date.", "danger")
            return redirect(request.url)
        try:
            df = read_csv_upload(upload)
            updated, errors = post_distribute(df, distribution_date)
            if errors:
                for e in errors:
                    flash(e, "danger")
                flash("No database changes were committed because the CSV contains errors.", "danger")
            else:
                import json
                return render_template(
                    "post_distribution_success.html",
                    updated=updated,
                    distribution_date=distribution_date
                )
        except Exception as exc:
            flash(str(exc), "danger")
    return render_template("post_distribution.html", today=date.today().isoformat())

@bp.route("/post-distribution/update-sp", methods=["POST"])
def update_sp():
    data = request.get_json(force=True)
    try:
        update_sp_distribution_file(data["updated"], data["distribution_date"])
        return jsonify(ok=True, message="SP Distribution file updated successfully.")
    except Exception as exc:
        return jsonify(ok=False, message=str(exc)), 400

@bp.route("/inventory/download")
def inventory_download():
    make_inventory_template()
    output = config.BASE_DIR / "SP_TAB_Device_and_Accessoires_Inventory.xlsx"
    try:
        build_inventory_workbook(output)
        return send_file(output, as_attachment=True,
                         download_name="SP_TAB_Device_and_Accessoires_Inventory.xlsx")
    except Exception as exc:
        flash(str(exc), "danger")
        return redirect(url_for("main.dashboard"))

@bp.route("/pre-distribution", methods=["GET", "POST"])
def pre_distribution():
    if request.method == "POST":
        upload = request.files.get("csv_file")
        output_name = request.form.get("output_name", "").strip()
        if not upload or not upload.filename:
            flash("Please select a CSV file.", "danger")
            return redirect(request.url)
        if not output_name:
            flash("Please provide a file name.", "danger")
            return redirect(request.url)
        try:
            df = read_csv_upload(upload)
            output = generate_pre_distribution(df, output_name)
            flash(f"Created: {output.name}", "success")
            return send_file(output, as_attachment=True, download_name=output.name)
        except Exception as exc:
            flash(str(exc), "danger")
    return render_template("pre_distribution.html")
