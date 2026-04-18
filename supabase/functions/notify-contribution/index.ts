import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") ?? "";
const NOTIFICATION_EMAIL = Deno.env.get("NOTIFICATION_EMAIL") ?? "info@zoomoot.com";
const SITE_URL = Deno.env.get("SITE_URL") ?? "https://solarsystem.zoomoot.com";

interface ContributionRecord {
  id: string;
  object_designation: string;
  entity_name: string;
  kind: string;
  body: string | null;
  structured_data: Record<string, unknown> | null;
  parent_id: string | null;
  created_at: string;
}

interface WebhookPayload {
  type: "INSERT";
  table: string;
  record: ContributionRecord;
  schema: string;
}

const KIND_LABELS: Record<string, string> = {
  comment: "Discussion Comment",
  observation: "Observation Report",
  correction: "Data Correction",
  mission_report: "Mission Report",
};

serve(async (req: Request) => {
  try {
    const payload: WebhookPayload = await req.json();
    const record = payload.record;

    if (!record || !RESEND_API_KEY) {
      return new Response(JSON.stringify({ ok: false, reason: "missing data or key" }), {
        status: 200,
      });
    }

    const kindLabel = KIND_LABELS[record.kind] ?? record.kind;
    const isReply = !!record.parent_id;
    const subjectPrefix = isReply ? "Reply" : "New";
    const subject = `[SSF] ${subjectPrefix} ${kindLabel}: ${record.object_designation}`;

    let bodyParts: string[] = [
      `<h2>Solar System Facility — ${kindLabel}</h2>`,
      `<p><strong>Object:</strong> ${record.object_designation}</p>`,
      `<p><strong>From:</strong> ${record.entity_name}</p>`,
      `<p><strong>Time:</strong> ${record.created_at}</p>`,
    ];

    if (isReply) {
      bodyParts.push(`<p><em>This is a reply to an existing thread.</em></p>`);
    }

    if (record.body) {
      bodyParts.push(`<h3>Content</h3><p>${record.body.replace(/\n/g, "<br>")}</p>`);
    }

    if (record.structured_data && Object.keys(record.structured_data).length > 0) {
      bodyParts.push(`<h3>Structured Data</h3><pre>${JSON.stringify(record.structured_data, null, 2)}</pre>`);
    }

    bodyParts.push(
      `<hr>`,
      `<p><a href="${SITE_URL}">Open Solar System Facility</a></p>`,
      `<p style="color:#888; font-size:0.85em;">Contribution ID: ${record.id}</p>`,
    );

    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${RESEND_API_KEY}`,
      },
      body: JSON.stringify({
        from: "Solar System Facility <noreply@zoomoot.com>",
        to: [NOTIFICATION_EMAIL],
        subject: subject,
        html: bodyParts.join("\n"),
      }),
    });

    const result = await res.json();
    return new Response(JSON.stringify({ ok: true, resend: result }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
});
