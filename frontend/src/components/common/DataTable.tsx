import {
  flexRender,
  functionalUpdate,
  getCoreRowModel,
  type ColumnDef,
  type OnChangeFn,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";

interface DataTableProps<TData> {
  columns: ColumnDef<TData, any>[];
  data: TData[];
  sorting: SortingState;
  onSortingChange: OnChangeFn<SortingState>;
  pageIndex: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (pageIndex: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  getRowId?: (row: TData) => string;
  onRowClick?: (row: TData) => void;
  emptyMessage?: string;
}

export function DataTable<TData>({
  columns,
  data,
  sorting,
  onSortingChange,
  pageIndex,
  pageSize,
  totalCount,
  onPageChange,
  onPageSizeChange,
  getRowId,
  onRowClick,
  emptyMessage = "No records found.",
}: DataTableProps<TData>) {
  const pagination = { pageIndex, pageSize };
  const table = useReactTable({
    columns,
    data,
    state: { pagination, sorting },
    getCoreRowModel: getCoreRowModel(),
    getRowId,
    manualPagination: true,
    manualSorting: true,
    rowCount: totalCount,
    enableMultiSort: false,
    enableSortingRemoval: false,
    onSortingChange,
    onPaginationChange: (updater) => {
      const next = functionalUpdate(updater, pagination);
      onPageChange(next.pageIndex);
    },
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-auto rounded-md border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[960px] border-collapse text-left">
          <thead className="sticky top-0 z-10 bg-slate-50 shadow-[0_1px_0_0_rgb(226_232_240)]">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-slate-200">
                {headerGroup.headers.map((header) => {
                  const sorted = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      scope="col"
                      aria-sort={
                        sorted === "asc"
                          ? "ascending"
                          : sorted === "desc"
                            ? "descending"
                            : "none"
                      }
                      className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500"
                    >
                      {header.isPlaceholder ? null : header.column.getCanSort() ? (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className="inline-flex items-center gap-1 rounded-sm hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2"
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          <span aria-hidden="true" className="w-3 text-center">
                            {sorted === "asc" ? "↑" : sorted === "desc" ? "↓" : "↕"}
                          </span>
                        </button>
                      ) : (
                        flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-slate-100">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-2 py-4 text-center text-sm text-slate-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => onRowClick?.(row.original)}
                  className={
                    onRowClick
                      ? "group cursor-pointer text-sm text-slate-600 hover:bg-teal-50/40"
                      : "text-sm text-slate-600"
                  }
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-2 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <nav
        className="mt-1 flex shrink-0 flex-wrap items-center justify-between gap-1.5"
        aria-label="Table pagination"
      >
        <span className="text-xs text-slate-500">
          {totalCount === 0
            ? "0 patients"
            : `Showing ${pageIndex * pageSize + 1}-${Math.min(
                (pageIndex + 1) * pageSize,
                totalCount,
              )} of ${totalCount} patients`}
        </span>

        <div className="flex items-center gap-1.5">
          <label className="flex items-center gap-1.5 text-xs text-slate-600">
            Rows per page
            <select
              value={pageSize}
              onChange={(event) => onPageSizeChange(Number(event.target.value))}
              className="rounded border border-slate-300 bg-white px-1.5 py-1 text-xs font-semibold text-slate-700 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
              aria-label="Rows per page"
            >
              {[10, 20, 50].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
          >
            Previous
          </button>
          <span className="whitespace-nowrap text-xs text-slate-500">
            Page {pageIndex + 1} of {Math.max(table.getPageCount(), 1)}
          </span>
          <button
            type="button"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
          >
            Next
          </button>
        </div>
      </nav>
    </div>
  );
}
