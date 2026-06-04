export function formatMillis(value: number | null | undefined): string {
  if (!value) {
    return "never";
  }
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function countByStatus(items: Array<{ status?: string | null }>): Record<string, number> {
  return items.reduce<Record<string, number>>((counts, item) => {
    const status = item.status || "unknown";
    counts[status] = (counts[status] || 0) + 1;
    return counts;
  }, {});
}

export function compactId(value: string, prefixLength = 8): string {
  if (value.length <= prefixLength + 3) {
    return value;
  }
  return `${value.slice(0, prefixLength)}...`;
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
