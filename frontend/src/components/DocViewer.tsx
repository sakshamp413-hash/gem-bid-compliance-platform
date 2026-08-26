import { useEffect, useState } from "react";
import type { Document } from "../api/client";
import { SigBadge, TamperBadge } from "./ui";

/**
 * Split-view document viewer: rendered PDF page with extracted-field
 * highlight boxes (bbox in PDF points → scaled to the rendered image).
 */
export default function DocViewer({ doc }: { doc: Document }) {
  const [page, setPage] = useState(1);
  const [nPages, setNPages] = useState(1);
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  const [imgSize, setImgSize] = useState<{ w: number; h: number } | null>(null);

  useEffect(() => {
    setImgUrl(null);
    setImgSize(null);
    const url = `/documents/${doc.id}/page/${page}.png?scale=2`;
    const img = new Image();
    img.onload = () => {
      setImgUrl(url);
      setImgSize({ w: img.naturalWidth, h: img.naturalHeight });
    };
    img.src = url;
    return () => {
      img.onload = null;
    };
  }, [doc.id, page]);

  const fields = (doc.extracted_json?.fields as
    | Record<string, { value: string; confidence?: number; page?: number; bbox?: number[] }>
    | undefined) || {};
  const pageFields = Object.entries(fields).filter(([, f]) => f.bbox && (f.page === page || !f.page));

  const renderWidth = 480; // CSS px
  const scaleX = imgSize ? imgSize.w / 595.28 : 1; // A4 width in points
  const scaleY = imgSize ? imgSize.h / 841.89 : 1;

  const details: (Record<string, unknown> | null)[] = [
    doc.signature_detail,
    doc.tamper_flags_json,
  ];

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-slate-500">{doc.file_name}</span>
        <SigBadge status={doc.signature_status} />
        <TamperBadge tampered={doc.tamper_flags_json?.tampered as boolean | undefined} />
        <span className="text-[11px] text-slate-400">
          OCR: {doc.ocr_source || "none"} · conf {doc.ocr_confidence != null ? Math.round(doc.ocr_confidence * 100) : "—"}%
        </span>
      </div>

      <div className="flex flex-col gap-4 lg:flex-row">
        {/* left: rendered page with highlights */}
        <div className="relative min-h-[300px] flex-1 rounded-md border border-slate-200 bg-slate-100 p-2">
          {!imgUrl && <div className="py-20 text-center text-xs text-slate-400">Rendering page…</div>}
          {imgUrl && imgSize && (
            <div className="relative mx-auto" style={{ width: renderWidth }}>
              <img
                src={imgUrl}
                alt={`Page ${page}`}
                className="w-full rounded shadow"
                style={{ display: "block" }}
              />
              {pageFields.map(([key, f]) => {
                const [x0, top, x1, bottom] = f.bbox as number[];
                const left = (x0 / 595.28) * renderWidth;
                const topPx = (top / 841.89) * (renderWidth * (imgSize.h / imgSize.w));
                const wPx = ((x1 - x0) / 595.28) * renderWidth;
                const hPx = ((bottom - top) / 841.89) * (renderWidth * (imgSize.h / imgSize.w));
                return (
                  <div
                    key={key}
                    title={`${key}: ${f.value}`}
                    className="absolute border-2 border-amber-400 bg-amber-300/25"
                    style={{ left, top: topPx, width: wPx, height: hPx }}
                  />
                );
              })}
            </div>
          )}
          <div className="mt-2 flex items-center justify-center gap-3 text-xs text-slate-500">
            <button
              className="rounded border border-slate-300 px-2 py-0.5 disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              ◀ Prev
            </button>
            <span>
              Page {page} / {nPages}
            </span>
            <button
              className="rounded border border-slate-300 px-2 py-0.5 disabled:opacity-40"
              disabled={page >= nPages}
              onClick={() => setPage((p) => Math.min(nPages, p + 1))}
            >
              Next ▶
            </button>
          </div>
        </div>

        {/* right: extracted fields + integrity detail */}
        <div className="w-full space-y-3 lg:w-80">
          <div className="rounded-md border border-slate-200 bg-white p-3">
            <div className="label">Extracted fields (AI / OCR)</div>
            {Object.keys(fields).length === 0 && <div className="text-xs text-slate-400">No fields extracted.</div>}
            <ul className="space-y-1.5">
              {Object.entries(fields).map(([key, f]) => (
                <li key={key} className="flex items-baseline justify-between gap-2 text-xs">
                  <span className="text-slate-500">{key}</span>
                  <span className="text-right font-medium text-gov-navy">{f.value}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-md border border-slate-200 bg-white p-3">
            <div className="label">Signature analysis</div>
            <pre className="max-h-44 overflow-auto text-[10px] leading-relaxed text-slate-600">
              {JSON.stringify(details[0], null, 1)}
            </pre>
          </div>
          <div className="rounded-md border border-slate-200 bg-white p-3">
            <div className="label">Tamper analysis</div>
            <pre className="max-h-44 overflow-auto text-[10px] leading-relaxed text-slate-600">
              {JSON.stringify(details[1], null, 1)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}