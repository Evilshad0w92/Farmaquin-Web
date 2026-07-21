import os
import threading
import requests
from app.utils.email_report import build_report_html

_MONTHS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

def _fmt_date(ts: str) -> str:
    try:
        y, m, d = str(ts)[:10].split("-")
        return f"{int(d)} {_MONTHS[int(m)-1]} {y}"
    except Exception:
        return str(ts)[:10]


def _build_summary(cut: dict) -> str:
    diff = float(cut["difference"])
    diff_icon = "⚠️" if diff < 0 else "✅"
    diff_str  = f"{'−' if diff < 0 else '+'} ${abs(diff):,.2f}"

    lines = [
        "📊 *Farmaquin — Corte de Caja*",
        f"📅 {_fmt_date(cut['to_ts'])}",
        "",
        f"💰 Ventas brutas:     ${float(cut['total_sales']):,.2f}",
        f"↩️  Devoluciones:      ${float(cut['total_returns']):,.2f}",
        f"✅ Ventas netas:     ${float(cut['net_total']):,.2f}",
        "",
        f"💵 Efectivo:          ${float(cut['total_cash']):,.2f}",
        f"💳 Tarjeta:           ${float(cut['total_card']):,.2f}",
        f"🔄 Transferencia:     ${float(cut['total_transfer']):,.2f}",
        f"🧾 Gastos:            ${float(cut['total_expenses']):,.2f}",
        "",
        f"📦 Efectivo esperado: ${float(cut['cash_expected']):,.2f}",
        f"📦 Efectivo contado:  ${float(cut['cash_counted']):,.2f}",
        f"{diff_icon} Diferencia:        {diff_str}",
    ]

    if cut.get("comment"):
        lines.append(f"\n💬 {cut['comment']}")

    lines.append("\n📎 Reporte completo adjunto.")
    return "\n".join(lines)


def _upload_media(pdf_bytes: bytes, token: str, phone_id: str) -> str | None:
    url = f"https://graph.facebook.com/v19.0/{phone_id}/media"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": ("reporte.pdf", pdf_bytes, "application/pdf"),
            "messaging_product": (None, "whatsapp"),
            "type": (None, "application/pdf"),
        },
        timeout=30,
    )
    if resp.ok:
        return resp.json().get("id")
    print(f"[whatsapp] Error al subir PDF ({resp.status_code}): {resp.text}")
    return None


def _send_msg(payload: dict, token: str, phone_id: str) -> None:
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    if not resp.ok or (isinstance(body, dict) and "error" in body):
        print(f"[whatsapp] Error al enviar mensaje ({resp.status_code}): {body}")
    else:
        print(f"[whatsapp] Mensaje enviado OK ({resp.status_code}): {body}")


def _worker(cut: dict, products: list, expenses: list, low_stock: list, expiring: list) -> None:
    token    = os.getenv("META_WA_TOKEN", "")
    phone_id = os.getenv("META_WA_PHONE_ID", "")
    to_raw   = os.getenv("META_WA_TO", "")

    if not all([token, phone_id, to_raw]):
        print("[whatsapp] META_WA_TOKEN / META_WA_PHONE_ID / META_WA_TO no configurados. Omitido.")
        return

    recipients = [r.strip() for r in to_raw.split(",") if r.strip()]

    try:
        import io
        from xhtml2pdf import pisa
        html      = build_report_html(cut, products, expenses, low_stock, expiring, for_pdf=True)
        buf       = io.BytesIO()
        pisa.CreatePDF(html, dest=buf)
        pdf_bytes = buf.getvalue()
    except Exception as e:
        print(f"[whatsapp] Error al generar PDF: {e}")
        return

    summary  = _build_summary(cut)
    filename = f"corte_{str(cut['to_ts'])[:10]}.pdf"

    for recipient in recipients:
        media_id = _upload_media(pdf_bytes, token, phone_id)
        if media_id is None:
            print(f"[whatsapp] No se pudo subir el PDF para {recipient}, se omite.")
            continue

        _send_msg({
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": summary},
        }, token, phone_id)

        _send_msg({
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "document",
            "document": {"id": media_id, "filename": filename},
        }, token, phone_id)

        print(f"[whatsapp] Reporte enviado a {recipient}")


def send_whatsapp_report(
    cut: dict,
    products_summary: list,
    expenses_detail: list,
    low_stock: list,
    expiring: list,
) -> None:
    """Genera el PDF del corte y lo manda por WhatsApp en un hilo de fondo."""
    threading.Thread(
        target=_worker,
        args=(cut, products_summary, expenses_detail, low_stock, expiring),
        daemon=True,
    ).start()
