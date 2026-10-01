const natural = new Intl.Collator('zh-CN', { numeric: true, sensitivity: 'base' })
/** Presentation-only context for source names; never an official building-name alias. */
export function displayBuildingName(name: string) {
  return /^\d+$/.test(name.trim()) ? `建筑 ${name}` : name
}
export function sortBuildings<T extends { id: string; name: string }>(
  buildings: readonly T[],
): T[] {
  return [...buildings].sort((a, b) => natural.compare(a.name, b.name) || a.id.localeCompare(b.id))
}
