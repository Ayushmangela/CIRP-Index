'use client';

export function Pagination({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between mt-4 pt-3 border-t border-hairline text-xs font-mono tabular-nums text-[#6B6B66]">
      <span>
        {start}–{end} of {total}
      </span>
      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          className="disabled:opacity-30 hover:text-ink focus:outline-none focus-visible:ring-1 focus-visible:ring-ink"
        >
          ← Prev
        </button>
        <span>
          {page} / {totalPages}
        </span>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          className="disabled:opacity-30 hover:text-ink focus:outline-none focus-visible:ring-1 focus-visible:ring-ink"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
