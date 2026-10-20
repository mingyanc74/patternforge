import type { Column } from "../api";

export function DataTable({
  rows,
  columns,
  selected = [],
  offset = 0,
}: {
  rows: Record<string, unknown>[];
  columns: Column[];
  selected?: string[];
  offset?: number;
}) {
  return (
    <div className="table-wrap data-scroll">
      <table className="data-table" aria-label="Data preview">
        <thead>
          <tr>
            <th className="row-number">#</th>
            {columns.map((column) => (
              <th
                key={column.name}
                className={
                  selected.includes(column.name) ? "selected-column" : ""
                }
              >
                <span className="data-type">Aa</span>
                {column.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              <td className="row-number">{offset + index + 1}</td>
              {columns.map((column) => (
                <td
                  key={column.name}
                  className={
                    selected.includes(column.name) ? "selected-column" : ""
                  }
                  title={
                    row[column.name] == null
                      ? undefined
                      : String(row[column.name])
                  }
                >
                  {row[column.name] == null ? (
                    <span className="null-value">null</span>
                  ) : row[column.name] === "" ? (
                    <span className="null-value">empty</span>
                  ) : (
                    String(row[column.name]).slice(0, 250)
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && (
        <div className="empty compact">
          No rows in this dataset. Column names are preserved.
        </div>
      )}
    </div>
  );
}
