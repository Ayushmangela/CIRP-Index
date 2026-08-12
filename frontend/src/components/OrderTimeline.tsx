import type { OrderSummary } from '@/lib/api';
import { StatusPill } from './StatusPill';
import { formatDate } from '@/lib/format';

export function OrderTimeline({ orders }: { orders: OrderSummary[] }) {
  const sorted = [...orders].sort((a, b) => {
    if (!a.order_date) return 1;
    if (!b.order_date) return -1;
    return a.order_date.localeCompare(b.order_date);
  });

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex items-start gap-0 min-w-max">
        {sorted.map((order, i) => (
          <div key={order.id} className="flex items-start">
            <div className="flex flex-col items-center w-40 shrink-0">
              <span className="w-2 h-2 rounded-full bg-ink" aria-hidden />
              <span className="mt-2 text-[11px] font-mono tabular-nums text-center">
                {formatDate(order.order_date)}
              </span>
              <div className="mt-1.5">
                <StatusPill outcome={order.outcome} />
              </div>
              <a
                href={order.pdf_url}
                target="_blank"
                rel="noreferrer"
                className="mt-1.5 text-[10px] font-mono uppercase tracking-wider text-[#6B6B66] hover:text-ink underline underline-offset-2"
              >
                Source PDF
              </a>
              {order.processing_status === 'ocr_extracted' && (
                <span
                  className="mt-1 text-[9px] font-mono uppercase tracking-wider text-[#B8860B]"
                  title="This order was a scanned image with no text layer — its text comes from OCR, not the original document. Verify against the source PDF before relying on any figure."
                >
                  OCR text
                </span>
              )}
            </div>
            {i < sorted.length - 1 && (
              <div className="w-10 h-px bg-hairline mt-1 shrink-0" aria-hidden />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
