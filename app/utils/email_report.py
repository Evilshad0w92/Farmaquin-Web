import os
import ssl
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_MONTHS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

def _fmt_ts(ts: str) -> str:
    """'2026-04-23 20:31:18.677795-06:00' → '23 Abr 2026, 20:31'"""
    try:
        part = str(ts)[:16].replace("T", " ")
        date, time = part.split(" ")
        y, m, d = date.split("-")
        return f"{int(d)} {_MONTHS[int(m)-1]} {y}, {time}"
    except Exception:
        return str(ts)


# ---------------------------------------------------------------------------
# Internal send helper — runs in a background thread
# ---------------------------------------------------------------------------

def _send(subject: str, html: str) -> None:
    host     = os.getenv("MAIL_HOST", "smtp.gmail.com")
    port     = int(os.getenv("MAIL_PORT", "587"))
    user     = os.getenv("MAIL_USER", "")
    password = os.getenv("MAIL_PASS", "")
    to_raw   = os.getenv("MAIL_TO", "")

    if not all([user, password, to_raw]):
        print("[email] Credenciales no configuradas (MAIL_USER/MAIL_PASS/MAIL_TO). Correo omitido.")
        return

    recipients = [r.strip() for r in to_raw.split(",") if r.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Farmaquin <{user}>"
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.login(user, password)
            smtp.sendmail(user, recipients, msg.as_string())
        print(f"[email] Reporte de corte enviado a {to_raw}")
    except Exception as e:
        print(f"[email] Error al enviar reporte: {e}")


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def _row(label: str, value: str, bold: bool = False) -> str:
    weight = "font-weight:700;" if bold else ""
    return f"""
        <tr>
            <td style="padding:6px 10px;border-bottom:1px solid #f0f0f0;color:#374151;{weight}">{label}</td>
            <td style="padding:6px 10px;border-bottom:1px solid #f0f0f0;text-align:right;{weight}">{value}</td>
        </tr>"""

def _section(title: str, color: str, body: str) -> str:
    return f"""
        <h3 style="margin:24px 0 8px;font-size:15px;color:{color};border-left:4px solid {color};padding-left:8px;">{title}</h3>
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;background:#fff;border-radius:8px;border:1px solid #e5e7eb;">
            {body}
        </table>"""

def _build_html(cut: dict, products: list, expenses: list, low_stock: list, expiring: list) -> str:
    # -- Resumen del corte --
    diff     = float(cut["difference"])
    diff_str = f'<span style="color:{"#dc2626" if diff < 0 else "#16a34a"};">{"−" if diff < 0 else "+"} ${abs(diff):,.2f}</span>'

    summary_rows = (
        _row("Período", f'{_fmt_ts(cut["from_ts"])} &nbsp;→&nbsp; {_fmt_ts(cut["to_ts"])}')
        + _row("Ventas brutas", f'${float(cut["total_sales"]):,.2f}')
        + _row("Devoluciones", f'${float(cut["total_returns"]):,.2f}')
        + _row("Ventas netas", f'${float(cut["net_total"]):,.2f}', bold=True)
        + _row("Efectivo ventas", f'${float(cut["total_cash"]):,.2f}')
        + _row("Tarjeta", f'${float(cut["total_card"]):,.2f}')
        + _row("Transferencia", f'${float(cut["total_transfer"]):,.2f}')
        + _row("Gastos", f'${float(cut["total_expenses"]):,.2f}')
        + _row("Efectivo esperado", f'${float(cut["cash_expected"]):,.2f}')
        + _row("Efectivo contado", f'${float(cut["cash_counted"]):,.2f}')
        + _row("Diferencia", diff_str, bold=True)
    )
    if cut.get("comment"):
        summary_rows += _row("Comentario", cut["comment"])

    summary_section = _section("Resumen del Corte", "#2563eb", summary_rows)

    # -- Artículos vendidos --
    if products:
        prod_rows = "".join(
            _row(p["description"], f'{p["quantity"]} pzas — ${float(p["total"]):,.2f}')
            for p in products
        )
    else:
        prod_rows = _row("Sin ventas en este período", "")
    products_section = _section("Artículos Vendidos", "#7c3aed", prod_rows)

    # -- Gastos --
    if expenses:
        exp_rows = "".join(
            _row(f'{e["description"] or e["expense_type"] or "Gasto"}', f'${float(e["amount"]):,.2f}')
            for e in expenses
        )
    else:
        exp_rows = _row("Sin gastos en este período", "")
    expenses_section = _section("Gastos del Período", "#d97706", exp_rows)

    # -- Por agotarse --
    if low_stock:
        ls_rows = "".join(
            _row(
                p["name"],
                f'<span style="color:#dc2626;font-weight:700;">{p["stock"]} / {p["min_stock"]}</span>'
            )
            for p in low_stock
        )
    else:
        ls_rows = _row("Sin productos por agotarse", "")
    low_section = _section("Productos por Agotarse", "#dc2626", ls_rows)

    # -- Próximos a caducar --
    def _expiry_badge(e: dict) -> str:
        days  = e["days_left"]
        color = "#dc2626" if days <= 15 else "#d97706"
        label = "VENCIDO" if days <= 0 else f"{days}d"
        return f'<span style="color:{color};font-weight:700;">{label}</span>'

    if expiring:
        exp2_rows = "".join(
            _row(f'{e["name"]} — Lote {e["lot"]} ({e["qty"]} pzas)', _expiry_badge(e))
            for e in expiring
        )
    else:
        exp2_rows = _row("Sin lotes próximos a vencer", "")
    expiry_section = _section("Próximos a Caducar (60 días)", "#ea580c", exp2_rows)

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;font-size:14px;color:#111827;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:24px 16px;">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr><td style="background:#1e3a5f;border-radius:12px 12px 0 0;padding:24px 32px;text-align:center;">
          <h1 style="margin:0;color:#fff;font-size:22px;">Farmaquin</h1>
          <p style="margin:4px 0 0;color:#93c5fd;font-size:13px;">Reporte de Corte de Caja</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="background:#f9fafb;padding:24px 32px;border-radius:0 0 12px 12px;">
          {summary_section}
          {products_section}
          {expenses_section}
          {low_section}
          {expiry_section}

          <p style="margin-top:28px;font-size:12px;color:#9ca3af;text-align:center;">
            Generado automáticamente por Farmaquin ERP · {cut["to_ts"][:10]}
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body></html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_cashcut_report(
    cut: dict,
    products_summary: list,
    expenses_detail: list,
    low_stock: list,
    expiring: list,
) -> None:
    """Build the HTML report and dispatch it in a daemon background thread."""
    subject = f"Farmaquin – Corte de Caja {_fmt_ts(cut['to_ts'])}"
    html    = _build_html(cut, products_summary, expenses_detail, low_stock, expiring)
    threading.Thread(target=_send, args=(subject, html), daemon=True).start()
